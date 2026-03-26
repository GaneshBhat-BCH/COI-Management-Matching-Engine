import msal
import requests
import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from databases import Database
from app.utils.doc_extraction import extract_text, pdf_to_base64_images
from app.services.ai import analyze_document_and_answer, analyze_document_visual, get_embeddings, ocr_document_visual
from app.questions import QUESTIONS_DATA, QUESTIONS
from app.utils.logger import log_event
from app.utils.chunking import chunk_text

# Load .env
dotenv_path = os.path.join(os.getcwd(), 'app', '.env')
load_dotenv(dotenv_path)

# Config
CLIENT_ID = os.getenv("SP_CLIENT_ID")
CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET")
TENANT_ID = os.getenv("SP_TENANT_ID")
SITE_ID = os.getenv("SP_SITE_ID")
DRIVE_ID = os.getenv("SP_DRIVE_ID")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Azure AD Auth
authority = f"https://login.microsoftonline.com/{TENANT_ID}"
scope = ["https://graph.microsoft.com/.default"]

async def get_access_token():
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=authority, client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_silent(scope, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=scope)
    return result.get("access_token")

async def check_schema(db: Database):
    """Ensures all required columns exist in the database."""
    print("Checking database schema...")
    try:
        # Check for columns in pdf_documents
        cols_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'coi_mgmt' AND table_name = 'pdf_documents'
        """
        existing_cols = [r["column_name"] for r in await db.fetch_all(cols_query)]
        
        required_cols = {
            "input_body": "TEXT",
            "modified_at": "TIMESTAMP",
            "doc_date": "TEXT",
            "docusign_id": "TEXT",
            "from_user": "TEXT"
        }
        
        for col, col_type in required_cols.items():
            if col not in existing_cols:
                print(f"Migration: Adding column '{col}' to coi_mgmt.pdf_documents...")
                await db.execute(f"ALTER TABLE coi_mgmt.pdf_documents ADD COLUMN {col} {col_type}")
                
    except Exception as e:
        print(f"Schema check warning: {e}")

async def sync_sharepoint():
    log_event("SharePoint Sync", "Starting sync process", "START")
    db = Database(DATABASE_URL)
    await db.connect()
    
    # Run Schema Verification
    await check_schema(db)
    
    processed_files = [] # Track actually processed (inserted/updated) files
    
    token = await get_access_token()
    if not token:
        log_event("SharePoint Sync", "Failed to acquire access token", "ERROR")
        await db.disconnect()
        return processed_files

    headers = {"Authorization": f"Bearer {token}"}
    
    # 0. Resolve the specific folder ID
    target_folder_path = "Legal Business Units/COI Management/COI Management Plans"
    encoded_path = target_folder_path.replace(" ", "%20")
    resolve_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{encoded_path}"
    
    target_folder_id = None
    try:
        resolve_resp = requests.get(resolve_url, headers=headers)
        if resolve_resp.status_code == 200:
            target_folder_id = resolve_resp.json().get("id")
            print(f"Resolved target folder ID by path: {target_folder_id}")
        else:
            print(f"Could not resolve '{target_folder_path}' directly. Searching...")
            search_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root/search(q='COI Management Plans')"
            search_resp = requests.get(search_url, headers=headers)
            if search_resp.status_code == 200:
                results = search_resp.json().get("value", [])
                for res in results:
                    if res.get("name") == "COI Management Plans" and "folder" in res:
                        target_folder_id = res.get("id")
                        print(f"Found target folder ID by search: {target_folder_id}")
                        break
            
            if not target_folder_id:
                 print("Critical: Target folder not found. Falling back to root (not recommended).")
    except Exception as e:
        print(f"Error resolving path: {e}")

    # 1. Traverse Drive (Recursive)
    async def process_folder(folder_id=None, current_path=""):
        if folder_id:
            url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{folder_id}/children"
        else:
            url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root/children"
            
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching children for {folder_id or 'root'}: {response.text}")
            return
    
        items = response.json().get("value", [])
        for item in items:
            item_name = item["name"]
            if "folder" in item:
                # Recursive call for subfolders
                new_path = f"{current_path}/{item_name}" if current_path else item_name
                await process_folder(item["id"], new_path)
            else:
                # Process File (PDF or DOCX)
                raw_file_name = item_name
                file_ext = os.path.splitext(raw_file_name)[1].lower()
                if file_ext in [".pdf", ".docx"]:
                    # Construct full file name as subfolder/filename.ext
                    display_file_name = f"{current_path}/{raw_file_name}" if current_path else raw_file_name
                    
                    # Safeguard: If path still includes 'COI Management Plans/', strip it to match user requirement
                    prefix = "Legal Business Units/COI Management/COI Management Plans/"
                    if display_file_name.startswith(prefix):
                        display_file_name = display_file_name[len(prefix):]
                    elif "/COI Management Plans/" in display_file_name:
                        display_file_name = display_file_name.split("/COI Management Plans/")[-1]
                    
                    modified_at_str = item["lastModifiedDateTime"] # ISO format
                    modified_at = datetime.fromisoformat(modified_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    
                    # Check if exists in DB
                    query_check = "SELECT pdf_id, modified_at, result_body, input_body FROM coi_mgmt.pdf_documents WHERE file_name = :file_name"
                    existing = await db.fetch_one(query_check, values={"file_name": display_file_name})
                    
                    pdf_id = None
                    re_process = False
                    if existing:
                        pdf_id = existing["pdf_id"]
                        db_modified_at = existing["modified_at"]
                        result_body_str = existing["result_body"]
                        db_input_body = existing["input_body"]
                        
                        has_answers = False
                        if result_body_str:
                            try:
                                res_json = json.loads(result_body_str)
                                if res_json.get("answers"):
                                    ans_list = res_json.get("answers", [])
                                    valid_count = sum(1 for a in ans_list if a.get("answer_text", "").upper() not in ["NA", "N/A", "NO", "NONE", ""])
                                    if valid_count > 0:
                                        has_answers = True
                            except: pass
                            
                        if not has_answers:
                            re_process = True
                            print(f"Re-processing {display_file_name} (Missing or invalid answers)")
                        elif not db_input_body:
                            re_process = True
                            print(f"Re-processing {display_file_name} (Missing input_body)")
                        elif db_modified_at and db_modified_at < modified_at:
                            re_process = True
                            print(f"Updating {display_file_name} (Modified)")
                        else:
                            print(f"Skipping {display_file_name} (Up to date)")
                            continue
                    else:
                        re_process = True
                        print(f"Processing new file: {display_file_name}")
 
                    if not re_process:
                        continue
 
                    # 2. Download and Process
                    download_url = item["@microsoft.graph.downloadUrl"]
                    file_content_resp = requests.get(download_url)
                    
                    temp_path = os.path.join("/tmp", raw_file_name) if os.name != 'nt' else os.path.join(os.environ["TEMP"], raw_file_name)
                    with open(temp_path, "wb") as f:
                        f.write(file_content_resp.content)
                    
                    # 3. AI Analysis (2-Pass Guardrail Strategy for PDF)
                    input_body = ""
                    if file_ext == ".pdf":
                        print(f"Using 2-Pass Guardrail Strategy for {display_file_name}...")
                        base64_imgs = pdf_to_base64_images(temp_path)
                        
                        # Pass 1: Raw OCR (Bypasses 'jailbreak' content filter)
                        raw_ocr_text = await ocr_document_visual(base64_imgs)
                        if not raw_ocr_text:
                            print(f"FAILED to extract raw text via OCR for {display_file_name}")
                            continue
                        
                        # Pass 2: Masked Structured Extraction (using existing text-based AI service)
                        ai_result = await analyze_document_and_answer(raw_ocr_text, QUESTIONS_DATA)
                        input_body = f"[2-Pass Guardrail Input: {min(len(base64_imgs), 8)} pages OCRed and analyzed]"
                    else:
                        extracted_text = extract_text(temp_path)
                        if not extracted_text:
                            print(f"Failed to extract text from {display_file_name}")
                            continue
                        ai_result = await analyze_document_and_answer(extracted_text, QUESTIONS_DATA)
                        input_body = extracted_text
                    
                    answers_data = ai_result.get("answers", [])
                    if not answers_data:
                        print(f"AI extraction failed for {display_file_name}")
                        continue

                    # Pluck Metadata Fields (IDs 101, 102, 103)
                    doc_date = "NA"
                    docusign_id = "NA"
                    from_user = "NA"
                    
                    final_answers = []
                    for ans in answers_data:
                        q_id = ans.get("question_id")
                        if q_id == 101: doc_date = ans.get("answer_text", "NA")
                        elif q_id == 102: docusign_id = ans.get("answer_text", "NA")
                        elif q_id == 103: from_user = ans.get("answer_text", "NA")
                        else:
                             final_answers.append(ans)

                    # 4. Store in DB
                    if existing:
                        query_upsert = """
                        UPDATE coi_mgmt.pdf_documents 
                        SET file_path = :file_path, modified_at = :modified_at, doc_date = :doc_date, 
                            docusign_id = :docusign_id, from_user = :from_user, result_body = :result_body,
                            input_body = :input_body
                        WHERE pdf_id = :pdf_id
                        """
                        await db.execute(query_upsert, values={
                            "pdf_id": pdf_id,
                            "file_path": item.get("webUrl", "sharepoint"),
                            "modified_at": modified_at,
                            "doc_date": doc_date,
                            "docusign_id": docusign_id,
                            "from_user": from_user,
                            "result_body": json.dumps({"answers": final_answers}),
                            "input_body": input_body
                        })
                    else:
                        query_upsert = """
                        INSERT INTO coi_mgmt.pdf_documents (file_name, file_path, modified_at, doc_date, docusign_id, from_user, result_body, input_body)
                        VALUES (:file_name, :file_path, :modified_at, :doc_date, :docusign_id, :from_user, :result_body, :input_body)
                        RETURNING pdf_id
                        """
                        pdf_id = await db.fetch_val(query_upsert, values={
                            "file_name": display_file_name,
                            "file_path": item.get("webUrl", "sharepoint"),
                            "modified_at": modified_at,
                            "doc_date": doc_date,
                            "docusign_id": docusign_id,
                            "from_user": from_user,
                            "result_body": json.dumps({"answers": final_answers}),
                            "input_body": input_body
                        })
                    
                    # 5. Process Answers (Vectorize & Store)
                    texts_to_embed = [ans.get("answer_text", "N/A") for ans in final_answers]
                    all_embeddings = await get_embeddings(texts_to_embed)
                    
                    if existing:
                        await db.execute("DELETE FROM coi_mgmt.pdf_answers WHERE pdf_id = :pdf_id", {"pdf_id": pdf_id})
                        await db.execute("DELETE FROM coi_mgmt.pdf_chunks WHERE pdf_id = :pdf_id", {"pdf_id": pdf_id})

                    query_ans = """
                    INSERT INTO coi_mgmt.pdf_answers (pdf_id, question_id, question_text, answer_text, answer_embedding)
                    VALUES (:pdf_id, :question_id, :question_text, :answer_text, :answer_embedding)
                    """
                    for i, ans in enumerate(final_answers):
                        await db.execute(query_ans, {
                            "pdf_id": pdf_id,
                            "question_id": ans["question_id"],
                            "question_text": ans["question_text"],
                            "answer_text": ans["answer_text"],
                            "answer_embedding": str(all_embeddings[i])
                        })
                    
                    # Process Chunks
                    chunks_to_index = [f"Question: {ans['question_text']}\nAnswer: {ans['answer_text']}" for ans in final_answers]
                    if chunks_to_index:
                        chunk_vectors = await get_embeddings(chunks_to_index)
                        query_chunk = """
                        INSERT INTO coi_mgmt.pdf_chunks (pdf_id, chunk_text, chunk_embedding, search_vector)
                        VALUES (:pdf_id, :chunk_text, :chunk_embedding, to_tsvector('english', :chunk_text))
                        """
                        for i, chunk in enumerate(chunks_to_index):
                            await db.execute(query_chunk, {
                                "pdf_id": pdf_id,
                                "chunk_text": chunk,
                                "chunk_embedding": str(chunk_vectors[i])
                            })
                    
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    processed_files.append(display_file_name)
                    log_event("SharePoint Sync", f"Processed {display_file_name}", "PROGRESS")
 
    await process_folder(target_folder_id, current_path="")
    await db.disconnect()
    log_event("SharePoint Sync", "Sync process complete", "SUCCESS")
    return processed_files

if __name__ == "__main__":
    asyncio.run(sync_sharepoint())

import msal
import requests
import os
import json
import asyncio
import re
from datetime import datetime
from dotenv import load_dotenv
from databases import Database
import urllib.parse

# Local imports
from app.utils.doc_extraction import extract_text, pdf_to_base64_images
from app.services.ai import analyze_document_and_answer, get_embeddings, ocr_document_visual
from app.questions import QUESTIONS_DATA
from app.utils.logger import log_event

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
encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

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

async def force_resync_broken_files():
    db = Database(DATABASE_URL)
    await db.connect()
    
    # 1. Identify broken records
    print("Identifying broken records in DB...")
    query_broken = "SELECT file_name, pdf_id FROM coi_mgmt.pdf_documents WHERE from_user = 'NA' OR input_body LIKE '[Hybrid %'"
    broken_rows = await db.fetch_all(query_broken)
    broken_files = {row['file_name']: row['pdf_id'] for row in broken_rows}
    print(f"Found {len(broken_files)} records to force-resync.")

    if not broken_files:
        await db.disconnect()
        return

    token = await get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    target_folder_path = "COI Management/COI Management Plans"
    encoded_path = target_folder_path.replace(" ", "%20")
    resolve_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root:/{encoded_path}"
    
    resolve_resp = requests.get(resolve_url, headers=headers)
    if resolve_resp.status_code != 200:
        print(f"Could not resolve folder: {resolve_resp.text}")
        await db.disconnect()
        return
        
    target_folder_id = resolve_resp.json().get("id")

    async def process_folder_recursive(folder_id, current_path=""):
        url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{folder_id}/children"
        while url:
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200: break
            data = resp.json()
            for item in data.get("value", []):
                item_name = item["name"]
                if "folder" in item:
                    new_path = f"{current_path}/{item_name}" if current_path else item_name
                    await process_folder_recursive(item["id"], new_path)
                else:
                    display_name = f"{current_path}/{item_name}" if current_path else item_name
                    
                    # FUZZY MATCHING: Check if this file needs resync by comparing stripped names
                    clean_display_name = display_name
                    if "COI Management Plans/" in clean_display_name:
                        clean_display_name = clean_display_name.split("COI Management Plans/")[-1]
                    
                    pdf_id = None
                    if display_name in broken_files:
                        pdf_id = broken_files[display_name]
                    elif clean_display_name in broken_files:
                        pdf_id = broken_files[clean_display_name]
                    
                    if pdf_id:
                        print(f"Force-resyncing: {display_name} (Resolved ID: {pdf_id})")
                        
                        # Download
                        download_url = item["@microsoft.graph.downloadUrl"]
                        f_resp = requests.get(download_url)
                        temp_path = os.path.join(os.environ.get("TEMP", "/tmp"), item_name)
                        with open(temp_path, "wb") as f:
                            f.write(f_resp.content)
                            
                        # Extract logic (Visual OCR forced)
                        print(f"  -> Performing Visual OCR...")
                        base64_imgs = pdf_to_base64_images(temp_path)
                        raw_ocr_text = await ocr_document_visual(base64_imgs)
                        
                        if raw_ocr_text:
                            print(f"  -> Extracting Metadata via AI...")
                            ai_result = await analyze_document_and_answer(raw_ocr_text, QUESTIONS_DATA)
                            
                            doc_date = "NA"
                            docusign_id = "NA"
                            from_user = "NA"
                            company_name = "NA"
                            answers_data = ai_result.get("answers", [])
                            
                            final_answers = []
                            for ans in answers_data:
                                q_id = ans.get("question_id")
                                if q_id == 101: doc_date = ans.get("answer_text", "NA")
                                elif q_id == 102: docusign_id = ans.get("answer_text", "NA")
                                elif q_id == 103: from_user = ans.get("answer_text", "NA")
                                elif q_id == 104: company_name = ans.get("answer_text", "NA")
                                else: final_answers.append(ans)
                            
                            # --- AGGRESSIVE EXTRACTION PASS IF NA ---
                            if from_user == "NA" or not from_user:
                                print(f"  -> First pass NA. Triggering Aggressive GPT-5 Vision extraction...")
                                aggressive_q = {
                                    "QUESTIONS_DATA": {
                                        "global_instructions": "Identify the HUMAN RESEARCHER SUBJECT of this COI management plan. This is the person the rules apply to.",
                                        "QUESTIONS": [
                                            {
                                                "id": 103,
                                                "text": "Metadata: FROM",
                                                "prompt": "Look for names after 'FROM:', 'Subject:', 'Signed by:', or in the first paragraph ('This plan applies to [NAME]'). Ignore hospital names. Format as 'Lastname Firstname'. Return ONLY name or NA."
                                            }
                                        ]
                                    }
                                }
                                # Use visual logic for maximum fidelity
                                agg_res = await ocr_document_visual(base64_imgs) # Get deep OCR again if needed, or just re-extract from text
                                if agg_res:
                                    # Call AI again with extra instructions
                                    agg_ai = await analyze_document_and_answer(raw_ocr_text, aggressive_q)
                                    if agg_ai.get("answers"):
                                        from_user = agg_ai["answers"][0].get("answer_text", "NA")
                                        print(f"  -> Aggressive PasS SUCCESS: '{from_user}'")

                            
                            # Update DB
                            update_query = """
                                UPDATE coi_mgmt.pdf_documents
                                SET from_user = :from_user,
                                    input_body = :input_body,
                                    doc_date = :doc_date,
                                    docusign_id = :docusign_id,
                                    company = :company
                                WHERE pdf_id = :pdf_id
                            """
                            await db.execute(update_query, {
                                "from_user": from_user,
                                "input_body": raw_ocr_text,
                                "doc_date": doc_date,
                                "docusign_id": docusign_id,
                                "company": company_name,
                                "pdf_id": pdf_id
                            })
                            print(f"  -> SUCCESS: '{from_user}'")
                        else:
                            print(f"  -> FAILED: OCR failed for {display_name}")
                            
                        if os.path.exists(temp_path): os.remove(temp_path)
                        await asyncio.sleep(1) # Rate limit protection
            
            url = data.get("@odata.nextLink")

    await process_folder_recursive(target_folder_id)
    await db.disconnect()
    print("Force re-sync complete.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(force_resync_broken_files())

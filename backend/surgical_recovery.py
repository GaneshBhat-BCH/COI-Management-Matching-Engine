import msal
import requests
import os
import asyncio
import urllib.parse
from dotenv import load_dotenv
from databases import Database

# Local imports
from app.utils.doc_extraction import pdf_to_base64_images
from app.services.ai import analyze_document_and_answer, ocr_document_visual

# Load .env
dotenv_path = os.path.join(os.getcwd(), 'app', '.env')
load_dotenv(dotenv_path)

CLIENT_ID = os.getenv("SP_CLIENT_ID")
CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET")
TENANT_ID = os.getenv("SP_TENANT_ID")
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

app = msal.ConfidentialClientApplication(CLIENT_ID, authority=authority, client_credential=CLIENT_SECRET)
token = app.acquire_token_for_client(scopes=scope).get("access_token")
headers = {"Authorization": f"Bearer {token}"}

SURGICAL_FILES = [
    {
        "id": "01E6JN7TWWE4ZJFTEXQJALGM3VVOX6Z36J",
        "name": "Zon_COI_mgmtplan_2009.pdf",
        "file_name_in_db": "Zon - 001/Zon_COI_mgmtplan_2009.pdf"
    },
    {
        "id": "01E6JN7TVPLEK3SQDFSVF2SYYBUYTEK7TZ",
        "name": "Signed BCH Conflict Management.pdf",
        "file_name_in_db": "Zhang, Yi/Signed BCH Conflict Management.pdf"
    }
]

# Targeted Page 1 Question Logic
PAGE_1_QUEST_DATA = {
    "global_instructions": "Identify the HUMAN RESEARCHER SUBJECT of this institutional record. Look specifically at the first page.",
    "QUESTIONS": [
        {
            "id": 103,
            "text": "Researcher Name",
            "prompt": "Identify the primary researcher this management plan is for. Look for 'RE:', 'FROM:', 'Subject:', or the introductory paragraph stating 'This plan applies to [NAME]'. Format as 'Lastname Firstname'. Return ONLY name or NA."
        }
    ]
}

async def run_surgical_recovery():
    db = Database(DATABASE_URL)
    await db.connect()
    
    for item in SURGICAL_FILES:
        print(f"\nProcessing Surgical Item: {item['name']}")
        
        # 1. Download directly by ID
        download_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{item['id']}/content"
        f_resp = requests.get(download_url, headers=headers)
        
        if f_resp.status_code != 200:
            print(f"FAILED to download {item['name']}: {f_resp.text}")
            continue
            
        temp_path = os.path.join(os.environ.get("TEMP", "/tmp"), item["name"])
        with open(temp_path, "wb") as f:
            f.write(f_resp.content)
            
        # 2. Page 1 Vision OCR
        print(f"  -> Performing Surgical Page 1 Vision OCR...")
        base64_imgs = pdf_to_base64_images(temp_path)
        if not base64_imgs:
            print(f"  -> FAILED to extract images from {item['name']}")
            continue
            
        # Only take the first page image
        first_page_imgs = [base64_imgs[0]]
        
        raw_ocr_text = await ocr_document_visual(first_page_imgs)
        
        if raw_ocr_text:
            print(f"  -> Extracting Name via Focused AI...")
            ai_result = await analyze_document_and_answer(raw_ocr_text, PAGE_1_QUEST_DATA)
            from_user = "NA"
            for ans in ai_result.get("answers", []):
                if ans.get("question_id") == 103:
                    from_user = ans.get("answer_text", "NA")
            
            # 3. Force update DB
            update_query = """
                UPDATE coi_mgmt.pdf_documents
                SET from_user = :from_user,
                    input_body = :input_body
                WHERE file_name = :file_name_in_db
            """
            await db.execute(update_query, {
                "from_user": from_user,
                "input_body": raw_ocr_text,
                "file_name_in_db": item["file_name_in_db"]
            })
            print(f"  -> SUCCESS: '{from_user}'")
            
        if os.path.exists(temp_path): os.remove(temp_path)

    await db.disconnect()
    print("\nSurgical recovery complete.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_surgical_recovery())

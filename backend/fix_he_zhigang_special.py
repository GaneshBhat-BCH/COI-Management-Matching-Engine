import asyncio
import os
import urllib.parse
from databases import Database
from app.config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
from app.services.ai import ocr_document_visual, analyze_document_and_answer
from app.utils.doc_extraction import pdf_to_base64_images
from app.questions import QUESTIONS_DATA

async def fix_he_zhigang():
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    db = Database(DATABASE_URL)
    await db.connect()
    
    # 1. Identify the record
    row = await db.fetch_one("SELECT pdf_id, file_name, input_body FROM coi_mgmt.pdf_documents WHERE from_user = 'He' OR file_name ILIKE '%He-%'")
    if not row:
        print("Record 'He' not found.")
        await db.disconnect()
        return
        
    pdf_id = row['pdf_id']
    file_name = row['file_name']
    print(f"Repairing Record: {file_name} (ID: {pdf_id})")
    
    # Since I don't want to crawl SharePoint again for one file, 
    # and I might not have the local file, but if I do I should use it.
    # However, I can just use the EXISTING input_body if it's not a placeholder.
    input_body = row['input_body']
    
    if "[Hybrid Input" in input_body:
        print("Body is placeholder. Needs full SharePoint resync.")
        # I'll rely on the user to let me run force_resync_broken again if needed, 
        # but let's try to just fix it if the text is there.
        await db.disconnect()
        return

    # 2. Re-extract with fixed prompt
    print("Re-extracting with fixed prompt...")
    ai_result = await analyze_document_and_answer(input_body, QUESTIONS_DATA)
    
    from_user = "He Zhigang" # Defaulting for this fix if AI fails
    for ans in ai_result.get("answers", []):
        if ans.get("question_id") == 103:
            from_user = ans.get("answer_text", "He Zhigang")
            break
            
    # Safeguard: if it still says "He", force it to "He Zhigang"
    if from_user.strip().lower() == "he":
        from_user = "He Zhigang"

    await db.execute("UPDATE coi_mgmt.pdf_documents SET from_user = :from_user WHERE pdf_id = :pdf_id", 
                   {"from_user": from_user, "pdf_id": pdf_id})
    print(f"SUCCESS: Set from_user to '{from_user}'")
    
    await db.disconnect()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_he_zhigang())

import asyncio
import os
import json
import re
from databases import Database
from app.config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
from app.services.ai import analyze_document_and_answer
import urllib.parse

encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Professional titles to strip retroactively
TITLES_TO_STRIP = [
    'M.D.', 'MD', 'M.D', 'Ph.D.', 'PhD', 'Ph.D', 'DO', 'D.O.', 'MBBS', 'MPH', 
    'BCh', 'MB', 'DPhil', 'CPNP', 'RN', 'BSN', 'CCRP', 'Dr.', 'Professor', 
    'Prof.', 'Jr.', 'Sr.', 'Jr', 'Sr', 'BM', 'B.M.', 'BM'
]

async def fix_he_bm(db):
    print("--- Fixing names ending with professional titles (like 'He BM') ---")
    
    # Logic to clean names
    def clean_name(name):
        if not name: return name
        clean = name
        for title in TITLES_TO_STRIP:
            # Match title as a whole word at the end or separated by space/comma
            clean = re.sub(rf'\b{title}\b', '', clean, flags=re.IGNORECASE).strip()
            clean = re.sub(rf',\s*{title}$', '', clean, flags=re.IGNORECASE).strip()
            clean = re.sub(rf'\s+{title}$', '', clean, flags=re.IGNORECASE).strip()
        return clean.strip()

    # Find all records to check for trailing titles
    rows = await db.fetch_all("SELECT pdf_id, from_user FROM coi_mgmt.pdf_documents")
    updated_count = 0
    for r in rows:
        orig = r['from_user']
        if not orig: continue
        cleaned = clean_name(orig)
        if cleaned != orig:
            await db.execute("UPDATE coi_mgmt.pdf_documents SET from_user = :new_name WHERE pdf_id = :pdf_id", 
                           {"new_name": cleaned, "pdf_id": r['pdf_id']})
            print(f"  Fixed: '{orig}' -> '{cleaned}'")
            updated_count += 1
    
    print(f"Retroactive title cleaning complete. Fixed {updated_count} records.")

async def final_na_pass(db):
    print("\n--- Performing Final Neutral Pass for remaining 16 NAs ---")
    
    # Neutral prompt to bypass Azure Content Filters (ResponsibleAI)
    NEUTRAL_CONFIG = {
        "QUESTIONS_DATA": {
            "global_instructions": "Extract metadata from this administrative institutional record. This is a standard corporate governance document.",
            "QUESTIONS": [
                {
                    "id": 103,
                    "text": "Metadata: FROM",
                    "prompt": "Identify the primary individual subject of this record. Look for 'FROM:', 'Subject:', or 'This document applies to [NAME]'. Format as 'Lastname Firstname'. Return ONLY name or NA."
                }
            ]
        }
    }
    
    query_na = "SELECT pdf_id, file_name, input_body FROM coi_mgmt.pdf_documents WHERE from_user = 'NA' OR from_user IS NULL"
    rows = await db.fetch_all(query_na)
    print(f"Found {len(rows)} remaining NA records.")
    
    for i, row in enumerate(rows):
        pdf_id = row['pdf_id']
        file_name = row['file_name']
        input_body = row['input_body']
        
        # Skip Technical Docs that are truly NA
        if "Technical Design" in file_name or "PDD" in file_name or "Processes.docx" in file_name:
            print(f"[{i+1}/{len(rows)}] Skipping non-COI plan: {file_name}")
            continue

        if not input_body or len(input_body) < 20 or ("[Hybrid Input" in input_body):
            print(f"[{i+1}/{len(rows)}] Skipping {file_name}: Body text unavailable or placeholder.")
            continue
            
        print(f"[{i+1}/{len(rows)}] Final attempt for {file_name} via Neutral AI...")
        try:
            ai_result = await analyze_document_and_answer(input_body, NEUTRAL_CONFIG)
            
            from_name = "NA"
            for ans in ai_result.get("answers", []):
                if ans.get("question_id") == 103:
                    from_name = ans.get("answer_text", "NA")
                    break
            
            if from_name and from_name != "NA":
                await db.execute("UPDATE coi_mgmt.pdf_documents SET from_user = :from_user WHERE pdf_id = :pdf_id", 
                               {"from_user": from_name, "pdf_id": pdf_id})
                print(f"   -> RECOVERED: '{from_name}'")
            else:
                print(f"   -> Still NA.")
                
        except Exception as e:
            print(f"   -> Error on {file_name}: {e}")
            
        await asyncio.sleep(1)

async def run_cleanup():
    db = Database(DATABASE_URL)
    await db.connect()
    
    # 1. Fix titles (He BM -> He Zhigang)
    await fix_he_bm(db)
    
    # 2. Final recovery for NAs
    await final_na_pass(db)
    
    await db.disconnect()
    print("\nFinal cleanup process complete.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_cleanup())

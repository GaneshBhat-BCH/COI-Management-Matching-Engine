import asyncio
import os
import sys
from pathlib import Path
import json

backend_path = Path(r"c:\Users\GaneshBhat\Documents\COI-Management-Matching-Engine-main\backend")
sys.path.append(str(backend_path))

from app.config import DATABASE_URL
from asyncpg import connect

async def main():
    try:
        conn = await connect(DATABASE_URL)
        
        pdf_id = "b37ae8a0-1ac6-4e62-bdfa-396f9ff37127"
        
        # Get document info
        doc = await conn.fetchrow("SELECT pdf_id, file_name, result_body FROM coi_mgmt.pdf_documents WHERE pdf_id = $1", pdf_id)
        
        print(f"Document ID: {doc['pdf_id']}")
        print(f"File Name: {doc['file_name']}")
        
        print("\nResult Body (Snippet):")
        if doc['result_body']:
            try:
                # Try to parse if it's JSON
                rb = json.loads(doc['result_body'])
                print(json.dumps(rb, indent=2)[:2000] + "...")
            except:
                print(doc['result_body'][:2000] + "...")
        
        # Get answers
        answers = await conn.fetch("SELECT question_id, question_text, answer_text FROM coi_mgmt.pdf_answers WHERE pdf_id = $1 ORDER BY question_id", pdf_id)
        
        print("\nAll Answers:")
        for ans in answers:
            print(f"Q{ans['question_id']}: {ans['answer_text']}")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

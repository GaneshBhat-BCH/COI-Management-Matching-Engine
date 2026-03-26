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
        query = """
        SELECT d.file_name,
               count(CASE WHEN a.answer_text NOT ILIKE 'NA' 
                          AND a.answer_text NOT ILIKE 'N/A'
                          AND a.answer_text IS NOT NULL
                          AND a.answer_text != '' THEN 1 END) as score
        FROM coi_mgmt.pdf_documents d
        JOIN coi_mgmt.pdf_answers a ON d.pdf_id = a.pdf_id
        GROUP BY d.pdf_id, d.file_name
        HAVING count(CASE WHEN a.answer_text NOT ILIKE 'NA' 
                          AND a.answer_text NOT ILIKE 'N/A'
                          AND a.answer_text IS NOT NULL
                          AND a.answer_text != '' THEN 1 END) >= 12
        ORDER BY score DESC, d.file_name
        """
        results = await conn.fetch(query)
        
        output_file = Path(r"C:\Users\GaneshBhat\.gemini\antigravity\brain\edde625e-aab9-4594-9f8b-5f7d60ff7288\matches_80.json")
        matches = [{"file_name": r['file_name'], "score": r['score']} for r in results]
        
        with open(output_file, 'w') as f:
            json.dump(matches, f, indent=2)
            
        print(f"Successfully saved {len(matches)} matches to {output_file}")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

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
        
        # Check for other common 'null-like' strings
        query = """
        SELECT d.pdf_id, d.file_name, a.answer_text
        FROM coi_mgmt.pdf_documents d
        JOIN coi_mgmt.pdf_answers a ON d.pdf_id = a.pdf_id
        WHERE a.answer_text ILIKE 'not applicable'
           OR a.answer_text ILIKE 'none'
           OR a.answer_text ILIKE 'n.a.'
        LIMIT 10
        """
        results = await conn.fetch(query)
        print("Other possible null-like values found:")
        for r in results:
            print(f"File: {r['file_name']}, Answer: {r['answer_text']}")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

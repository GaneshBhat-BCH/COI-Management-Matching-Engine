import asyncio
import os
import sys
from pathlib import Path

# Add backend to path to import app.config
backend_path = Path(r"c:\Users\GaneshBhat\Documents\COI-Management-Matching-Engine-main\backend")
sys.path.append(str(backend_path))

from app.config import DATABASE_URL
from asyncpg import connect

async def main():
    print(f"Connecting to database...")
    try:
        conn = await connect(DATABASE_URL)
        print("Connected.")

        # Query: Find pdf_ids where >= 12 (80% of 15) of the answers are NOT 'NA' or 'N/A'
        query = """
        SELECT d.pdf_id, d.file_name, count(a.id) as total_ans,
               count(CASE WHEN a.answer_text NOT ILIKE 'NA' 
                          AND a.answer_text NOT ILIKE 'N/A'
                          AND a.answer_text IS NOT NULL
                          AND a.answer_text != '' THEN 1 END) as valid_ans_count
        FROM coi_mgmt.pdf_documents d
        JOIN coi_mgmt.pdf_answers a ON d.pdf_id = a.pdf_id
        GROUP BY d.pdf_id, d.file_name
        HAVING count(CASE WHEN a.answer_text NOT ILIKE 'NA' 
                          AND a.answer_text NOT ILIKE 'N/A'
                          AND a.answer_text IS NOT NULL
                          AND a.answer_text != '' THEN 1 END) >= 12
        ORDER BY valid_ans_count DESC, d.file_name
        """
        
        results = await conn.fetch(query)
        
        print(f"\nFound {len(results)} documents with at least 80% (12/15) non-NA answers:\n")
        print(f"{'File Name':<60} | {'Valid Ans':<10} | {'Total Ans':<10} | {'%':<5}")
        print("-" * 90)
        for row in results:
            percentage = (row['valid_ans_count'] / row['total_ans']) * 100 if row['total_ans'] > 0 else 0
            print(f"{row['file_name'][:58]:<60} | {row['valid_ans_count']:<10} | {row['total_ans']:<10} | {percentage:,.1f}%")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

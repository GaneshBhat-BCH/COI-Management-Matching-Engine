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

        # Query 1: Total documents
        total_docs = await conn.fetchval("SELECT count(*) FROM coi_mgmt.pdf_documents")
        print(f"Total documents: {total_docs}")

        # Query 2: Find pdf_ids where NONE of the answers are 'NA' or 'N/A'
        # We look for pdf_ids that are NOT in the set of pdf_ids having at least one 'NA'/'N/A'
        query = """
        SELECT d.pdf_id, d.file_name
        FROM coi_mgmt.pdf_documents d
        WHERE d.pdf_id NOT IN (
            SELECT DISTINCT pdf_id 
            FROM coi_mgmt.pdf_answers 
            WHERE answer_text ILIKE 'NA' 
               OR answer_text ILIKE 'N/A'
               OR answer_text IS NULL
               OR answer_text = ''
        )
        AND EXISTS (SELECT 1 FROM coi_mgmt.pdf_answers a WHERE a.pdf_id = d.pdf_id)
        """
        
        results = await conn.fetch(query)
        
        print(f"\nFound {len(results)} documents with no 'NA' or 'N/A' answers:\n")
        for row in results:
            print(f"ID: {row['pdf_id']}, File: {row['file_name']}")

        # Query 3: Sample an 'NA' document for comparison
        sample_query = """
        SELECT d.pdf_id, d.file_name, count(a.id) as total_ans, 
               count(CASE WHEN a.answer_text ILIKE 'NA' OR a.answer_text ILIKE 'N/A' THEN 1 END) as na_count
        FROM coi_mgmt.pdf_documents d
        JOIN coi_mgmt.pdf_answers a ON d.pdf_id = a.pdf_id
        GROUP BY d.pdf_id, d.file_name
        LIMIT 5
        """
        samples = await conn.fetch(sample_query)
        print("\nSample counts (First 5):")
        for s in samples:
            print(f"File: {s['file_name']}, Total Answers: {s['total_ans']}, NA Count: {s['na_count']}")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

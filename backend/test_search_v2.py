import asyncio
import os
import sys
import json

# Add current directory to path
sys.path.append(os.getcwd())

from app.routers.search import SearchRequest, SearchItem, search_documents
from app.database import Database

async def test_search():
    print("--- TESTING SEARCH OVERHAUL (v2) ---")
    
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    db = Database(DATABASE_URL)
    await db.connect()
    
    try:
        # Search scenario
        qa_list = [
            SearchItem(question="Is the researcher a cofounder in a company outside of BCH?", answer="Yes"),
            SearchItem(question="What is the researcher’s equity in the company?", answer="StockOptions")
        ]
        request = SearchRequest(user_id="overhaul_test", questions_answers=qa_list)
        
        results = await search_documents(request, db)
        
        print(f"\nRESULTS FOUND: {len(results['results'])}")
        
        # Check first result for Mismatch handling
        res = results['results'][0]
        print(f"\nFILE: {res['pdf_name']}")
        print(f"SCORE: {res['match_score']}")
        
        print("\nMATCHED QAs:")
        for m in res['matched_qa']:
            print(f"- {m['question']}: {m['pdf_answer']} [OK]")
            
        print("\nUNMATCHED QAs (SHOULD CONTAIN MISMATCHES):")
        for u in res['unmatched_qa']:
             print(f"- {u['question']}: {u['pdf_answer']} [MISMATCH]")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_search())

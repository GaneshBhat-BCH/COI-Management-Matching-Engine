import asyncio
import os
import sys
import time

# Add current directory to path
sys.path.append(os.getcwd())

from app.routers.search import SearchRequest, SearchItem, search_documents
from app.database import Database

async def test_performance():
    print("--- TESTING SEARCH PERFORMANCE (BATCH SEMANTIC) ---")
    
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    db = Database(DATABASE_URL)
    await db.connect()
    
    try:
        # Search for BOD
        qa_list = [
            SearchItem(question="Is the researcher a cofounder in a company outside of BCH?", answer="Yes"),
            SearchItem(question="What is the researcher’s equity in the company?", answer="StockOptions")
        ]
        request = SearchRequest(user_id="perf_test", questions_answers=qa_list)
        
        start_time = time.time()
        results = await search_documents(request, db)
        end_time = time.time()
        
        # Search results are inside the "results" key
        results_list = results.get("results", [])
        print(f"RESULTS FOUND: {len(results_list)}")
        
        # Verify result quality
        for res in results_list[:3]:
            print(f"- {res['pdf_name']} (Score: {res['match_score']})")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_performance())

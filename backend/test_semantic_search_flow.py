import asyncio
import os
import sys
import json

# Add current directory to path
sys.path.append(os.getcwd())

from app.services.ai import is_semantic_equivalent
from app.routers.search import SearchRequest, SearchItem, search_documents
from app.database import Database

async def test_semantic():
    print("--- TESTING SEMANTIC AI BRIDGE ---")
    
    test_cases = [
        ("SAB", "Scientific Advisory Board Member"),
        ("BOD", "Board of Directors"),
        ("Rule 1d", "I(d) Rule"),
        ("Buness decvlopmnet Admin", "Business Development Administrator")
    ]
    
    for term1, term2 in test_cases:
        result = await is_semantic_equivalent(term1, term2)
        print(f"Match '{term1}' vs '{term2}'? -> {'✅ YES' if result else '❌ NO'}")

    print("\n--- RUNNING FULL SEARCH TEST (BOD Scenario) ---")
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
            SearchItem(question="What is the researcher’s role(s)/title(s) in the company?", answer="BOD")
        ]
        request = SearchRequest(user_id="test_user", questions_answers=qa_list)
        
        results = await search_documents(request, db)
        print(f"\nRESULTS FOUND: {len(results)}")
        
        # Look for 'BOD' -> 'Board of Directors' in the matched_qa details
        for res in results[:2]:
            print(f"- {res['pdf_name']} (Score: {res['match_score']})")
            for m in res['matched_qa']:
                if m['match_type'] == "Match (Semantic AI)":
                    print(f"  ✅ Semantic Match: '{m['user_answer_ref']}' -> '{m['pdf_answer']}'")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_semantic())

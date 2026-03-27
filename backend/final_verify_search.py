import asyncio
import os
import sys
import json

# Add current directory to path
sys.path.append(os.getcwd())

from app.routers.search import SearchRequest, SearchItem, search_documents
from app.database import Database

async def test_search():
    print("--- FINAL SYSTEM VERIFICATION (Search v2) ---")
    
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    db = Database(DATABASE_URL)
    await db.connect()
    
    try:
        # Search scenario mimicking user screenshot
        qa_list = [
            SearchItem(question="Is the researcher a cofounder in a company outside of BCH?", answer="Yes"),
            SearchItem(question="What COI rule applies to this management plan?", answer="[]"), # Simulating empty/bracket input
            SearchItem(question="What is the researcher’s equity in the company?", answer="[StockOptions]") # Simulating bracketed input
        ]
        request = SearchRequest(user_id="final_test", questions_answers=qa_list)
        
        print(f"Executing search for: Q1='Yes', QRule='[]', QEquity='[StockOptions]'...")
        results = await search_documents(request, db)
        
        results_list = results.get("results", [])
        print(f"\nTOTAL PDFs FOUND: {len(results_list)}")
        
        for i, res in enumerate(results_list[:3]):
            if res['pdf_name'] == "No Data Found":
                print(f"{i+1}. [Empty Placeholder]")
                continue
                
            print(f"\n{i+1}. FILE: {res['pdf_name']}")
            print(f"   SCORE: {res['match_score']} ({res['weightage_details']})")
            print(f"   METHOD: {res['search_method']}")
            
            print("   MATCHES:")
            for m in res['matched_qa']:
                print(f"   - {m['question'][:40]}... -> {m['pdf_answer']} [OK: {m['match_type']}]")
                
            print("   MISMATCHES:")
            for u in res['unmatched_qa']:
                 # Verify score_earned is 0 for mismatches
                 indicator = "RED" if u.get('score_earned', 0) == 0 else "ERROR (SHOULD BE RED)"
                 print(f"   - {u['question'][:40]}... -> {u['pdf_answer']} [{indicator}]")

    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_search())

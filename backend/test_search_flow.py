import asyncio
import os
import sys
import json

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from app.routers.search import SearchRequest, SearchItem
from app.database import get_db

async def test_search():
    from app.questions import QUESTIONS
    
    # Construct the specific target query
    # Q1 text: "Is the researcher a cofounder in a company outside of BCH?"
    # Q4 text: "What is the researcher’s equity in the company?"
    
    qa_list = [
        SearchItem(question="Is the researcher a cofounder in a company outside of BCH?", answer="yes"),
        SearchItem(question="What is the researcher’s equity in the company?", answer="[StockOptions]"),
        # Other questions blank/NA
    ]
    
    # Add dummy entries for the rest to match the user's typical full payload
    for q in QUESTIONS:
        q_text = q["text"]
        if q_text not in [it.question for it in qa_list]:
            qa_list.append(SearchItem(question=q_text, answer="NA"))

    request = SearchRequest(user_id="test_user", questions_answers=qa_list)
    
    print(f"Testing Search with Q1='yes' and Q4='StockOptions'...")
    
    # We need to mock 'Depends(get_db)' or just get it directly
    from app.database import Database
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    db = Database(DATABASE_URL)
    await db.connect()
    
    try:
        # We'll call the search function directly
        from app.routers.search import search_documents
        results = await search_documents(request, db)
        
        print(f"\nRESULTS FOUND: {len(results)}")
        with open("search_debug_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("Detailed results written to search_debug_results.json")
                
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_search())

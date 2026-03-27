import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from app.database import Database

async def list_roles():
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    db = Database(DATABASE_URL)
    await db.connect()
    
    try:
        # Get Q2 (Role) and Q14 (Rule) to see if we have good semantic test cases
        query = "SELECT pdf_id, question_id, answer_text FROM coi_mgmt.pdf_answers WHERE question_id IN (2, 14) LIMIT 20"
        rows = await db.fetch_all(query)
        
        print("\n--- ROLES & RULES IN DB ---")
        for r in rows:
            q_type = "ROLE" if r["question_id"] == 2 else "RULE"
            print(f"- {q_type}: {r['answer_text']}")
            
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(list_roles())

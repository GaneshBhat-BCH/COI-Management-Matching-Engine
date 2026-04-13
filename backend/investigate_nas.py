import asyncio
import urllib.parse
from databases import Database
from app.config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

async def investigate_remaining_nas():
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    db = Database(DATABASE_URL)
    await db.connect()
    
    query = "SELECT file_name, from_user, input_body FROM coi_mgmt.pdf_documents WHERE from_user = 'NA'"
    rows = await db.fetch_all(query)
    print(f"Investigating {len(rows)} remaining NA records:")
    
    for row in rows:
        body = row['input_body']
        body_start = body[:100].replace('\n', ' ') if body else "EMPTY"
        print(f"File: {row['file_name']}")
        print(f"  Body Preview: {body_start}...")
        print("-" * 20)
        
    await db.disconnect()

if __name__ == "__main__":
    import os
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(investigate_remaining_nas())

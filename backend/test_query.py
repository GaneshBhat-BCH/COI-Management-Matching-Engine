import asyncio
import urllib.parse
from databases import Database
from app.config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

async def main():
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    db = Database(DATABASE_URL)
    await db.connect()
    
    query = "SELECT file_name, from_user FROM coi_mgmt.pdf_documents WHERE from_user = 'NA'"
    rows = await db.fetch_all(query)
    print(f"Total NA count: {len(rows)}")
    for r in rows[:10]:
        print(f"  - {r['file_name']}")
        
    await db.disconnect()

if __name__ == "__main__":
    import os
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

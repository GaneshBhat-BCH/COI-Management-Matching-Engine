import asyncio
import os
from databases import Database
from dotenv import load_dotenv

# Load env from backend/app/.env
parent_dir = os.path.dirname(os.getcwd())
dotenv_path = os.path.join(os.getcwd(), 'app', '.env')
load_dotenv(dotenv_path)

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

async def run_migration():
    database = Database(DATABASE_URL)
    await database.connect()
    
    queries = [
        "ALTER TABLE coi_mgmt.pdf_documents ADD COLUMN IF NOT EXISTS modified_at TIMESTAMP;",
        "ALTER TABLE coi_mgmt.pdf_documents ADD COLUMN IF NOT EXISTS doc_date TEXT;",
        "ALTER TABLE coi_mgmt.pdf_documents ADD COLUMN IF NOT EXISTS docusign_id TEXT;",
        "ALTER TABLE coi_mgmt.pdf_documents ADD COLUMN IF NOT EXISTS from_user TEXT;"
    ]
    
    print("Running migration...")
    for query in queries:
        try:
            await database.execute(query)
            print(f"Executed: {query}")
        except Exception as e:
            print(f"Error executing {query}: {e}")
            
    await database.disconnect()
    print("Migration complete.")

if __name__ == "__main__":
    asyncio.run(run_migration())

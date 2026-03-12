import asyncio
import json
import os
from databases import Database

# Try explicit connection string
DATABASE_URL = "postgresql://postgres:password@127.0.0.1:5432/coi_db" 
# Note: I am guessing the password/db name based on typical defaults if .env is missing. 
# But wait, backend/database.py loads .env. I should try to load it too.

from dotenv import load_dotenv
load_dotenv()

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1") # Force IPv4
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "coi_db")

# Construct URL
encoded_password = DB_PASSWORD # Simplified for debug
url = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
print(f"Connecting to: {url}")

database = Database(url)

async def inspect():
    await database.connect()
    print("Connected!")
    query = "SELECT query_id, agent_answer, created_at FROM coi_mgmt.user_queries ORDER BY created_at DESC LIMIT 1"
    row = await database.fetch_one(query)
    if row:
        print(f"Query ID: {row['query_id']}")
        print(f"Created: {row['created_at']}")
        data = json.loads(row['agent_answer'])
        print(json.dumps(data, indent=2))
    else:
        print("No row")
    await database.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(inspect())
    except Exception as e:
        print(f"Failed: {e}")

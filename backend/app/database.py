from app.config import DATABASE_URL
from databases import Database

database = Database(DATABASE_URL)

async def get_db():
    # Connection is managed by FastAPI startup/shutdown events in main.py
    return database

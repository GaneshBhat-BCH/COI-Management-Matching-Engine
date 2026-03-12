import asyncio
from backend.database import database

async def update_schema():
    print("Connecting to database...")
    await database.connect()
    
    try:
        print("Dropping old table...")
        await database.execute("DROP TABLE IF EXISTS coi_mgmt.user_queries;")
        
        print("Creating new table...")
        create_query = """
        CREATE TABLE IF NOT EXISTS coi_mgmt.user_queries (
            query_id BIGSERIAL PRIMARY KEY,
            user_id TEXT,
            input_json JSONB,
            agent_answer JSONB,
            query_type JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        await database.execute(create_query)
        print("Schema update complete successfully.")
        
    except Exception as e:
        print(f"Error updating schema: {e}")
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(update_schema())

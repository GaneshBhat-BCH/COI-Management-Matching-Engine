import asyncio
import json
from backend.database import database

async def inspect_latest_query():
    print("Connecting to database...")
    await database.connect()
    
    try:
        query = """
        SELECT query_id, input_json, agent_answer, query_type, created_at 
        FROM coi_mgmt.user_queries 
        ORDER BY created_at DESC LIMIT 1
        """
        row = await database.fetch_one(query)
        
        if row:
            print(f"--- Query ID: {row['query_id']} ---")
            print(f"Created At: {row['created_at']}")
            print(f"Query Type Map: {row['query_type']}")
            
            agent_answer = json.loads(row['agent_answer'])
            print("\n--- Agent Answer Analysis ---")
            for res in agent_answer:
                print(f"\nPDF: {res.get('pdf_name')}")
                print(f"Score: {res.get('match_score')}")
                print(f"Method: {res.get('search_method')}")
                print("Matches:")
                for m in res.get('matched_qa', []):
                    print(f"  [MATCH] {m.get('question')[:50]}... -> Type: {m.get('match_type', 'Exact')}")
                print("Non-Matches:")
                for m in res.get('unmatched_qa', []):
                    print(f"  [FAIL] {m.get('question')[:50]}... -> Ref: '{m.get('user_answer_ref')}' vs PDF: '{m.get('pdf_answer')}' Status: {m.get('status')}")

        else:
            print("No queries found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(inspect_latest_query())

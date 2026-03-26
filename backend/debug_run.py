import asyncio
import os
import sys

# Add the current directory to sys.path so app can be imported
sys.path.append(os.getcwd())

from app.services.sharepoint_sync import sync_sharepoint

async def main():
    print("Starting sync... (This will print all logs to console)")
    try:
        results = await sync_sharepoint()
        print(f"Sync complete. Processed {len(results)} files.")
    except Exception as e:
        print(f"CRITICAL SYNC ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

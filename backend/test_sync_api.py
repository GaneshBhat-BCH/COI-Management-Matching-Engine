import requests
import json
import os

# Configuration: Use port 8001 as per user's remote machine setup
API_URL = "http://localhost:8001/api/upload"

def test_sync():
    """
    Verification script for the SharePoint Sync API.
    Triggers the sync process via POST /api/upload (no body).
    """
    print("====================================================")
    print("   COI MATCHING ENGINE - API VERIFICATION")
    print("====================================================")
    print(f"Target Endpoint: {API_URL}")
    print("Status: Sending sync trigger...")
    print("Note: This may take a minute if new documents are being processed.\n")
    
    try:
        # POST request without a body triggers the automated SharePoint sync
        response = requests.post(API_URL, timeout=600) # Long timeout for sync
        
        if response.status_code == 200:
            data = response.json()
            processed = data.get("processed_files", [])
            print(f"SUCCESS: API is up and running correctly.")
            print(f"Results: {len(processed)} files were processed during this run.")
            if processed:
                print("Files processed:")
                for f in processed:
                    print(f"  - {f}")
            else:
                print("Result: No new or modified files found (Database is up to date).")
        else:
            print(f"ERROR: Received status code {response.status_code}")
            print(f"Response Body: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not connect to the server at {API_URL}.")
        print("Please ensure the FastAPI server is running (usually via 'npm run dev' or 'uvicorn app.main:app --port 8001').")
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")

if __name__ == "__main__":
    test_sync()

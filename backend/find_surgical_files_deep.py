import msal
import requests
import os
from dotenv import load_dotenv

# Load .env
dotenv_path = os.path.join(os.getcwd(), 'app', '.env')
load_dotenv(dotenv_path)

CLIENT_ID = os.getenv("SP_CLIENT_ID")
CLIENT_SECRET = os.getenv("SP_CLIENT_SECRET")
TENANT_ID = os.getenv("SP_TENANT_ID")
DRIVE_ID = os.getenv("SP_DRIVE_ID")

authority = f"https://login.microsoftonline.com/{TENANT_ID}"
scope = ["https://graph.microsoft.com/.default"]

app = msal.ConfidentialClientApplication(CLIENT_ID, authority=authority, client_credential=CLIENT_SECRET)
token = app.acquire_token_for_client(scopes=scope).get("access_token")
headers = {"Authorization": f"Bearer {token}"}

target_files = [
    "Zon_COI_mgmtplan_2009.pdf",
    "Signed BCH Conflict Management.pdf"
]

found_items = []

def process_folder(folder_id, current_path=""):
    url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{folder_id}/children"
    while url:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200: break
        data = resp.json()
        for item in data.get("value", []):
            name = item["name"]
            if "folder" in item:
                # Optimized: Only go deep into COI Management related folders to save time
                if any(x in current_path or x in name for x in ["COI", "Management", "Plans"]):
                    process_folder(item["id"], f"{current_path}/{name}")
            else:
                if any(target in name for target in target_files):
                    print(f"MATCH: {name} in {current_path}")
                    found_items.append({
                        "id": item["id"],
                        "name": name,
                        "path": current_path,
                        "download_url": item.get("@microsoft.graph.downloadUrl")
                    })
        url = data.get("@odata.nextLink")

# Start from root
process_folder("root")

print(f"\nFinal Found: {len(found_items)} items.")
for item in found_items:
    print(f"Filename: {item['name']}")
    print(f"ID: {item['id']}")
    print(f"---")

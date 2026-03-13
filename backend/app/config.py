import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the same directory as this file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# API Settings
API_PORT = int(os.getenv("API_PORT", "8001"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# Azure OpenAI Settings
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_EMBEDDING_ENDPOINT = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")

GPT_DEPLOYMENT = os.getenv("GPT_DEPLOYMENT", "gpt-5")
EMBEDDING_DEPLOYMENT = os.getenv("EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
API_VERSION = os.getenv("API_VERSION", "2025-01-01-preview")

# SharePoint Settings
SHAREPOINT_ROOT_URL = os.getenv("SHAREPOINT_ROOT_URL", "https://bostonchildrenshospital.sharepoint.com/:f:/r/sites/OGCIntelligentAutomation/Legal%20Business%20Units/COI%20Management/COI%20Management%20Plans")
SHAREPOINT_URL_PARAMS = os.getenv("SHAREPOINT_URL_PARAMS", "csf=1&web=1&e=Ivm2oM")

# Database Settings
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT", "5432")

import urllib.parse
encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
DATABASE_URL = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

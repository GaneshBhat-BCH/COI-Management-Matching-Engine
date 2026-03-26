from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from app.routers.upload import router as upload_router
from app.routers.search import router as search_router
from app.database import database

app = FastAPI(title="COI Management Matching Engine")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

app.include_router(upload_router, prefix="/api")
app.include_router(search_router, prefix="/api")

@app.get("/api/debug")
async def debug_endpoint():
    """Diagnostics for health checks."""
    import os
    from app.database import database
    
    db_status = "Unknown"
    try:
        if not database.is_connected:
            await database.connect()
        db_status = "Connected"
    except Exception as e:
        db_status = f"Error: {str(e)}"

    return {
        "status": "online",
        "database": db_status,
        "env_check": {
            "DB_USER": bool(os.getenv("DB_USER")),
            "AZURE_OPENAI_API_KEY": bool(os.getenv("AZURE_OPENAI_API_KEY")),
            "SP_CLIENT_ID": bool(os.getenv("SP_CLIENT_ID")),
            "cwd": os.getcwd()
        }
    }

@app.get("/")
def read_root():
    return {"message": "Welcome to the PDF Q&A API"}

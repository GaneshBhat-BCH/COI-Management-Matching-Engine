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

@app.get("/")
def read_root():
    return {"message": "Welcome to the PDF Q&A API"}

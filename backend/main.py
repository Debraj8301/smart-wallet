from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from core.config import startup_initialize
from api.routes.upload import router as upload_router
from api.routes.ai import router as ai_router
from api.routes.transactions import router as transactions_router
from api.routes.auth import router as auth_router
from api.routes.categories import router as categories_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)

@app.get("/")
async def root():
    return {"message": "Welcome to the Smart Wallet API"}

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(upload_router)
app.include_router(ai_router)
app.include_router(transactions_router)
app.include_router(auth_router)
app.include_router(categories_router)

@app.on_event("startup")
async def startup_event():
    await startup_initialize()

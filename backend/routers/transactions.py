from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from datetime import datetime

from utils.database import connect_to_mongo, close_mongo_connection
from routers import auth, users, projects, transactions, messages, admin

load_dotenv()

app = FastAPI(title="WeFund API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(transactions.router)
app.include_router(messages.router)
app.include_router(admin.router)

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    print("✅ Connected to MongoDB")
    print(f"📡 WeFund FastAPI Server starting...")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    print("❌ Disconnected from MongoDB")

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/")
async def root():
    return {"message": "Welcome to WeFund API"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
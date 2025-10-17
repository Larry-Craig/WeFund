from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import os
from dotenv import load_dotenv
from datetime import datetime

from utils.database import connect_to_mongo, close_mongo_connection
from routers import auth, users, projects, transactions, messages, admin, verification, admin_enhanced
from config import settings

# Import new routers - handle import errors gracefully
try:
    from routers import mobile_money, kyc_aml, notifications, mobile_api
    NEW_ROUTERS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Some routers not available: {e}")
    NEW_ROUTERS_AVAILABLE = False

load_dotenv()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="WeFund API",
    version="2.0.0",
    description="WeFund Crowdfunding Platform with Mobile Money & Advanced Features",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with versioning
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(projects.router, prefix=settings.API_V1_PREFIX)
app.include_router(transactions.router, prefix=settings.API_V1_PREFIX)
app.include_router(messages.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(verification.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_enhanced.router, prefix=settings.API_V1_PREFIX)

# Include new routers if available
if NEW_ROUTERS_AVAILABLE:
    app.include_router(mobile_money.router, prefix=settings.API_V1_PREFIX)
    app.include_router(kyc_aml.router, prefix=settings.API_V1_PREFIX)
    app.include_router(notifications.router, prefix=settings.API_V1_PREFIX)
    app.include_router(mobile_api.router, prefix=settings.API_V1_PREFIX)
    print("✅ All new routers loaded successfully")
else:
    print("⚠️ Some new routers not loaded - check for errors")

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    print("✅ Connected to MongoDB")
    print(f"📡 WeFund API v2.0 starting...")
    print(f"🔒 Rate limiting: {settings.RATE_LIMIT_PER_MINUTE}/minute, {settings.RATE_LIMIT_PER_HOUR}/hour")
    print(f"📱 Personal MoMo: {settings.PERSONAL_MOMO_NUMBER}")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    print("❌ Disconnected from MongoDB")

@app.get("/")
async def root():
    return {
        "message": "Welcome to WeFund API v2.0",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs",
        "health": "/health",
        "features": {
            "mobile_money": NEW_ROUTERS_AVAILABLE,
            "kyc_aml": NEW_ROUTERS_AVAILABLE,
            "notifications": NEW_ROUTERS_AVAILABLE,
            "mobile_api": NEW_ROUTERS_AVAILABLE
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "mobile_money_configured": bool(settings.PERSONAL_MOMO_NUMBER)
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
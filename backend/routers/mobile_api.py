from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId
from slowapi import Limiter
from slowapi.util import get_remote_address

from utils.auth import get_current_user
from utils.database import get_users_collection, get_projects_collection, get_transactions_collection
from config import settings

router = APIRouter(prefix="/mobile", tags=["mobile-api"])


# Mobile-specific rate limiting
mobile_limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])

class MobileProjectResponse(BaseModel):
    id: str
    title: str
    description: str
    roi: float
    fundingGoal: float
    fundedAmount: float
    image: str
    category: str
    riskLevel: str

class MobileTransactionResponse(BaseModel):
    id: str
    type: str
    amount: float
    status: str
    date: str

class MobileUserStats(BaseModel):
    walletBalance: float
    totalInvested: float
    totalReturns: float
    activeInvestments: int

@router.get("/dashboard", dependencies=[Depends(mobile_limiter)])
async def mobile_dashboard(current_user: dict = Depends(get_current_user)):
    """Mobile-optimized dashboard data"""
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's active investments
    user_transactions = await get_transactions_collection().find({
        "userId": ObjectId(current_user["userId"]),
        "type": "investment"
    }).to_list(100)
    
    active_investments = len(set(t.get("projectId") for t in user_transactions))
    
    # Get featured projects (mobile-optimized)
    featured_projects = await get_projects_collection().find({
        "verified": True,
        "blocked": False,
        "status": "open"
    }).sort("createdAt", -1).limit(6).to_list(6)
    
    # Recent transactions
    recent_transactions = await get_transactions_collection().find({
        "userId": ObjectId(current_user["userId"])
    }).sort("date", -1).limit(10).to_list(10)
    
    return {
        "user_stats": {
            "walletBalance": user.get("walletBalance", 0),
            "totalInvested": user.get("totalInvested", 0),
            "totalReturns": user.get("totalReturns", 0),
            "activeInvestments": active_investments,
            "verification_level": user.get("verification_level", "unverified")
        },
        "featured_projects": [{
            "id": str(p["_id"]),
            "title": p["title"],
            "description": p["description"][:100] + "..." if len(p["description"]) > 100 else p["description"],
            "roi": p["roi"],
            "fundingGoal": p["fundingGoal"],
            "fundedAmount": p.get("fundedAmount", 0),
            "image": p["image"],
            "category": p["category"],
            "riskLevel": p["riskLevel"]
        } for p in featured_projects],
        "recent_transactions": [{
            "id": str(t["_id"]),
            "type": t["type"],
            "amount": t["amount"],
            "status": t["status"],
            "date": t["date"].isoformat()
        } for t in recent_transactions]
    }

@router.get("/projects/featured", dependencies=[Depends(mobile_limiter)])
async def mobile_featured_projects(
    category: Optional[str] = None,
    page: int = 1,
    limit: int = 10
):
    """Mobile-optimized project listing"""
    skip = (page - 1) * limit
    query = {
        "verified": True,
        "blocked": False,
        "status": "open"
    }
    
    if category:
        query["category"] = category
    
    projects = await get_projects_collection().find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    return [{
        "id": str(p["_id"]),
        "title": p["title"],
        "short_description": p["description"][:150] + "..." if len(p["description"]) > 150 else p["description"],
        "roi": p["roi"],
        "fundingGoal": p["fundingGoal"],
        "fundedAmount": p.get("fundedAmount", 0),
        "fundingProgress": (p.get("fundedAmount", 0) / p["fundingGoal"]) * 100,
        "image": p["image"],
        "category": p["category"],
        "riskLevel": p["riskLevel"],
        "minInvestment": p["minInvestment"],
        "investors": len(p.get("investors", [])),
        "days_remaining": 30  # Mock - calculate based on project duration
    } for p in projects]

@router.get("/projects/{project_id}", dependencies=[Depends(mobile_limiter)])
async def mobile_project_detail(project_id: str, current_user: dict = Depends(get_current_user)):
    """Mobile-optimized project detail"""
    project = await get_projects_collection().find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if user has invested in this project
    user_investment = await get_transactions_collection().find_one({
        "userId": ObjectId(current_user["userId"]),
        "projectId": ObjectId(project_id),
        "type": "investment"
    })
    
    return {
        "id": str(project["_id"]),
        "title": project["title"],
        "description": project["description"],
        "roi": project["roi"],
        "duration": project["duration"],
        "fundingGoal": project["fundingGoal"],
        "fundedAmount": project.get("fundedAmount", 0),
        "fundingProgress": (project.get("fundedAmount", 0) / project["fundingGoal"]) * 100,
        "riskLevel": project["riskLevel"],
        "category": project["category"],
        "image": project["image"],
        "minInvestment": project["minInvestment"],
        "investors": len(project.get("investors", [])),
        "user_has_invested": user_investment is not None,
        "user_investment_amount": user_investment["amount"] if user_investment else 0
    }

@router.get("/wallet/quick-stats", dependencies=[Depends(mobile_limiter)])
async def mobile_wallet_quick_stats(current_user: dict = Depends(get_current_user)):
    """Quick wallet statistics for mobile"""
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Recent transactions count
    recent_count = await get_transactions_collection().count_documents({
        "userId": ObjectId(current_user["userId"]),
        "date": {"$gte": datetime.utcnow() - timedelta(days=7)}
    })
    
    return {
        "walletBalance": user.get("walletBalance", 0),
        "totalInvested": user.get("totalInvested", 0),
        "weeklyActivity": recent_count,
        "verification_level": user.get("verification_level", "unverified"),
        "investment_limit": get_investment_limit(user.get("verification_level", "unverified"))
    }

# Helper function for investment limits (from kyc_aml.py)
def get_investment_limit(verification_level: str) -> float:
    limits = {
        "unverified": settings.MAX_INVESTMENT_UNVERIFIED,
        "verified": settings.MAX_INVESTMENT_VERIFIED,
        "premium": settings.MAX_INVESTMENT_PREMIUM
    }
    return limits.get(verification_level, settings.MAX_INVESTMENT_UNVERIFIED)
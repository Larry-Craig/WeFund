from fastapi import APIRouter, Depends, HTTPException
from models.project_models import ProjectResponse, InvestmentRequest
from utils.auth import get_current_user
from utils.database import get_projects_collection, get_users_collection, get_transactions_collection
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/api/projects", tags=["projects"])

@router.get("", response_model=list[ProjectResponse])
async def get_projects(current_user: dict = Depends(get_current_user)):
    projects = await get_projects_collection().find({
        "verified": True,
        "blocked": False,
        "status": {"$ne": "pending"}
    }).to_list(1000)
    
    return [{
        "id": str(p["_id"]),
        "title": p["title"],
        "description": p["description"],
        "roi": p["roi"],
        "duration": p["duration"],
        "fundingGoal": p["fundingGoal"],
        "fundedAmount": p.get("fundedAmount", 0),
        "riskLevel": p["riskLevel"],
        "status": p.get("status", "open"),
        "category": p["category"],
        "image": p["image"],
        "minInvestment": p["minInvestment"],
        "investors": len(p.get("investors", [])),
    } for p in projects]

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, current_user: dict = Depends(get_current_user)):
    project = await get_projects_collection().find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "id": str(project["_id"]),
        "title": project["title"],
        "description": project["description"],
        "roi": project["roi"],
        "duration": project["duration"],
        "fundingGoal": project["fundingGoal"],
        "fundedAmount": project.get("fundedAmount", 0),
        "riskLevel": project["riskLevel"],
        "status": project.get("status", "open"),
        "category": project["category"],
        "image": project["image"],
        "minInvestment": project["minInvestment"],
        "investors": len(project.get("investors", [])),
    }

@router.post("/{project_id}/invest")
async def invest_in_project(project_id: str, investment: InvestmentRequest, current_user: dict = Depends(get_current_user)):
    project = await get_projects_collection().find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.get("status") != "open":
        raise HTTPException(status_code=400, detail="Project is not open for investment")
    
    if investment.amount < project["minInvestment"]:
        raise HTTPException(status_code=400, detail=f"Minimum investment is {project['minInvestment']} FCFA")
    
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    if user["walletBalance"] < investment.amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    
    await get_users_collection().update_one(
        {"_id": ObjectId(current_user["userId"])},
        {
            "$inc": {
                "walletBalance": -investment.amount,
                "totalInvested": investment.amount
            }
        }
    )
    
    new_funded = project.get("fundedAmount", 0) + investment.amount
    new_status = "closed" if new_funded >= project["fundingGoal"] else "open"
    
    await get_projects_collection().update_one(
        {"_id": ObjectId(project_id)},
        {
            "$inc": {"fundedAmount": investment.amount},
            "$set": {"status": new_status},
            "$push": {
                "investors": {
                    "userId": ObjectId(current_user["userId"]),
                    "amount": investment.amount,
                    "date": datetime.utcnow()
                }
            }
        }
    )
    
    await get_transactions_collection().insert_one({
        "userId": ObjectId(current_user["userId"]),
        "amount": investment.amount,
        "type": "investment",
        "status": "completed",
        "projectId": ObjectId(project_id),
        "projectTitle": project["title"],
        "date": datetime.utcnow(),
    })
    
    updated_user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    
    return {
        "message": "Investment successful",
        "walletBalance": updated_user["walletBalance"],
        "totalInvested": updated_user["totalInvested"],
    }
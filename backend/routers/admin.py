from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from models.user_models import UserBlock
from models.project_models import ProjectCreate, ProjectBlock
from utils.auth import get_current_user, require_admin
from utils.database import get_users_collection, get_projects_collection, get_transactions_collection
from bson import ObjectId
from datetime import datetime
from io import StringIO
import csv

router = APIRouter(prefix="/api/admin", tags=["admin"])

def format_user(user: dict):
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "age": user["age"],
        "role": user["role"],
        "walletBalance": user.get("walletBalance", 0),
        "totalInvested": user.get("totalInvested", 0),
        "totalReturns": user.get("totalReturns", 0),
        "verified": user.get("verified", False),
        "memberSince": user.get("createdAt", datetime.utcnow()).isoformat(),
    }

@router.get("/users")
async def get_all_users(current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    users = await get_users_collection().find().sort("createdAt", -1).to_list(10000)
    return [{
        "_id": str(u["_id"]),
        "name": u["name"],
        "email": u["email"],
        "age": u["age"],
        "role": u["role"],
        "walletBalance": u.get("walletBalance", 0),
        "totalInvested": u.get("totalInvested", 0),
        "totalReturns": u.get("totalReturns", 0),
        "verified": u.get("verified", False),
        "blocked": u.get("blocked", False),
        "createdAt": u.get("createdAt", datetime.utcnow()).isoformat(),
    } for u in users]

@router.put("/users/{user_id}/verify")
async def verify_user(user_id: str, current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    await get_users_collection().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"verified": True}}
    )
    user = await get_users_collection().find_one({"_id": ObjectId(user_id)})
    return format_user(user)

@router.put("/users/{user_id}/block")
async def block_user(user_id: str, block_data: UserBlock, current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    await get_users_collection().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"blocked": block_data.blocked}}
    )
    user = await get_users_collection().find_one({"_id": ObjectId(user_id)})
    return format_user(user)

@router.get("/projects/all")
async def get_all_projects(current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    projects = await get_projects_collection().find().sort("createdAt", -1).to_list(10000)
    return [{
        "_id": str(p["_id"]),
        "title": p["title"],
        "description": p["description"],
        "roi": p["roi"],
        "duration": p["duration"],
        "fundingGoal": p["fundingGoal"],
        "fundedAmount": p.get("fundedAmount", 0),
        "riskLevel": p["riskLevel"],
        "status": p.get("status", "pending"),
        "category": p["category"],
        "image": p["image"],
        "minInvestment": p["minInvestment"],
        "verified": p.get("verified", False),
        "blocked": p.get("blocked", False),
        "investors": p.get("investors", []),
        "createdAt": p.get("createdAt", datetime.utcnow()).isoformat(),
    } for p in projects]

@router.post("/projects")
async def create_project(project_data: ProjectCreate, current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    new_project = {
        "title": project_data.title,
        "description": project_data.description,
        "roi": project_data.roi,
        "duration": project_data.duration,
        "fundingGoal": project_data.fundingGoal,
        "fundedAmount": 0,
        "riskLevel": project_data.riskLevel,
        "status": "pending",
        "category": project_data.category,
        "image": project_data.image,
        "minInvestment": project_data.minInvestment,
        "verified": False,
        "blocked": False,
        "investors": [],
        "createdAt": datetime.utcnow(),
    }
    
    result = await get_projects_collection().insert_one(new_project)
    new_project["_id"] = result.inserted_id
    
    return {
        "_id": str(new_project["_id"]),
        **{k: v for k, v in new_project.items() if k != "_id"}
    }

@router.put("/projects/{project_id}/verify")
async def verify_project(project_id: str, current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    await get_projects_collection().update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"verified": True, "status": "open"}}
    )
    project = await get_projects_collection().find_one({"_id": ObjectId(project_id)})
    return project

@router.put("/projects/{project_id}/block")
async def block_project(project_id: str, block_data: ProjectBlock, current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    await get_projects_collection().update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"blocked": block_data.blocked}}
    )
    project = await get_projects_collection().find_one({"_id": ObjectId(project_id)})
    return project

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    await get_projects_collection().delete_one({"_id": ObjectId(project_id)})
    return {"message": "Project deleted successfully"}

@router.get("/transactions")
async def get_all_transactions(current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    transactions = await get_transactions_collection().find().sort("date", -1).limit(500).to_list(500)
    
    result = []
    for t in transactions:
        user = await get_users_collection().find_one({"_id": t["userId"]}, {"name": 1, "email": 1})
        result.append({
            "_id": str(t["_id"]),
            "userId": {
                "_id": str(t["userId"]),
                "name": user["name"] if user else "Unknown",
                "email": user["email"] if user else "Unknown",
            },
            "amount": t["amount"],
            "type": t["type"],
            "status": t["status"],
            "projectTitle": t.get("projectTitle"),
            "date": t["date"].isoformat(),
        })
    
    return result

@router.get("/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    total_users = await get_users_collection().count_documents({})
    verified_users = await get_users_collection().count_documents({"verified": True})
    total_projects = await get_projects_collection().count_documents({})
    active_projects = await get_projects_collection().count_documents({"status": "open", "verified": True})
    pending_projects = await get_projects_collection().count_documents({"status": "pending"})
    
    all_transactions = await get_transactions_collection().find({"status": "completed"}).to_list(100000)
    total_investments = sum(t["amount"] for t in all_transactions if t["type"] == "investment")
    total_deposits = sum(t["amount"] for t in all_transactions if t["type"] == "deposit")
    
    return {
        "totalUsers": total_users,
        "verifiedUsers": verified_users,
        "totalProjects": total_projects,
        "activeProjects": active_projects,
        "pendingProjects": pending_projects,
        "totalInvestments": total_investments,
        "totalDeposits": total_deposits,
    }

@router.get("/reports/users")
async def download_users_report(current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    users = await get_users_collection().find().to_list(100000)
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Age', 'Role', 'Wallet Balance', 'Total Invested', 'Total Returns', 'Verified', 'Blocked', 'Member Since'])
    
    for u in users:
        writer.writerow([
            str(u["_id"]),
            u["name"],
            u["email"],
            u["age"],
            u["role"],
            u.get("walletBalance", 0),
            u.get("totalInvested", 0),
            u.get("totalReturns", 0),
            u.get("verified", False),
            u.get("blocked", False),
            u.get("createdAt", datetime.utcnow()).isoformat(),
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users-report.csv"}
    )

@router.get("/reports/transactions")
async def download_transactions_report(current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    transactions = await get_transactions_collection().find().to_list(100000)
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'User Name', 'User Email', 'Type', 'Amount', 'Project Title', 'Status', 'Date'])
    
    for t in transactions:
        user = await get_users_collection().find_one({"_id": t["userId"]}, {"name": 1, "email": 1})
        writer.writerow([
            str(t["_id"]),
            user["name"] if user else "Unknown",
            user["email"] if user else "Unknown",
            t["type"],
            t["amount"],
            t.get("projectTitle", "N/A"),
            t["status"],
            t["date"].isoformat(),
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions-report.csv"}
    )

@router.get("/reports/projects")
async def download_projects_report(current_user: dict = Depends(get_current_user)):
    await require_admin(current_user)
    projects = await get_projects_collection().find().to_list(100000)
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Title', 'Category', 'ROI', 'Duration', 'Funding Goal', 'Funded Amount', 'Risk Level', 'Status', 'Verified', 'Blocked', 'Investors Count', 'Created At'])
    
    for p in projects:
        writer.writerow([
            str(p["_id"]),
            p["title"],
            p["category"],
            p["roi"],
            p["duration"],
            p["fundingGoal"],
            p.get("fundedAmount", 0),
            p["riskLevel"],
            p.get("status", "pending"),
            p.get("verified", False),
            p.get("blocked", False),
            len(p.get("investors", [])),
            p.get("createdAt", datetime.utcnow()).isoformat(),
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=projects-report.csv"}
    )
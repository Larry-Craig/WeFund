from fastapi import APIRouter, Depends, HTTPException
from models.user_models import UserUpdate, UserResponse
from models.transaction_models import WalletTransaction
from utils.auth import get_current_user
from utils.database import get_users_collection, get_transactions_collection
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/api/user", tags=["users"])

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

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: dict = Depends(get_current_user)):
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return format_user(user)

@router.put("/profile", response_model=UserResponse)
async def update_profile(user_update: UserUpdate, current_user: dict = Depends(get_current_user)):
    await get_users_collection().update_one(
        {"_id": ObjectId(current_user["userId"])},
        {"$set": {"name": user_update.name, "age": user_update.age}}
    )
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    return format_user(user)

@router.get("/wallet")
async def get_wallet(current_user: dict = Depends(get_current_user)):
    user = await get_users_collection().find_one(
        {"_id": ObjectId(current_user["userId"])},
        {"walletBalance": 1, "totalInvested": 1, "totalReturns": 1}
    )
    return {
        "walletBalance": user.get("walletBalance", 0),
        "totalInvested": user.get("totalInvested", 0),
        "totalReturns": user.get("totalReturns", 0),
    }

@router.post("/deposit")
async def deposit(transaction: WalletTransaction, current_user: dict = Depends(get_current_user)):
    if transaction.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    
    await get_users_collection().update_one(
        {"_id": ObjectId(current_user["userId"])},
        {"$inc": {"walletBalance": transaction.amount}}
    )
    
    trans_result = await get_transactions_collection().insert_one({
        "userId": ObjectId(current_user["userId"]),
        "amount": transaction.amount,
        "type": "deposit",
        "status": "completed",
        "date": datetime.utcnow(),
    })
    
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    trans_doc = await get_transactions_collection().find_one({"_id": trans_result.inserted_id})
    
    return {
        "message": "Deposit successful",
        "walletBalance": user["walletBalance"],
        "transaction": {
            "id": str(trans_doc["_id"]),
            "type": trans_doc["type"],
            "amount": trans_doc["amount"],
            "status": trans_doc["status"],
            "date": trans_doc["date"].isoformat(),
        }
    }

@router.post("/withdraw")
async def withdraw(transaction: WalletTransaction, current_user: dict = Depends(get_current_user)):
    if transaction.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    if user["walletBalance"] < transaction.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    await get_users_collection().update_one(
        {"_id": ObjectId(current_user["userId"])},
        {"$inc": {"walletBalance": -transaction.amount}}
    )
    
    trans_result = await get_transactions_collection().insert_one({
        "userId": ObjectId(current_user["userId"]),
        "amount": transaction.amount,
        "type": "withdraw",
        "status": "completed",
        "date": datetime.utcnow(),
    })
    
    updated_user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    trans_doc = await get_transactions_collection().find_one({"_id": trans_result.inserted_id})
    
    return {
        "message": "Withdrawal successful",
        "walletBalance": updated_user["walletBalance"],
        "transaction": {
            "id": str(trans_doc["_id"]),
            "type": trans_doc["type"],
            "amount": trans_doc["amount"],
            "status": trans_doc["status"],
            "date": trans_doc["date"].isoformat(),
        }
    }

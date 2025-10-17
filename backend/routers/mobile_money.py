from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime
import requests
import base64
import hashlib
import hmac
import json
from bson import ObjectId

from utils.auth import get_current_user, require_admin
from utils.database import get_users_collection, get_transactions_collection, get_momo_transfers_collection
from config import settings

router = APIRouter(prefix="/mobile-money", tags=["mobile-money"])

class MobileMoneyDeposit(BaseModel):
    provider: Literal["mpesa", "orange_money", "mtn_money"]
    phone_number: str
    amount: float
    currency: str = "XAF"

class MobileMoneyWithdraw(BaseModel):
    provider: Literal["mpesa", "orange_money", "mtn_money"]
    phone_number: str
    amount: float
    currency: str = "XAF"

class BankTransferRequest(BaseModel):
    amount: float
    description: str

# Personal MoMo Service (Temporary Solution)
class PersonalMoMoService:
    @staticmethod
    async def process_deposit_to_personal_momo(amount: float, user_phone: str, user_id: str, transaction_ref: str):
        """Process deposit to your personal MoMo number"""
        try:
            # In a real implementation, this would integrate with MoMo API
            # For now, we'll simulate the process and record it
            
            transfer_data = {
                "from_phone": user_phone,
                "to_phone": settings.PERSONAL_MOMO_NUMBER,
                "amount": amount,
                "provider": settings.PERSONAL_MOMO_PROVIDER,
                "transaction_ref": transaction_ref,
                "user_id": user_id,
                "status": "completed",
                "type": "deposit_to_personal_momo",
                "processed_at": datetime.utcnow(),
                "notes": f"Funds deposited to personal MoMo {settings.PERSONAL_MOMO_NUMBER}"
            }
            
            # Record the transfer to personal MoMo
            await get_momo_transfers_collection().insert_one(transfer_data)
            
            # Update user's virtual wallet (for platform tracking)
            await get_users_collection().update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"walletBalance": amount}}
            )
            
            # Record platform transaction
            platform_tx = {
                "userId": ObjectId(user_id),
                "amount": amount,
                "type": "momo_deposit",
                "status": "completed",
                "provider": settings.PERSONAL_MOMO_PROVIDER,
                "phone_number": user_phone,
                "transaction_ref": transaction_ref,
                "personal_momo_received": True,
                "personal_momo_number": settings.PERSONAL_MOMO_NUMBER,
                "notes": f"Funds sent to personal MoMo {settings.PERSONAL_MOMO_NUMBER}",
                "date": datetime.utcnow()
            }
            
            await get_transactions_collection().insert_one(platform_tx)
            
            return {
                "success": True,
                "message": f"Deposit processed successfully. Funds sent to MoMo: {settings.PERSONAL_MOMO_NUMBER}",
                "personal_momo_number": settings.PERSONAL_MOMO_NUMBER,
                "amount": amount
            }
            
        except Exception as e:
            print(f"Personal MoMo deposit error: {e}")
            return {
                "success": False,
                "message": f"Deposit failed: {str(e)}"
            }

    @staticmethod
    async def transfer_to_bank(amount: float, description: str):
        """Transfer funds from personal MoMo to bank (Future implementation)"""
        if not settings.BANK_TRANSFER_ENABLED:
            return {
                "success": False,
                "message": "Bank transfers are not yet enabled. Funds remain in personal MoMo.",
                "current_location": f"Personal MoMo: {settings.PERSONAL_MOMO_NUMBER}"
            }
        
        try:
            # This would integrate with bank transfer API
            # For now, simulate the process
            
            transfer_data = {
                "from_momo": settings.PERSONAL_MOMO_NUMBER,
                "to_bank": settings.BANK_ACCOUNT_NUMBER,
                "bank_name": settings.BANK_NAME,
                "amount": amount,
                "description": description,
                "status": "pending",
                "type": "momo_to_bank",
                "initiated_at": datetime.utcnow()
            }
            
            await get_momo_transfers_collection().insert_one(transfer_data)
            
            return {
                "success": True,
                "message": f"Transfer initiated from MoMo to {settings.BANK_NAME}",
                "amount": amount,
                "bank_account": settings.BANK_ACCOUNT_NUMBER
            }
            
        except Exception as e:
            print(f"Bank transfer error: {e}")
            return {
                "success": False,
                "message": f"Bank transfer failed: {str(e)}"
            }

# ... existing MPesaService and OrangeMoneyService classes ...

@router.post("/deposit")
async def mobile_money_deposit(
    deposit_data: MobileMoneyDeposit,
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Initiate mobile money deposit to personal MoMo"""
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate amount
    if deposit_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    
    if deposit_data.amount < 100:  # Minimum deposit
        raise HTTPException(status_code=400, detail="Minimum deposit is 100 XAF")
    
    # Generate transaction reference
    transaction_ref = f"WFD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # For now, we'll simulate the MoMo payment process
    # In production, this would integrate with actual MoMo APIs
    
    # Process deposit to personal MoMo
    result = await PersonalMoMoService.process_deposit_to_personal_momo(
        deposit_data.amount,
        deposit_data.phone_number,
        current_user["userId"],
        transaction_ref
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return {
        "message": "Deposit initiated successfully",
        "transaction_ref": transaction_ref,
        "personal_momo_number": settings.PERSONAL_MOMO_NUMBER,
        "amount": deposit_data.amount,
        "next_steps": [
            f"Send {deposit_data.amount} XAF to {settings.PERSONAL_MOMO_NUMBER}",
            "Use the transaction reference in the payment description",
            "Your wallet will be updated automatically once payment is confirmed"
        ],
        "important_note": f"ALL DEPOSITS MUST BE SENT TO: {settings.PERSONAL_MOMO_NUMBER}"
    }

@router.post("/withdraw")
async def mobile_money_withdraw(
    withdraw_data: MobileMoneyWithdraw,
    current_user: dict = Depends(get_current_user)
):
    """Initiate mobile money withdrawal from platform wallet"""
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check wallet balance
    if user.get("walletBalance", 0) < withdraw_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Validate amount
    if withdraw_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    
    if withdraw_data.amount < 500:  # Minimum withdrawal
        raise HTTPException(status_code=400, detail="Minimum withdrawal is 500 XAF")
    
    # Generate transaction reference
    transaction_ref = f"WFW{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # Record withdrawal transaction
    transaction_data = {
        "userId": ObjectId(current_user["userId"]),
        "amount": withdraw_data.amount,
        "type": "mobile_withdrawal",
        "status": "pending",
        "provider": withdraw_data.provider,
        "phone_number": withdraw_data.phone_number,
        "transaction_ref": transaction_ref,
        "personal_momo_source": settings.PERSONAL_MOMO_NUMBER,
        "notes": f"Withdrawal processed from personal MoMo {settings.PERSONAL_MOMO_NUMBER}",
        "date": datetime.utcnow()
    }
    
    await get_transactions_collection().insert_one(transaction_data)
    
    # Update wallet balance
    await get_users_collection().update_one(
        {"_id": ObjectId(current_user["userId"])},
        {"$inc": {"walletBalance": -withdraw_data.amount}}
    )
    
    return {
        "message": "Withdrawal initiated successfully",
        "transaction_ref": transaction_ref,
        "amount": withdraw_data.amount,
        "source_momo": settings.PERSONAL_MOMO_NUMBER,
        "processing_time": "2-4 hours",
        "new_balance": user.get("walletBalance", 0) - withdraw_data.amount,
        "note": "Withdrawals are processed manually from personal MoMo account"
    }

@router.post("/admin/transfer-to-bank")
async def transfer_to_bank(
    transfer_request: BankTransferRequest,
    current_user: dict = Depends(get_current_user)
):
    """Transfer funds from personal MoMo to bank account (Admin only)"""
    await require_admin(current_user)
    
    result = await PersonalMoMoService.transfer_to_bank(
        transfer_request.amount,
        transfer_request.description
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return {
        "message": result["message"],
        "transfer_details": {
            "from_momo": settings.PERSONAL_MOMO_NUMBER,
            "to_bank": settings.BANK_ACCOUNT_NUMBER if settings.BANK_TRANSFER_ENABLED else "NOT_CONFIGURED",
            "amount": transfer_request.amount,
            "description": transfer_request.description
        }
    }

@router.get("/admin/personal-momo-stats")
async def get_personal_momo_stats(current_user: dict = Depends(get_current_user)):
    """Get statistics for personal MoMo transactions (Admin only)"""
    await require_admin(current_user)
    
    # Calculate total deposits to personal MoMo
    pipeline = [
        {
            "$match": {
                "type": "deposit_to_personal_momo",
                "status": "completed"
            }
        },
        {
            "$group": {
                "_id": None,
                "total_deposits": {"$sum": "$amount"},
                "transaction_count": {"$sum": 1}
            }
        }
    ]
    
    stats = await get_momo_transfers_collection().aggregate(pipeline).to_list(1)
    
    # Recent transactions
    recent_transfers = await get_momo_transfers_collection().find({
        "type": "deposit_to_personal_momo"
    }).sort("processed_at", -1).limit(10).to_list(10)
    
    return {
        "personal_momo_number": settings.PERSONAL_MOMO_NUMBER,
        "provider": settings.PERSONAL_MOMO_PROVIDER,
        "total_deposits": stats[0]["total_deposits"] if stats else 0,
        "total_transactions": stats[0]["transaction_count"] if stats else 0,
        "bank_transfer_enabled": settings.BANK_TRANSFER_ENABLED,
        "auto_transfer_to_bank": settings.AUTO_TRANSFER_TO_BANK,
        "recent_transfers": [{
            "id": str(t["_id"]),
            "from_phone": t["from_phone"],
            "amount": t["amount"],
            "transaction_ref": t["transaction_ref"],
            "processed_at": t["processed_at"].isoformat(),
            "status": t["status"]
        } for t in recent_transfers]
    }

@router.get("/deposit-instructions")
async def get_deposit_instructions():
    """Get instructions for depositing via mobile money"""
    return {
        "deposit_instructions": {
            "step_1": f"Send the desired amount to: {settings.PERSONAL_MOMO_NUMBER}",
            "step_2": "Include your user ID or transaction reference in the payment description",
            "step_3": "Your WeFund wallet will be updated within 5-10 minutes",
            "step_4": "Check your transaction history for confirmation",
            "important_notes": [
                f"ONLY send money to: {settings.PERSONAL_MOMO_NUMBER}",
                "Include your user ID in the payment description",
                "Minimum deposit: 100 XAF",
                "Contact support if wallet not updated within 15 minutes"
            ],
            "supported_providers": ["MTN Mobile Money", "Orange Money"],
            "contact_support": "If you have any issues, contact support with your transaction details"
        }
    }

@router.get("/transactions")
async def get_mobile_transactions(current_user: dict = Depends(get_current_user)):
    """Get user's mobile money transactions"""
    transactions = await get_transactions_collection().find({
        "userId": ObjectId(current_user["userId"]),
        "type": {"$in": ["momo_deposit", "mobile_withdrawal"]}
    }).sort("date", -1).limit(50).to_list(50)
    
    return [{
        "id": str(t["_id"]),
        "type": t["type"],
        "amount": t["amount"],
        "status": t["status"],
        "provider": t.get("provider"),
        "phone_number": t.get("phone_number"),
        "personal_momo_involved": t.get("personal_momo_received", False),
        "personal_momo_number": t.get("personal_momo_number"),
        "transaction_ref": t.get("transaction_ref"),
        "date": t["date"].isoformat(),
        "notes": t.get("notes", "")
    } for t in transactions]
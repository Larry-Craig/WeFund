import logging
from datetime import datetime
from utils.database import get_bank_accounts_collection
from bson import ObjectId

logger = logging.getLogger(__name__)

class BankAccountService:
    @staticmethod
    async def create_bank_account(account_data: dict):
        """Create a new bank account"""
        account_data.update({
            "balance": 0.0,
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "transactions": []
        })
        
        result = await get_bank_accounts_collection().insert_one(account_data)
        return result.inserted_id

    @staticmethod
    async def get_bank_account(account_id: str):
        """Get bank account by ID"""
        return await get_bank_accounts_collection().find_one({"_id": ObjectId(account_id)})

    @staticmethod
    async def get_all_bank_accounts():
        """Get all bank accounts"""
        return await get_bank_accounts_collection().find().sort("created_at", -1).to_list(1000)

    @staticmethod
    async def update_bank_account(account_id: str, update_data: dict):
        """Update bank account"""
        update_data["updated_at"] = datetime.utcnow()
        await get_bank_accounts_collection().update_one(
            {"_id": ObjectId(account_id)},
            {"$set": update_data}
        )

    @staticmethod
    async def record_transaction(account_id: str, transaction_data: dict):
        """Record a bank transaction"""
        transaction_data.update({
            "id": str(ObjectId()),
            "created_at": datetime.utcnow()
        })
        
        # Update account balance
        if transaction_data["type"] == "deposit":
            update_op = {"$inc": {"balance": transaction_data["amount"]}}
        else:  # withdrawal
            update_op = {"$inc": {"balance": -transaction_data["amount"]}}
        
        await get_bank_accounts_collection().update_one(
            {"_id": ObjectId(account_id)},
            {
                **update_op,
                "$push": {"transactions": transaction_data},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

    @staticmethod
    async def get_account_balance(account_id: str):
        """Get current account balance"""
        account = await get_bank_accounts_collection().find_one(
            {"_id": ObjectId(account_id)},
            {"balance": 1}
        )
        return account.get("balance", 0) if account else 0

    @staticmethod
    async def get_account_transactions(account_id: str, limit: int = 50):
        """Get account transactions"""
        account = await get_bank_accounts_collection().find_one(
            {"_id": ObjectId(account_id)},
            {"transactions": {"$slice": -limit}}  # Get last N transactions
        )
        return account.get("transactions", []) if account else []

    @staticmethod
    async def get_total_platform_balance():
        """Get total balance across all bank accounts"""
        pipeline = [
            {"$group": {"_id": None, "total_balance": {"$sum": "$balance"}}}
        ]
        result = await get_bank_accounts_collection().aggregate(pipeline).to_list(1)
        return result[0]["total_balance"] if result else 0
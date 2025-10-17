from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

client = None
db = None

async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]
    print("✅ Connected to MongoDB")

async def close_mongo_connection():
    if client:
        client.close()

def get_database():
    return db

def get_users_collection():
    return db.users

def get_projects_collection():
    return db.projects

def get_transactions_collection():
    return db.transactions

def get_messages_collection():
    return db.messages

def get_verification_collection():
    return db.verifications

def get_bank_accounts_collection():
    return db.bank_accounts

def get_admin_emails_collection():
    return db.admin_emails

def get_app_analytics_collection():
    return db.app_analytics
def get_kyc_collection():
    return db.kyc_verifications

def get_notifications_collection():
    return db.notifications

def get_mobile_tokens_collection():
    return db.mobile_tokens

def get_aml_checks_collection():
    return db.aml_checkss

def get_momo_transfers_collection():
    return db.momo_transfers
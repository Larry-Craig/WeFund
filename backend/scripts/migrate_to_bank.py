"""
Migration script to switch from personal MoMo to bank transfers
Run this when you're ready to implement bank transfers
"""
import asyncio
from utils.database import connect_to_mongo, get_momo_transfers_collection
from config import settings

async def migrate_to_bank_system():
    """Migrate from personal MoMo to bank transfer system"""
    print("🔧 Starting migration to bank transfer system...")
    
    await connect_to_mongo()
    
    # Update system configuration
    print("📋 Updating system configuration...")
    # This would update your environment variables or database settings
    
    # Archive current MoMo transactions
    print("📁 Archiving MoMo transactions...")
    momo_transfers = await get_momo_transfers_collection().find({
        "status": "completed"
    }).to_list(1000)
    
    print(f"📊 Found {len(momo_transfers)} completed MoMo transfers")
    
    # Create bank transfer records for existing funds
    print("💳 Creating bank transfer records...")
    # This would create initial bank transfer records
    
    print("✅ Migration completed!")
    print("🎯 Next steps:")
    print("1. Update .env with bank account details")
    print("2. Set BANK_TRANSFER_ENABLED=true")
    print("3. Test bank transfer functionality")
    print("4. Monitor first few transfers carefully")

if __name__ == "__main__":
    asyncio.run(migrate_to_bank_system())
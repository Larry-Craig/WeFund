import logging
from utils.email_service import send_phone_verification_email
from utils.database import get_users_collection
from bson import ObjectId

logger = logging.getLogger(__name__)

async def send_phone_verification(user_id: str, phone_number: str, verification_code: str):
    """Send phone verification - for now we'll use email as fallback"""
    try:
        # Get user to send email
        user = await get_users_collection().find_one({"_id": ObjectId(user_id)})
        if not user:
            logger.error(f"User {user_id} not found for phone verification")
            return False
        
        # Send verification code via email (as fallback until SMS is set up)
        success = await send_phone_verification_email(
            user["email"],
            user["name"],
            verification_code
        )
        
        if success:
            logger.info(f"Phone verification code sent via email to {user['email']}")
            return True
        else:
            logger.error(f"Failed to send phone verification email to {user['email']}")
            return False
            
    except Exception as e:
        logger.error(f"Error in phone verification for user {user_id}: {e}")
        return False

async def send_verification_code(phone_number: str, verification_code: str, method: str = "email"):
    """Send verification code - currently only email method supported"""
    # For now, we'll just log this and handle it via the user context
    logger.info(f"Verification code {verification_code} generated for phone {phone_number}")
    return True  # Return True since we'll handle sending via user context
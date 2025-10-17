from twilio.rest import Client
from config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Twilio client
try:
    twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
except Exception as e:
    logger.warning(f"Twilio client initialization failed: {e}")
    twilio_client = None

async def send_sms_verification(phone_number: str, verification_code: str):
    """Send SMS verification code"""
    if not twilio_client:
        logger.error("Twilio client not initialized")
        return False
    
    try:
        message = twilio_client.messages.create(
            body=f"Your WeFund verification code is: {verification_code}. This code will expire in 10 minutes.",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        logger.info(f"SMS sent to {phone_number}: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {e}")
        return False

async def send_whatsapp_verification(phone_number: str, verification_code: str):
    """Send WhatsApp verification code"""
    if not twilio_client:
        logger.error("Twilio client not initialized")
        return False
    
    try:
        # Ensure phone number is in E.164 format and has WhatsApp prefix
        whatsapp_number = f"whatsapp:{phone_number}" if not phone_number.startswith("whatsapp:") else phone_number
        
        message = twilio_client.messages.create(
            body=f"Welcome to WeFund! 🎉\n\nYour verification code is: *{verification_code}*\n\nThis code will expire in 10 minutes.\n\nThank you for joining WeFund - where your investment journey begins!",
            from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
            to=whatsapp_number
        )
        logger.info(f"WhatsApp message sent to {phone_number}: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp to {phone_number}: {e}")
        return False

async def send_verification_code(phone_number: str, verification_code: str, method: str = "sms"):
    """Send verification code via SMS or WhatsApp"""
    if method.lower() == "whatsapp":
        return await send_whatsapp_verification(phone_number, verification_code)
    else:
        return await send_sms_verification(phone_number, verification_code)
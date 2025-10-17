from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from models.user_models import PhoneVerificationRequest, PhoneVerificationVerify, ResendVerificationRequest
from utils.auth import get_current_user
from utils.email_service import generate_verification_code, generate_email_token, send_welcome_email, store_verification_data, verify_email_token, verify_phone_code, send_phone_verification_email
from utils.phone_service import send_phone_verification
from utils.database import get_verification_collection, get_users_collection
from bson import ObjectId
from datetime import datetime
from config import settings

router = APIRouter(prefix="/api/verification", tags=["verification"])

@router.post("/send-phone-code")
async def send_phone_verification_code(
    request: PhoneVerificationRequest,
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Send phone verification code (currently via email)"""
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate verification code
    verification_code = generate_verification_code(6)
    
    # Store verification data
    await store_verification_data(
        user_id=current_user["userId"],
        email_token=None,
        phone_code=verification_code,
        phone_number=request.phoneNumber
    )
    
    # Update user's phone number
    await get_users_collection().update_one(
        {"_id": ObjectId(current_user["userId"])},
        {"$set": {"phoneNumber": request.phoneNumber}}
    )
    
    # Send verification code via email (as fallback)
    success = await send_phone_verification_email(
        user["email"],
        user["name"],
        verification_code
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send verification code")
    
    return {
        "message": "Verification code sent to your email",
        "method": "email",
        "code": verification_code  # Remove this in production - only for testing
    }

@router.post("/verify-phone")
async def verify_phone_code_endpoint(
    request: PhoneVerificationVerify,
    current_user: dict = Depends(get_current_user)
):
    """Verify phone number with code"""
    result = await verify_phone_code(current_user["userId"], request.code)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return {"message": "Phone number verified successfully"}

@router.get("/verify-email")
async def verify_email_token_endpoint(token: str):
    """Verify email token (called when user clicks verification link)"""
    result = await verify_email_token(token)
    
    if not result["success"]:
        # For API response, return error details
        raise HTTPException(status_code=400, detail=result["message"])
    
    return {
        "success": True,
        "message": "Email verified successfully",
        "user_id": result["userId"],
        "redirect_url": f"{settings.FRONTEND_URL}{settings.VERIFICATION_SUCCESS_URL}"
    }

@router.post("/resend-verification")
async def resend_verification(
    request: ResendVerificationRequest,
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Resend verification email or phone code"""
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if request.type == "email":
        # Generate new email token
        email_token = generate_email_token()
        
        # Store verification data
        await store_verification_data(
            user_id=current_user["userId"],
            email_token=email_token,
            phone_code=None,
            phone_number=None
        )
        
        # Send welcome email
        success = await send_welcome_email(user["email"], user["name"], email_token)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send verification email")
        
        return {"message": "Verification email sent successfully"}
    
    elif request.type == "phone":
        # Check if user has a phone number
        if not user.get("phoneNumber"):
            raise HTTPException(status_code=400, detail="No phone number associated with account")
        
        # Generate new verification code
        verification_code = generate_verification_code(6)
        
        # Store verification data
        await store_verification_data(
            user_id=current_user["userId"],
            email_token=None,
            phone_code=verification_code,
            phone_number=user["phoneNumber"]
        )
        
        # Send verification code via email
        success = await send_phone_verification_email(
            user["email"],
            user["name"],
            verification_code
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send verification code")
        
        return {
            "message": "Verification code sent successfully",
            "code": verification_code  # Remove in production
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid verification type")

@router.get("/status")
async def get_verification_status(current_user: dict = Depends(get_current_user)):
    """Get verification status for current user"""
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get latest verification data
    verification = await get_verification_collection().find_one(
        {"userId": current_user["userId"]},
        sort=[("createdAt", -1)]
    )
    
    return {
        "emailVerified": user.get("verified", False),
        "phoneVerified": verification.get("phoneVerified", False) if verification else False,
        "hasPhoneNumber": bool(user.get("phoneNumber")),
        "phoneNumber": user.get("phoneNumber")
    }
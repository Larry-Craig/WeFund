from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime
from bson import ObjectId
import aiofiles
import os

from utils.auth import get_current_user, require_admin
from utils.database import get_users_collection, get_kyc_collection
from config import settings

router = APIRouter(prefix="/kyc", tags=["kyc-aml"])

class KYCDocumentUpload(BaseModel):
    document_type: Literal["id_card", "passport", "drivers_license", "utility_bill"]
    country: str

class KYCVerificationRequest(BaseModel):
    full_name: str
    date_of_birth: str
    address: str
    id_number: str

class AMLCheckRequest(BaseModel):
    user_id: str
    check_type: Literal["basic", "enhanced", "full"]

# KYC Verification Service
class KYCService:
    @staticmethod
    async def verify_document(document_path: str, document_type: str):
        """Verify KYC document (simplified - integrate with actual KYC service)"""
        # This would integrate with services like:
        # - Jumio
        # - Onfido
        # - Shufti Pro
        # - Local KYC providers
        
        # Mock verification for now
        return {
            "verified": True,
            "confidence_score": 0.95,
            "extracted_data": {
                "full_name": "John Doe",
                "date_of_birth": "1990-01-01",
                "id_number": "ABC123456"
            }
        }

    @staticmethod
    async def aml_check(user_data: dict, check_type: str):
        """Perform AML check (simplified - integrate with actual AML service)"""
        # This would integrate with services like:
        # - ComplyAdvantage
        # - LexisNexis
        # - Local AML databases
        
        # Mock AML check for now
        return {
            "risk_level": "low",
            "sanctions_match": False,
            "pep_match": False,
            "recommendation": "approve"
        }

@router.post("/upload-document")
async def upload_kyc_document(
    document_type: str = Form(...),
    country: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload KYC document for verification"""
    # Validate file type
    if file.content_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Create uploads directory if not exists
    os.makedirs("uploads/kyc", exist_ok=True)
    
    # Generate unique filename
    file_extension = file.filename.split('.')[-1]
    filename = f"kyc_{current_user['userId']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{file_extension}"
    file_path = f"uploads/kyc/{filename}"
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    # Verify document
    verification_result = await KYCService.verify_document(file_path, document_type)
    
    # Store KYC record
    kyc_record = {
        "userId": ObjectId(current_user["userId"]),
        "document_type": document_type,
        "country": country,
        "file_path": file_path,
        "verification_result": verification_result,
        "status": "pending",
        "submitted_at": datetime.utcnow()
    }
    
    await get_kyc_collection().insert_one(kyc_record)
    
    # Update user KYC status
    await get_users_collection().update_one(
        {"_id": ObjectId(current_user["userId"])},
        {"$set": {"kyc_status": "pending"}}
    )
    
    return {
        "message": "Document uploaded successfully",
        "verification_id": str(kyc_record["_id"]),
        "status": "pending",
        "verification_result": verification_result
    }

@router.post("/submit-verification")
async def submit_kyc_verification(
    verification_data: KYCVerificationRequest,
    current_user: dict = Depends(get_current_user)
):
    """Submit KYC verification information"""
    # Store verification data
    kyc_data = {
        "userId": ObjectId(current_user["userId"]),
        "full_name": verification_data.full_name,
        "date_of_birth": verification_data.date_of_birth,
        "address": verification_data.address,
        "id_number": verification_data.id_number,
        "submitted_at": datetime.utcnow(),
        "status": "under_review"
    }
    
    await get_kyc_collection().insert_one(kyc_data)
    
    # Update user verification level
    await get_users_collection().update_one(
        {"_id": ObjectId(current_user["userId"])},
        {"$set": {"kyc_status": "under_review"}}
    )
    
    # Perform AML check
    aml_result = await KYCService.aml_check(kyc_data, "basic")
    
    return {
        "message": "KYC verification submitted",
        "status": "under_review",
        "aml_result": aml_result
    }

@router.get("/status")
async def get_kyc_status(current_user: dict = Depends(get_current_user)):
    """Get KYC verification status"""
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    kyc_records = await get_kyc_collection().find({
        "userId": ObjectId(current_user["userId"])
    }).sort("submitted_at", -1).limit(5).to_list(5)
    
    return {
        "kyc_status": user.get("kyc_status", "not_submitted"),
        "verification_level": user.get("verification_level", "unverified"),
        "submissions": [{
            "id": str(k["_id"]),
            "type": k.get("document_type", "information"),
            "status": k.get("status"),
            "submitted_at": k["submitted_at"].isoformat(),
            "verified_at": k.get("verified_at")
        } for k in kyc_records]
    }

@router.post("/aml-check")
async def perform_aml_check(
    aml_request: AMLCheckRequest,
    current_user: dict = Depends(get_current_user)
):
    """Perform AML check (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = await get_users_collection().find_one({"_id": ObjectId(aml_request.user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user KYC data
    kyc_data = await get_kyc_collection().find_one({
        "userId": ObjectId(aml_request.user_id)
    }, sort=[("submitted_at", -1)])
    
    aml_result = await KYCService.aml_check(kyc_data or {}, aml_request.check_type)
    
    return {
        "user_id": aml_request.user_id,
        "check_type": aml_request.check_type,
        "result": aml_result
    }

# Investment limits based on verification level
def get_investment_limit(verification_level: str) -> float:
    """Get maximum investment amount based on verification level"""
    limits = {
        "unverified": settings.MAX_INVESTMENT_UNVERIFIED,
        "verified": settings.MAX_INVESTMENT_VERIFIED,
        "premium": settings.MAX_INVESTMENT_PREMIUM
    }
    return limits.get(verification_level, settings.MAX_INVESTMENT_UNVERIFIED)
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.user_models import UserRegister, UserLogin
from utils.security import get_password_hash, verify_password
from utils.auth import create_access_token
from utils.email_service import generate_email_token, send_welcome_email, store_verification_data
from utils.database import get_users_collection
from datetime import datetime

router = APIRouter(prefix="/api/auth", tags=["authentication"])

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

@router.post("/register")
async def register(user_data: UserRegister, background_tasks: BackgroundTasks):
    if user_data.age < 15:
        raise HTTPException(status_code=400, detail="You must be at least 15 years old to register")
    
    existing_user = await get_users_collection().find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user_data.password)
    new_user = {
        "name": user_data.name,
        "email": user_data.email,
        "password": hashed_password,
        "age": user_data.age,
        "phoneNumber": user_data.phoneNumber,  # Store phone number
        "role": "member",
        "walletBalance": 0,
        "totalInvested": 0,
        "totalReturns": 0,
        "verified": False,  # Start as unverified
        "blocked": False,
        "createdAt": datetime.utcnow(),
    }
    
    result = await get_users_collection().insert_one(new_user)
    new_user["_id"] = result.inserted_id
    
    # Generate email verification token
    email_token = generate_email_token()
    
    # Store verification data
    await store_verification_data(
        user_id=str(result.inserted_id),
        email_token=email_token,
        phone_code=None,  # Will be generated when user adds phone
        phone_number=user_data.phoneNumber
    )
    
    # Send welcome email with verification link (in background)
    background_tasks.add_task(
        send_welcome_email, 
        user_data.email, 
        user_data.name, 
        email_token
    )
    
    # Create access token (user can access but with limited functionality until verified)
    token = create_access_token({"userId": str(result.inserted_id), "role": "member"})
    
    return {
        "token": token,
        "user": format_user(new_user),
        "message": "Registration successful! Please check your email to verify your account."
    }

@router.post("/login")
async def login(credentials: UserLogin):
    user = await get_users_collection().find_one({"email": credentials.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user.get("blocked", False):
        raise HTTPException(status_code=403, detail="Your account has been blocked. Please contact support.")
    
    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"userId": str(user["_id"]), "role": user["role"]})
    
    response_data = {
        "token": token,
        "user": format_user(user),
    }
    
    # Add verification status reminder if not verified
    if not user.get("verified", False):
        response_data["message"] = "Please verify your email to access all features"
    
    return response_data
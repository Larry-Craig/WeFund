from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    age: int
    phoneNumber: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: str
    age: int

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    age: int
    role: str
    walletBalance: float
    totalInvested: float
    totalReturns: float
    verified: bool
    memberSince: str
    emailVerified: bool = False
    phoneVerified: bool = False

class UserBlock(BaseModel):
    blocked: bool

class PhoneVerificationRequest(BaseModel):
    phoneNumber: str
    method: str = "email"  # Default to email for now

class PhoneVerificationVerify(BaseModel):
    code: str

class ResendVerificationRequest(BaseModel):
    type: str  # "email" or "phone"
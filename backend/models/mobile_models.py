from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime

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

class NotificationToken(BaseModel):
    device_token: str
    device_type: Literal["android", "ios", "web"]

class PushNotification(BaseModel):
    title: str
    message: str
    notification_type: Literal["investment", "project", "system", "message"]
    data: Optional[dict] = None

class KYCDocumentUpload(BaseModel):
    document_type: Literal["id_card", "passport", "drivers_license", "utility_bill"]
    country: str

class KYCVerificationRequest(BaseModel):
    full_name: str
    date_of_birth: str
    address: str
    id_number: str
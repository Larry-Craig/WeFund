from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime
from bson import ObjectId

from utils.auth import get_current_user, require_admin
from utils.database import get_users_collection, get_notifications_collection
from config import settings

router = APIRouter(prefix="/notifications", tags=["notifications"])

class NotificationToken(BaseModel):
    device_token: str
    device_type: Literal["android", "ios", "web"]

class PushNotification(BaseModel):
    title: str
    message: str
    notification_type: Literal["investment", "project", "system", "message"]
    data: Optional[dict] = None

# Firebase Cloud Messaging Service
class NotificationService:
    push_service = None
    
    @classmethod
    def initialize(cls):
        if settings.FIREBASE_SERVER_KEY:
            cls.push_service = FCMNotification(api_key=settings.FIREBASE_SERVER_KEY)
    
    @classmethod
    async def send_push_notification(cls, device_tokens: List[str], title: str, message: str, data: dict = None):
        """Send push notification to devices"""
        if not cls.push_service:
            print("Push notifications not configured")
            return None
        
        try:
            result = cls.push_service.notify_multiple_devices(
                registration_ids=device_tokens,
                message_title=title,
                message_body=message,
                data_message=data,
                sound="default",
                badge=1
            )
            return result
        except Exception as e:
            print(f"Push notification error: {e}")
            return None
    
    @classmethod
    async def send_to_user(cls, user_id: str, title: str, message: str, notification_type: str, data: dict = None):
        """Send notification to specific user"""
        user = await get_users_collection().find_one({"_id": ObjectId(user_id)})
        if not user or not user.get("notification_tokens"):
            return None
        
        device_tokens = [token["device_token"] for token in user.get("notification_tokens", [])]
        
        # Store notification in database
        notification_data = {
            "userId": ObjectId(user_id),
            "title": title,
            "message": message,
            "type": notification_type,
            "data": data,
            "sent": False,
            "created_at": datetime.utcnow()
        }
        
        result = await cls.send_push_notification(device_tokens, title, message, data)
        
        if result and result.get("success", 0) > 0:
            notification_data["sent"] = True
            notification_data["sent_at"] = datetime.utcnow()
        
        await get_notifications_collection().insert_one(notification_data)
        
        return result

# Initialize notification service
NotificationService.initialize()

@router.post("/register-token")
async def register_notification_token(
    token_data: NotificationToken,
    current_user: dict = Depends(get_current_user)
):
    """Register device token for push notifications"""
    user = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if token already exists
    existing_tokens = user.get("notification_tokens", [])
    token_exists = any(t["device_token"] == token_data.device_token for t in existing_tokens)
    
    if not token_exists:
        await get_users_collection().update_one(
            {"_id": ObjectId(current_user["userId"])},
            {"$push": {
                "notification_tokens": {
                    "device_token": token_data.device_token,
                    "device_type": token_data.device_type,
                    "registered_at": datetime.utcnow()
                }
            }}
        )
    
    return {"message": "Device token registered successfully"}

@router.post("/send")
async def send_notification(
    notification: PushNotification,
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Send push notification (admin only)"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if background_tasks:
        # Send in background for better performance
        background_tasks.add_task(
            NotificationService.send_to_user,
            current_user["userId"],
            notification.title,
            notification.message,
            notification.notification_type,
            notification.data
        )
        return {"message": "Notification queued for sending"}
    
    result = await NotificationService.send_to_user(
        current_user["userId"],
        notification.title,
        notification.message,
        notification.notification_type,
        notification.data
    )
    
    return {
        "message": "Notification sent",
        "result": result
    }

@router.get("/")
async def get_user_notifications(
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    limit: int = 20
):
    """Get user notifications"""
    skip = (page - 1) * limit
    notifications = await get_notifications_collection().find({
        "userId": ObjectId(current_user["userId"])
    }).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Mark as read
    unread_ids = [n["_id"] for n in notifications if not n.get("read")]
    if unread_ids:
        await get_notifications_collection().update_many(
            {"_id": {"$in": unread_ids}},
            {"$set": {"read": True, "read_at": datetime.utcnow()}}
        )
    
    return [{
        "id": str(n["_id"]),
        "title": n["title"],
        "message": n["message"],
        "type": n["type"],
        "data": n.get("data"),
        "read": n.get("read", False),
        "created_at": n["created_at"].isoformat(),
        "read_at": n.get("read_at")
    } for n in notifications]

@router.post("/test")
async def test_notification(current_user: dict = Depends(get_current_user)):
    """Test push notification"""
    result = await NotificationService.send_to_user(
        current_user["userId"],
        "Test Notification",
        "This is a test notification from WeFund",
        "system",
        {"test": True}
    )
    
    return {
        "message": "Test notification sent",
        "result": result
    }
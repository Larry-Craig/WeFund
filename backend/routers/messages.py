from fastapi import APIRouter, Depends
from models.transaction_models import MessageSend, MessageResponse
from utils.auth import get_current_user
from utils.database import get_messages_collection, get_users_collection
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/api/messages", tags=["messages"])

@router.get("")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    messages = await get_messages_collection().find({
        "$or": [
            {"senderId": ObjectId(current_user["userId"])},
            {"receiverId": ObjectId(current_user["userId"])}
        ]
    }).sort("timestamp", -1).to_list(1000)
    
    conversations = {}
    for msg in messages:
        sender = await get_users_collection().find_one({"_id": msg["senderId"]}, {"name": 1})
        receiver = await get_users_collection().find_one({"_id": msg["receiverId"]}, {"name": 1})
        
        other_id = str(msg["receiverId"]) if str(msg["senderId"]) == current_user["userId"] else str(msg["senderId"])
        other_name = receiver["name"] if str(msg["senderId"]) == current_user["userId"] else sender["name"]
        
        if other_id not in conversations:
            conversations[other_id] = {
                "userId": other_id,
                "userName": other_name,
                "lastMessage": msg["message"],
                "timestamp": msg["timestamp"].isoformat(),
                "unread": not msg.get("read", False) and str(msg["receiverId"]) == current_user["userId"],
            }
    
    return list(conversations.values())

@router.get("/{user_id}")
async def get_chat(user_id: str, current_user: dict = Depends(get_current_user)):
    messages = await get_messages_collection().find({
        "$or": [
            {"senderId": ObjectId(current_user["userId"]), "receiverId": ObjectId(user_id)},
            {"senderId": ObjectId(user_id), "receiverId": ObjectId(current_user["userId"])}
        ]
    }).sort("timestamp", 1).to_list(1000)
    
    await get_messages_collection().update_many(
        {"senderId": ObjectId(user_id), "receiverId": ObjectId(current_user["userId"]), "read": False},
        {"$set": {"read": True}}
    )
    
    result = []
    for m in messages:
        sender = await get_users_collection().find_one({"_id": m["senderId"]}, {"name": 1})
        receiver = await get_users_collection().find_one({"_id": m["receiverId"]}, {"name": 1})
        result.append({
            "id": str(m["_id"]),
            "senderId": str(m["senderId"]),
            "senderName": sender["name"],
            "receiverId": str(m["receiverId"]),
            "receiverName": receiver["name"],
            "message": m["message"],
            "timestamp": m["timestamp"].isoformat(),
            "read": m.get("read", False),
        })
    
    return result

@router.post("/send", response_model=MessageResponse)
async def send_message(msg_data: MessageSend, current_user: dict = Depends(get_current_user)):
    new_message = {
        "senderId": ObjectId(current_user["userId"]),
        "receiverId": ObjectId(msg_data.receiverId),
        "message": msg_data.message,
        "read": False,
        "timestamp": datetime.utcnow(),
    }
    
    result = await get_messages_collection().insert_one(new_message)
    
    sender = await get_users_collection().find_one({"_id": ObjectId(current_user["userId"])}, {"name": 1})
    receiver = await get_users_collection().find_one({"_id": ObjectId(msg_data.receiverId)}, {"name": 1})
    
    return {
        "id": str(result.inserted_id),
        "senderId": current_user["userId"],
        "senderName": sender["name"],
        "receiverId": msg_data.receiverId,
        "receiverName": receiver["name"],
        "message": msg_data.message,
        "timestamp": new_message["timestamp"].isoformat(),
        "read": False,
    }
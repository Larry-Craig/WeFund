from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class WalletTransaction(BaseModel):
    amount: float

class TransactionResponse(BaseModel):
    id: str
    type: str
    amount: float
    projectTitle: Optional[str] = None
    status: str
    date: str

class MessageSend(BaseModel):
    receiverId: str
    message: str

class MessageResponse(BaseModel):
    id: str
    senderId: str
    senderName: str
    receiverId: str
    receiverName: str
    message: str
    timestamp: str
    read: bool
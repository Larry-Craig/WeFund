from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum

class BankAccountType(str, Enum):
    CURRENT = "current"
    SAVINGS = "savings"
    BUSINESS = "business"

class BankAccountStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class BankAccountCreate(BaseModel):
    bank_name: str
    account_name: str
    account_number: str
    account_type: BankAccountType
    currency: str = "XAF"
    branch_code: Optional[str] = None
    swift_code: Optional[str] = None
    iban: Optional[str] = None
    is_primary: bool = False
    daily_limit: float = 1000000  # 1 million XAF default
    monthly_limit: float = 5000000  # 5 million XAF default

class BankAccountUpdate(BaseModel):
    bank_name: Optional[str] = None
    account_name: Optional[str] = None
    account_type: Optional[BankAccountType] = None
    status: Optional[BankAccountStatus] = None
    daily_limit: Optional[float] = None
    monthly_limit: Optional[float] = None
    is_primary: Optional[bool] = None

class BankAccountResponse(BaseModel):
    id: str
    bank_name: str
    account_name: str
    account_number: str
    account_type: str
    currency: str
    balance: float
    status: str
    is_primary: bool
    daily_limit: float
    monthly_limit: float
    branch_code: Optional[str]
    swift_code: Optional[str]
    iban: Optional[str]
    created_at: str
    updated_at: str

class FundTransferRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: float
    description: str
    reference: Optional[str] = None

class BankTransactionResponse(BaseModel):
    id: str
    bank_account_id: str
    type: str  # deposit, withdrawal, transfer
    amount: float
    description: str
    reference: Optional[str]
    balance_after: float
    created_at: str
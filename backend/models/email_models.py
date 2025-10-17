from pydantic import BaseModel, EmailStr
from typing import Optional, List, Literal
from datetime import datetime

class EmailTemplateType(str, Enum):
    WELCOME = "welcome"
    VERIFICATION = "verification"
    PROJECT_APPROVAL = "project_approval"
    PROJECT_REJECTION = "project_rejection"
    INVESTMENT_SUCCESS = "investment_success"
    WITHDRAWAL_SUCCESS = "withdrawal_success"
    SECURITY_ALERT = "security_alert"
    NEWSLETTER = "newsletter"
    CUSTOM = "custom"

class AdminEmailCreate(BaseModel):
    subject: str
    recipients: List[EmailStr]
    template_type: EmailTemplateType
    content: str
    variables: Optional[dict] = None
    send_immediately: bool = True
    scheduled_for: Optional[datetime] = None

class BulkEmailRequest(BaseModel):
    subject: str
    template_type: EmailTemplateType
    content: str
    user_groups: List[str]  # all, verified, investors, etc.
    variables: Optional[dict] = None
    send_immediately: bool = True

class EmailTemplateCreate(BaseModel):
    name: str
    template_type: EmailTemplateType
    subject: str
    content: str
    variables: List[str]  # Available variables for this template

class EmailResponse(BaseModel):
    id: str
    subject: str
    recipients: List[str]
    template_type: str
    status: str
    sent_at: Optional[str]
    created_at: strs
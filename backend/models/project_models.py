from pydantic import BaseModel
from typing import Literal, Optional, List, Dict
from datetime import datetime
from enum import Enum

class ProjectStatus(str, Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    OPEN = "open"
    FUNDED = "funded"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class ProjectRiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

class ProjectCreate(BaseModel):
    title: str
    description: str
    roi: float
    duration: str
    fundingGoal: float
    riskLevel: ProjectRiskLevel
    category: str
    image: str
    minInvestment: float
    business_plan: Optional[str] = None
    financial_projections: Optional[str] = None
    team_details: Optional[str] = None
    market_analysis: Optional[str] = None

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    roi: Optional[float] = None
    duration: Optional[str] = None
    fundingGoal: Optional[float] = None
    riskLevel: Optional[ProjectRiskLevel] = None
    category: Optional[str] = None
    image: Optional[str] = None
    minInvestment: Optional[float] = None
    status: Optional[ProjectStatus] = None
    verified: Optional[bool] = None
    blocked: Optional[bool] = None
    review_notes: Optional[str] = None

class ProjectReview(BaseModel):
    project_id: str
    status: ProjectStatus
    review_notes: str
    risk_rating: int = Field(ge=1, le=5)  # 1-5 scale
    viability_score: int = Field(ge=1, le=10)  # 1-10 scale
    recommended: bool = False

class ProjectResponse(BaseModel):
    id: str
    title: str
    description: str
    roi: float
    duration: str
    fundingGoal: float
    fundedAmount: float
    riskLevel: str
    status: str
    category: str
    image: str
    minInvestment: float
    investors: int
    verified: bool
    blocked: bool
    created_at: str
    review_notes: Optional[str]
    risk_rating: Optional[int]
    viability_score: Optional[int]

class ProjectBlock(BaseModel):
    blocked: bool

class InvestmentRequest(BaseModel):
    amount: float
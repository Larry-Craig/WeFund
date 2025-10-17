from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime, date

class AppStatsResponse(BaseModel):
    total_users: int
    active_users: int
    verified_users: int
    total_projects: int
    active_projects: int
    funded_projects: int
    total_investments: float
    total_deposits: float
    total_withdrawals: float
    platform_balance: float
    monthly_growth: float
    user_retention_rate: float

class RevenueAnalytics(BaseModel):
    period: str  # daily, weekly, monthly
    total_revenue: float
    investment_fees: float
    withdrawal_fees: float
    other_fees: float
    date: date

class UserAnalytics(BaseModel):
    period: str
    new_users: int
    active_users: int
    returning_users: int
    churn_rate: float
    date: date

class ProjectAnalytics(BaseModel):
    period: str
    new_projects: int
    funded_projects: int
    total_funding: float
    average_roi: float
    success_rate: float
    date: date

class FinancialReportRequest(BaseModel):
    start_date: date
    end_date: date
    report_type: str  # transactions, users, projects, financial
    format: str = "json"  # json, csv, pdf
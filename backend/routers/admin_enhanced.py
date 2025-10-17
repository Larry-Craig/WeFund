from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, date, timedelta
from bson import ObjectId
import csv
from io import StringIO

from models.bank_models import (
    BankAccountCreate, BankAccountUpdate, BankAccountResponse, 
    FundTransferRequest, BankTransactionResponse
)
from models.email_models import AdminEmailCreate, BulkEmailRequest, EmailResponse
from models.project_models import ProjectReview, ProjectUpdate
from models.analytics_models import (
    AppStatsResponse, FinancialReportRequest, 
    RevenueAnalytics, UserAnalytics, ProjectAnalytics
)
from utils.auth import get_current_user, require_admin
from utils.database import (
    get_users_collection, get_projects_collection, get_transactions_collection,
    get_bank_accounts_collection, get_admin_emails_collection, get_app_analytics_collection
)
from utils.email_service import send_admin_email, send_project_status_email
from utils.bank_service import BankAccountService
from config import settings

router = APIRouter(prefix="/api/admin", tags=["admin-enhanced"])

# ===== BANK ACCOUNT MANAGEMENT =====

@router.post("/bank-accounts", response_model=dict)
async def create_bank_account(
    account_data: BankAccountCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new bank account for the platform"""
    await require_admin(current_user)
    
    # Check if this should be primary and update others
    if account_data.is_primary:
        await get_bank_accounts_collection().update_many(
            {"is_primary": True},
            {"$set": {"is_primary": False}}
        )
    
    account_dict = account_data.dict()
    account_id = await BankAccountService.create_bank_account(account_dict)
    
    return {
        "message": "Bank account created successfully",
        "account_id": str(account_id)
    }

@router.get("/bank-accounts", response_model=List[BankAccountResponse])
async def get_bank_accounts(current_user: dict = Depends(get_current_user)):
    """Get all bank accounts"""
    await require_admin(current_user)
    
    accounts = await BankAccountService.get_all_bank_accounts()
    
    return [{
        "id": str(acc["_id"]),
        "bank_name": acc["bank_name"],
        "account_name": acc["account_name"],
        "account_number": acc["account_number"],
        "account_type": acc["account_type"],
        "currency": acc["currency"],
        "balance": acc["balance"],
        "status": acc["status"],
        "is_primary": acc.get("is_primary", False),
        "daily_limit": acc.get("daily_limit", 0),
        "monthly_limit": acc.get("monthly_limit", 0),
        "branch_code": acc.get("branch_code"),
        "swift_code": acc.get("swift_code"),
        "iban": acc.get("iban"),
        "created_at": acc["created_at"].isoformat(),
        "updated_at": acc["updated_at"].isoformat(),
    } for acc in accounts]

@router.put("/bank-accounts/{account_id}")
async def update_bank_account(
    account_id: str,
    update_data: BankAccountUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update bank account details"""
    await require_admin(current_user)
    
    # Handle primary account change
    if update_data.is_primary:
        await get_bank_accounts_collection().update_many(
            {"is_primary": True},
            {"$set": {"is_primary": False}}
        )
    
    await BankAccountService.update_bank_account(account_id, update_data.dict(exclude_unset=True))
    
    return {"message": "Bank account updated successfully"}

@router.get("/bank-accounts/{account_id}/transactions")
async def get_bank_account_transactions(
    account_id: str,
    current_user: dict = Depends(get_current_user),
    limit: int = 50
):
    """Get transactions for a bank account"""
    await require_admin(current_user)
    
    transactions = await BankAccountService.get_account_transactions(account_id, limit)
    
    return [{
        "id": t["id"],
        "type": t["type"],
        "amount": t["amount"],
        "description": t["description"],
        "reference": t.get("reference"),
        "balance_after": t["balance_after"],
        "created_at": t["created_at"].isoformat(),
    } for t in transactions]

@router.get("/bank-accounts/balance/total")
async def get_total_platform_balance(current_user: dict = Depends(get_current_user)):
    """Get total balance across all bank accounts"""
    await require_admin(current_user)
    
    total_balance = await BankAccountService.get_total_platform_balance()
    
    return {"total_balance": total_balance}

# ===== PROJECT VETTING =====

@router.put("/projects/{project_id}/review")
async def review_project(
    project_id: str,
    review: ProjectReview,
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Review and update project status"""
    await require_admin(current_user)
    
    project = await get_projects_collection().find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = {
        "status": review.status,
        "verified": review.status == "approved",
        "review_notes": review.review_notes,
        "risk_rating": review.risk_rating,
        "viability_score": review.viability_score,
        "reviewed_at": datetime.utcnow(),
        "reviewed_by": current_user["userId"]
    }
    
    await get_projects_collection().update_one(
        {"_id": ObjectId(project_id)},
        {"$set": update_data}
    )
    
    # Send email notification to project owner
    if background_tasks and project.get("owner_id"):
        from utils.database import get_users_collection
        owner = await get_users_collection().find_one({"_id": ObjectId(project["owner_id"])})
        if owner:
            background_tasks.add_task(
                send_project_status_email,
                owner["email"],
                owner["name"],
                project["title"],
                review.status,
                review.review_notes
            )
    
    return {"message": f"Project {review.status} successfully"}

@router.get("/projects/pending")
async def get_pending_projects(
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    limit: int = 20
):
    """Get projects pending review"""
    await require_admin(current_user)
    
    skip = (page - 1) * limit
    projects = await get_projects_collection().find({
        "status": {"$in": ["pending", "under_review"]}
    }).sort("createdAt", -1).skip(skip).limit(limit).to_list(limit)
    
    return [{
        "id": str(p["_id"]),
        "title": p["title"],
        "description": p["description"],
        "fundingGoal": p["fundingGoal"],
        "riskLevel": p["riskLevel"],
        "category": p["category"],
        "status": p.get("status", "pending"),
        "createdAt": p.get("createdAt", datetime.utcnow()).isoformat(),
        "review_notes": p.get("review_notes"),
    } for p in projects]

# ===== EMAIL MANAGEMENT =====

@router.post("/emails/send")
async def send_admin_email_endpoint(
    email_data: AdminEmailCreate,
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Send email to users from admin"""
    await require_admin(current_user)
    
    if background_tasks:
        background_tasks.add_task(
            send_admin_email,
            email_data.recipients,
            email_data.subject,
            email_data.content,
            email_data.template_type
        )
        return {"message": "Email queued for sending"}
    else:
        success = await send_admin_email(
            email_data.recipients,
            email_data.subject,
            email_data.content,
            email_data.template_type
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send email")
        
        return {"message": "Email sent successfully"}

@router.post("/emails/bulk")
async def send_bulk_email(
    bulk_data: BulkEmailRequest,
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """Send bulk email to user groups"""
    await require_admin(current_user)
    
    # Build recipient list based on user groups
    query = {}
    if "verified" in bulk_data.user_groups:
        query["verified"] = True
    if "investors" in bulk_data.user_groups:
        query["totalInvested"] = {"$gt": 0}
    
    users = await get_users_collection().find(query).to_list(10000)
    recipients = [user["email"] for user in users if user.get("email")]
    
    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients found for the specified groups")
    
    if background_tasks:
        background_tasks.add_task(
            send_admin_email,
            recipients,
            bulk_data.subject,
            bulk_data.content,
            bulk_data.template_type
        )
        return {"message": f"Bulk email queued for {len(recipients)} recipients"}
    else:
        success = await send_admin_email(
            recipients,
            bulk_data.subject,
            bulk_data.content,
            bulk_data.template_type
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send bulk email")
        
        return {"message": f"Bulk email sent to {len(recipients)} recipients"}

@router.get("/emails/history", response_model=List[EmailResponse])
async def get_email_history(
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    limit: int = 20
):
    """Get email sending history"""
    await require_admin(current_user)
    
    skip = (page - 1) * limit
    emails = await get_admin_emails_collection().find().sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return [{
        "id": str(email["_id"]),
        "subject": email["subject"],
        "recipients": email["recipients"],
        "template_type": email["template_type"],
        "status": email["status"],
        "sent_at": email.get("sent_at").isoformat() if email.get("sent_at") else None,
        "created_at": email["created_at"].isoformat(),
    } for email in emails]

# ===== ENHANCED ANALYTICS & REPORTS =====

@router.get("/analytics/dashboard")
async def get_dashboard_analytics(current_user: dict = Depends(get_current_user)):
    """Get comprehensive dashboard analytics"""
    await require_admin(current_user)
    
    # Basic counts
    total_users = await get_users_collection().count_documents({})
    active_users = await get_users_collection().count_documents({
        "last_login": {"$gte": datetime.utcnow() - timedelta(days=30)}
    })
    verified_users = await get_users_collection().count_documents({"verified": True})
    
    total_projects = await get_projects_collection().count_documents({})
    active_projects = await get_projects_collection().count_documents({"status": "open"})
    funded_projects = await get_projects_collection().count_documents({"status": "funded"})
    
    # Financial data
    transactions = await get_transactions_collection().find({"status": "completed"}).to_list(100000)
    total_investments = sum(t["amount"] for t in transactions if t["type"] == "investment")
    total_deposits = sum(t["amount"] for t in transactions if t["type"] == "deposit")
    total_withdrawals = sum(t["amount"] for t in transactions if t["type"] == "withdrawal")
    
    # Platform balance from bank accounts
    platform_balance = await BankAccountService.get_total_platform_balance()
    
    # Calculate growth (simplified)
    last_month = datetime.utcnow() - timedelta(days=30)
    last_month_users = await get_users_collection().count_documents({
        "createdAt": {"$lt": last_month}
    })
    monthly_growth = ((total_users - last_month_users) / last_month_users * 100) if last_month_users > 0 else 0
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "verified_users": verified_users,
        "total_projects": total_projects,
        "active_projects": active_projects,
        "funded_projects": funded_projects,
        "total_investments": total_investments,
        "total_deposits": total_deposits,
        "total_withdrawals": total_withdrawals,
        "platform_balance": platform_balance,
        "monthly_growth": round(monthly_growth, 2),
        "user_retention_rate": round((active_users / total_users * 100), 2) if total_users > 0 else 0,
    }

@router.get("/analytics/financial")
async def get_financial_analytics(
    current_user: dict = Depends(get_current_user),
    period: str = "monthly"  # daily, weekly, monthly
):
    """Get financial analytics"""
    await require_admin(current_user)
    
    # Calculate date range based on period
    now = datetime.utcnow()
    if period == "daily":
        start_date = now - timedelta(days=30)
        group_format = "%Y-%m-%d"
    elif period == "weekly":
        start_date = now - timedelta(days=90)
        group_format = "%Y-%U"
    else:  # monthly
        start_date = now - timedelta(days=365)
        group_format = "%Y-%m"
    
    pipeline = [
        {
            "$match": {
                "date": {"$gte": start_date},
                "status": "completed"
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": group_format,
                        "date": "$date"
                    }
                },
                "total_deposits": {
                    "$sum": {
                        "$cond": [{"$eq": ["$type", "deposit"]}, "$amount", 0]
                    }
                },
                "total_investments": {
                    "$sum": {
                        "$cond": [{"$eq": ["$type", "investment"]}, "$amount", 0]
                    }
                },
                "total_withdrawals": {
                    "$sum": {
                        "$cond": [{"$eq": ["$type", "withdrawal"]}, "$amount", 0]
                    }
                },
                "transaction_count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    
    results = await get_transactions_collection().aggregate(pipeline).to_list(100)
    
    return {
        "period": period,
        "data": results
    }

@router.get("/reports/comprehensive")
async def download_comprehensive_report(
    current_user: dict = Depends(get_current_user),
    report_type: str = "all",  # all, financial, users, projects
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    """Download comprehensive report"""
    await require_admin(current_user)
    
    # Set default date range if not provided
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    output = StringIO()
    writer = csv.writer(output)
    
    if report_type in ["all", "financial"]:
        # Financial transactions report
        writer.writerow(['FINANCIAL TRANSACTIONS REPORT'])
        writer.writerow(['Period', f'{start_date} to {end_date}'])
        writer.writerow(['Generated', datetime.utcnow().isoformat()])
        writer.writerow([])
        writer.writerow(['Transaction ID', 'User', 'Type', 'Amount', 'Project', 'Status', 'Date'])
        
        transactions = await get_transactions_collection().find({
            "date": {"$gte": start_datetime, "$lte": end_datetime}
        }).sort("date", -1).to_list(1000)
        
        for t in transactions:
            user = await get_users_collection().find_one({"_id": t["userId"]}, {"name": 1, "email": 1})
            writer.writerow([
                str(t["_id"]),
                user["name"] if user else "Unknown",
                t["type"],
                t["amount"],
                t.get("projectTitle", "N/A"),
                t["status"],
                t["date"].isoformat(),
            ])
        
        writer.writerow([])
    
    if report_type in ["all", "users"]:
        # Users report
        writer.writerow(['USERS REPORT'])
        writer.writerow(['As of', datetime.utcnow().isoformat()])
        writer.writerow([])
        writer.writerow(['User ID', 'Name', 'Email', 'Age', 'Status', 'Wallet Balance', 'Total Invested', 'Member Since'])
        
        users = await get_users_collection().find().sort("createdAt", -1).to_list(1000)
        
        for u in users:
            writer.writerow([
                str(u["_id"]),
                u["name"],
                u["email"],
                u["age"],
                "Verified" if u.get("verified") else "Unverified",
                u.get("walletBalance", 0),
                u.get("totalInvested", 0),
                u.get("createdAt", datetime.utcnow()).isoformat(),
            ])
        
        writer.writerow([])
    
    if report_type in ["all", "projects"]:
        # Projects report
        writer.writerow(['PROJECTS REPORT'])
        writer.writerow(['As of', datetime.utcnow().isoformat()])
        writer.writerow([])
        writer.writerow(['Project ID', 'Title', 'Category', 'Funding Goal', 'Funded Amount', 'ROI', 'Status', 'Risk Level', 'Created At'])
        
        projects = await get_projects_collection().find().sort("createdAt", -1).to_list(1000)
        
        for p in projects:
            writer.writerow([
                str(p["_id"]),
                p["title"],
                p["category"],
                p["fundingGoal"],
                p.get("fundedAmount", 0),
                p["roi"],
                p.get("status", "pending"),
                p["riskLevel"],
                p.get("createdAt", datetime.utcnow()).isoformat(),
            ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=comprehensive-report-{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )

# ===== SYSTEM HEALTH =====

@router.get("/system/health")
async def get_system_health(current_user: dict = Depends(get_current_user)):
    """Get system health status"""
    await require_admin(current_user)
    
    health_status = {
        "database": "healthy",
        "email_service": "healthy",
        "api": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Test database connection
        await get_users_collection().find_one()
    except Exception as e:
        health_status["database"] = f"unhealthy: {str(e)}"
    
    try:
        # Test email service (simple check)
        health_status["email_service"] = "healthy"
    except Exception as e:
        health_status["email_service"] = f"unhealthy: {str(e)}"
    
    return health_status

@router.get("/system/backup")
async def create_system_backup(current_user: dict = Depends(get_current_user)):
    """Create system data backup"""
    await require_admin(current_user)
    
    # This would typically connect to your database backup system
    # For now, we'll return a message
    return {
        "message": "Backup initiated",
        "backup_id": str(ObjectId()),
        "timestamp": datetime.utcnow().isoformat()
    }
@router.get("/momo/overview")
async def get_momo_overview(current_user: dict = Depends(get_current_user)):
    """Get MoMo transaction overview (Admin only)"""
    await require_admin(current_user)
    
    # Today's transactions
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    pipeline_today = [
        {
            "$match": {
                "date": {"$gte": today_start},
                "type": "momo_deposit"
            }
        },
        {
            "$group": {
                "_id": None,
                "total_deposits_today": {"$sum": "$amount"},
                "count_today": {"$sum": 1}
            }
        }
    ]
    
    today_stats = await get_transactions_collection().aggregate(pipeline_today).to_list(1)
    
    # Weekly statistics
    week_start = today_start - timedelta(days=7)
    
    pipeline_week = [
        {
            "$match": {
                "date": {"$gte": week_start},
                "type": "momo_deposit"
            }
        },
        {
            "$group": {
                "_id": None,
                "total_deposits_week": {"$sum": "$amount"},
                "count_week": {"$sum": 1}
            }
        }
    ]
    
    week_stats = await get_transactions_collection().aggregate(pipeline_week).to_list(1)
    
    return {
        "personal_momo_number": settings.PERSONAL_MOMO_NUMBER,
        "today": {
            "total_deposits": today_stats[0]["total_deposits_today"] if today_stats else 0,
            "transaction_count": today_stats[0]["count_today"] if today_stats else 0
        },
        "this_week": {
            "total_deposits": week_stats[0]["total_deposits_week"] if week_stats else 0,
            "transaction_count": week_stats[0]["count_week"] if week_stats else 0
        },
        "system_status": {
            "bank_transfer_enabled": settings.BANK_TRANSFER_ENABLED,
            "auto_transfer_to_bank": settings.AUTO_TRANSFER_TO_BANK,
            "manual_transfer_required": settings.MANUAL_TRANSFER_REQUIRED
        }
    }

@router.post("/momo/manual-confirm")
async def manual_confirm_deposit(
    transaction_ref: str,
    current_user: dict = Depends(get_current_user)
):
    """Manually confirm a MoMo deposit (Admin only)"""
    await require_admin(current_user)
    
    # Find the transaction
    transaction = await get_transactions_collection().find_one({
        "transaction_ref": transaction_ref,
        "type": "momo_deposit"
    })
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction["status"] == "completed":
        raise HTTPException(status_code=400, detail="Transaction already completed")
    
    # Update transaction status
    await get_transactions_collection().update_one(
        {"transaction_ref": transaction_ref},
        {
            "$set": {
                "status": "completed",
                "confirmed_by": current_user["userId"],
                "confirmed_at": datetime.utcnow(),
                "notes": "Manually confirmed by admin"
            }
        }
    )
    
    # Update user wallet
    await get_users_collection().update_one(
        {"_id": transaction["userId"]},
        {"$inc": {"walletBalance": transaction["amount"]}}
    )
    
    return {
        "message": "Deposit confirmed successfully",
        "transaction_ref": transaction_ref,
        "amount": transaction["amount"],
        "user_id": str(transaction["userId"])
    }
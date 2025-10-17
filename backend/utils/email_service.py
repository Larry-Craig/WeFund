from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from config import settings
import secrets
import string
from datetime import datetime, timedelta
from utils.database import get_verification_collection, get_admin_emails_collection
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

fm = FastMail(conf)

def generate_verification_code(length: int = 6) -> str:
    """Generate a random verification code"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def generate_email_token() -> str:
    """Generate a secure token for email verification"""
    return secrets.token_urlsafe(32)

async def send_welcome_email(user_email: str, user_name: str, verification_token: str):
    """Send welcome email with verification link"""
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
    
    # Simple HTML email template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .button {{ display: inline-block; padding: 12px 30px; background: #4F46E5; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
            .code {{ font-size: 24px; font-weight: bold; text-align: center; margin: 20px 0; padding: 15px; background: #eee; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to WeFund! 🎉</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name},</h2>
                <p>Thank you for registering with WeFund - your gateway to innovative investment opportunities!</p>
                <p>To get started and access your dashboard, please verify your email address by clicking the button below:</p>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                </p>
                
                <p>If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background: #eee; padding: 10px; border-radius: 5px; font-size: 12px;">
                    {verification_url}
                </p>
                
                <p><strong>What's next?</strong></p>
                <ul>
                    <li>Explore investment opportunities</li>
                    <li>Set up your wallet</li>
                    <li>Start investing in vetted projects</li>
                    <li>Track your returns in real-time</li>
                </ul>
                
                <p>If you didn't create an account with WeFund, please ignore this email.</p>
                
                <p>Happy investing!<br>The WeFund Team</p>
            </div>
            <div class="footer">
                <p>&copy; 2024 WeFund. All rights reserved.</p>
                <p>This is an automated message, please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    message = MessageSchema(
        subject="Welcome to WeFund - Verify Your Email",
        recipients=[user_email],
        body=html_content,
        subtype="html"
    )
    
    try:
        await fm.send_message(message)
        logger.info(f"Welcome email sent to {user_email}")
        return True
    except Exception as e:
        logger.error(f"Error sending email to {user_email}: {e}")
        return False

async def send_phone_verification_email(user_email: str, user_name: str, verification_code: str):
    """Send phone verification code via email (fallback)"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #10B981; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .code {{ font-size: 32px; font-weight: bold; text-align: center; margin: 20px 0; padding: 20px; background: #eee; border-radius: 10px; letter-spacing: 5px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Phone Verification Code</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name},</h2>
                <p>Your WeFund phone verification code is:</p>
                
                <div class="code">{verification_code}</div>
                
                <p>Enter this code in the WeFund app to verify your phone number.</p>
                <p>This code will expire in 10 minutes.</p>
                
                <p>If you didn't request this code, please ignore this email.</p>
                
                <p>Best regards,<br>The WeFund Team</p>
            </div>
            <div class="footer">
                <p>&copy; 2024 WeFund. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    message = MessageSchema(
        subject="WeFund - Phone Verification Code",
        recipients=[user_email],
        body=html_content,
        subtype="html"
    )
    
    try:
        await fm.send_message(message)
        logger.info(f"Phone verification email sent to {user_email}")
        return True
    except Exception as e:
        logger.error(f"Error sending phone verification email to {user_email}: {e}")
        return False

async def store_verification_data(user_id: str, email_token: str, phone_code: str = None, phone_number: str = None):
    """Store verification data in database"""
    verification_data = {
        "userId": user_id,
        "emailToken": email_token,
        "emailVerified": False,
        "phoneCode": phone_code,
        "phoneVerified": False,
        "phoneNumber": phone_number,
        "createdAt": datetime.utcnow(),
        "expiresAt": datetime.utcnow() + timedelta(hours=24)  # 24 hours expiry
    }
    
    await get_verification_collection().insert_one(verification_data)

async def verify_email_token(token: str) -> dict:
    """Verify email token and mark email as verified"""
    verification = await get_verification_collection().find_one({
        "emailToken": token,
        "expiresAt": {"$gt": datetime.utcnow()}
    })
    
    if not verification:
        return {"success": False, "message": "Invalid or expired verification token"}
    
    # Update verification status
    await get_verification_collection().update_one(
        {"_id": verification["_id"]},
        {"$set": {"emailVerified": True, "emailVerifiedAt": datetime.utcnow()}}
    )
    
    # Update user verification status
    from utils.database import get_users_collection
    await get_users_collection().update_one(
        {"_id": verification["userId"]},
        {"$set": {"verified": True}}
    )
    
    return {"success": True, "userId": str(verification["userId"])}

async def verify_phone_code(user_id: str, code: str) -> dict:
    """Verify phone verification code"""
    verification = await get_verification_collection().find_one({
        "userId": user_id,
        "phoneCode": code,
        "expiresAt": {"$gt": datetime.utcnow()}
    })
    
    if not verification:
        return {"success": False, "message": "Invalid or expired verification code"}
    
    # Update phone verification status
    await get_verification_collection().update_one(
        {"_id": verification["_id"]},
        {"$set": {"phoneVerified": True, "phoneVerifiedAt": datetime.utcnow()}}
    )
    
    return {"success": True}
async def send_admin_email(
    recipients: List[str],
    subject: str,
    content: str,
    template_type: str = "custom"
):
    """Send email from admin to users"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>WeFund Official Communication</h1>
            </div>
            <div class="content">
                {content}
                <br><br>
                <p>Best regards,<br>The WeFund Team</p>
            </div>
            <div class="footer">
                <p>&copy; 2024 WeFund. All rights reserved.</p>
                <p>This is an official communication from WeFund.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=html_content,
        subtype="html"
    )
    
    try:
        await fm.send_message(message)
        
        # Log the email in database
        await get_admin_emails_collection().insert_one({
            "subject": subject,
            "recipients": recipients,
            "template_type": template_type,
            "content": content,
            "status": "sent",
            "sent_at": datetime.utcnow(),
            "created_at": datetime.utcnow()
        })
        
        logger.info(f"Admin email sent to {len(recipients)} recipients")
        return True
    except Exception as e:
        logger.error(f"Error sending admin email: {e}")
        
        # Log failed attempt
        await get_admin_emails_collection().insert_one({
            "subject": subject,
            "recipients": recipients,
            "template_type": template_type,
            "content": content,
            "status": "failed",
            "error": str(e),
            "created_at": datetime.utcnow()
        })
        
        return False

async def send_project_status_email(user_email: str, user_name: str, project_title: str, status: str, notes: str = None):
    """Send project status update email"""
    status_colors = {
        "approved": "#10B981",
        "rejected": "#EF4444",
        "under_review": "#F59E0B"
    }
    
    status_messages = {
        "approved": "has been approved and is now open for investments!",
        "rejected": "has been rejected.",
        "under_review": "is currently under review by our team."
    }
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: {status_colors.get(status, '#4F46E5')}; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .status-badge {{ display: inline-block; padding: 5px 15px; background: {status_colors.get(status, '#4F46E5')}; color: white; border-radius: 20px; text-transform: capitalize; }}
            .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Project Status Update</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name},</h2>
                <p>Your project <strong>"{project_title}"</strong> {status_messages.get(status, 'status has been updated.')}</p>
                
                <p>Status: <span class="status-badge">{status.replace('_', ' ')}</span></p>
                
                {f'<p><strong>Review Notes:</strong> {notes}</p>' if notes else ''}
                
                <p>
                    {f'<a href="{settings.FRONTEND_URL}/projects" style="display: inline-block; padding: 12px 30px; background: #4F46E5; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">View Project</a>' if status == 'approved' else ''}
                </p>
                
                <p>If you have any questions, please contact our support team.</p>
                
                <p>Best regards,<br>The WeFund Team</p>
            </div>
            <div class="footer">
                <p>&copy; 2024 WeFund. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    message = MessageSchema(
        subject=f"Project Update: {project_title}",
        recipients=[user_email],
        body=html_content,
        subtype="html"
    )
    
    try:
        await fm.send_message(message)
        return True
    except Exception as e:
        logger.error(f"Error sending project status email: {e}")
        return False
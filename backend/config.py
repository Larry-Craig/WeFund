import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://WeFund:cheboy2005@wefund.qgtyo6h.mongodb.net/?retryWrites=true&w=majority&appName=WeFund")
    JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-this-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS = 30
    DATABASE_NAME = "WeFund"
    
    # Email settings
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_FROM = os.getenv("MAIL_FROM")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "True").lower() == "true"
    MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"
    
    # Frontend URLs
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
    VERIFICATION_SUCCESS_URL = os.getenv("VERIFICATION_SUCCESS_URL", "/dashboard")
    VERIFICATION_FAILED_URL = os.getenv("VERIFICATION_FAILED_URL", "/verification-failed")
    
    # Admin settings
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@wefund.com")
    SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@wefund.com")
    # API Versioning
    API_V1_PREFIX = "/api/v1"
    
    # Rate Limiting
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    
    # Mobile Money - MPesa
    MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
    MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
    MPESA_SHORTCODE = os.getenv("MPESA_SHORTCODE")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
    MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL")
    
    # Mobile Money - Orange Money
    ORANGE_MONEY_API_KEY = os.getenv("ORANGE_MONEY_API_KEY")
    ORANGE_MONEY_API_SECRET = os.getenv("ORANGE_MONEY_API_SECRET")
    ORANGE_MONEY_MERCHANT_CODE = os.getenv("ORANGE_MONEY_MERCHANT_CODE")
    
    # Push Notifications
    FIREBASE_SERVER_KEY = os.getenv("FIREBASE_SERVER_KEY")
    
    # KYC/AML
    KYC_API_KEY = os.getenv("KYC_API_KEY")
    AML_API_KEY = os.getenv("AML_API_KEY")
    
    # Business Rules
    MAX_INVESTMENT_UNVERIFIED = float(os.getenv("MAX_INVESTMENT_UNVERIFIED", "50000"))
    MAX_INVESTMENT_VERIFIED = float(os.getenv("MAX_INVESTMENT_VERIFIED", "500000"))
    MAX_INVESTMENT_PREMIUM = float(os.getenv("MAX_INVESTMENT_PREMIUM", "2000000"))
    
    # File Upload
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES = ["image/jpeg", "image/png", "application/pdf"]

    # Personal MoMo (Temporary)
    PERSONAL_MOMO_NUMBER = os.getenv("PERSONAL_MOMO_NUMBER", "678394294")
    PERSONAL_MOMO_PROVIDER = os.getenv("PERSONAL_MOMO_PROVIDER", "mtn_money")
    
    # Bank Transfer Settings
    BANK_TRANSFER_ENABLED = os.getenv("BANK_TRANSFER_ENABLED", "false").lower() == "true"
    BANK_ACCOUNT_NUMBER = os.getenv("BANK_ACCOUNT_NUMBER")
    BANK_NAME = os.getenv("BANK_NAME")
    BANK_ROUTING_NUMBER = os.getenv("BANK_ROUTING_NUMBER")
    
    # Transfer Schedule
    AUTO_TRANSFER_TO_BANK = os.getenv("AUTO_TRANSFER_TO_BANK", "false").lower() == "true"
    MANUAL_TRANSFER_REQUIRED = os.getenv("MANUAL_TRANSFER_REQUIRED", "true").lower() == "true"


settings = Settings()
# WeFund - Crowdfunding Platform Backend

A comprehensive FastAPI backend for a crowdfunding platform with mobile money integration.

## 🚀 Features

- **User Management**: Registration, authentication, profile management
- **Project System**: Project creation, investment, vetting, and tracking
- **Mobile Money**: MoMo integration for deposits and withdrawals
- **Admin Dashboard**: Comprehensive analytics and user management
- **KYC/AML**: Identity verification and compliance checks
- **Real-time Features**: Messaging and push notifications
- **Security**: JWT authentication, rate limiting, input validation

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **Database**: MongoDB with Motor
- **Authentication**: JWT tokens
- **Payments**: Mobile Money (MoMo)
- **Security**: bcrypt, rate limiting
- **Notifications**: Firebase Cloud Messaging

## 📱 Mobile Money Integration

Currently using personal MoMo number: `678394294` for deposits. Ready for bank integration.

## 🚀 Quick Start

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in `.env`
4. Run: `uvicorn main:app --reload`

## 📚 API Documentation

Once running, visit: `http://localhost:8000/docs`

## 🔧 Configuration

See `.env.example` for required environment variables.

## 📄 License

MIT License
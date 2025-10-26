# 🏦 SmartBank API - Secure Banking System

> A comprehensive banking backend system built with FastAPI, featuring account management, secure transactions, loan processing, and intelligent fraud detection.

**Built for:** HCL Hackathon  
**Tech Stack:** FastAPI, SQLAlchemy, JWT Authentication, SQLite

---

## 🌟 Features

### 👥 User Management
- ✅ User registration with KYC verification
- ✅ Secure login with JWT authentication
- ✅ Role-based access control (Customer, Admin, Auditor)
- ✅ Password hashing with bcrypt

### 💳 Account Management
- ✅ Multiple account types (Savings, Current, Fixed Deposit)
- ✅ Unique account number generation
- ✅ Account balance tracking
- ✅ Daily transaction limits

### 💸 Transactions
- ✅ Money transfers between accounts
- ✅ Real-time balance updates
- ✅ Transaction history with timestamps
- ✅ Transaction descriptions and metadata

### 🚨 Fraud Detection
- ✅ Daily limit checking
- ✅ Multiple transaction pattern detection
- ✅ Large withdrawal alerts (>80% balance)
- ✅ Automatic flagging of suspicious transactions
- ✅ Detailed fraud reasoning

### 🏠 Loan Management
- ✅ Loan application (Personal, Home, Car, Education)
- ✅ EMI calculation using standard formula
- ✅ Admin approval workflow
- ✅ Interest rate configuration
- ✅ Loan status tracking

### 🔍 Audit & Compliance
- ✅ Comprehensive audit logging
- ✅ User activity tracking
- ✅ IP address logging
- ✅ Timestamp for all operations
- ✅ Auditor role access

### 👨‍💼 Admin Features
- ✅ View all users
- ✅ Approve/reject loan applications
- ✅ View flagged transactions
- ✅ System dashboard with statistics

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

1. **Clone the repository**
```bash
cd smartbank
```

2. **Install dependencies**
```bash
pip install fastapi uvicorn sqlalchemy passlib[bcrypt] python-jose[cryptography] python-multipart email-validator
```

3. **Run the server**
```bash
uvicorn app.main:app --reload
```

4. **Access the API**
- API Documentation: http://127.0.0.1:8000/docs
- Alternative Docs: http://127.0.0.1:8000/redoc

---

## 📚 API Endpoints

### Authentication
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Register new customer | ❌ |
| POST | `/auth/login` | Login and get JWT token | ❌ |
| GET | `/auth/me` | Get current user info | ✅ |

### Accounts
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/accounts` | Create new account | ✅ |
| GET | `/accounts` | List all my accounts | ✅ |
| GET | `/accounts/{account_number}` | Get account details | ✅ |

### Transactions
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/transactions/transfer` | Transfer money | ✅ |
| GET | `/transactions/history/{account_number}` | Get transaction history | ✅ |

### Loans
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/loans/apply` | Apply for a loan | ✅ |
| GET | `/loans` | View my loans | ✅ |

### Admin
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/admin/loans/{loan_id}/approve` | Approve/reject loan | ✅ Admin |
| GET | `/admin/users` | View all users | ✅ Admin |
| GET | `/admin/transactions/flagged` | View flagged transactions | ✅ Admin |
| GET | `/admin/dashboard` | System statistics | ✅ Admin |

---

## 🧪 Testing the API

### 1. Register a Customer
```bash
POST /auth/register
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "password123",
  "phone": "9876543210"
}
```

### 2. Login
```bash
POST /auth/login
{
  "email": "john@example.com",
  "password": "password123"
}
```
**Copy the `access_token` from response**

### 3. Authorize (in Swagger UI)
- Click 🔓 **Authorize** button
- Paste your token
- Click **Authorize**

### 4. Create an Account
```bash
POST /accounts
{
  "account_type": "savings",
  "initial_deposit": 10000
}
```

### 5. Transfer Money
```bash
POST /transactions/transfer
{
  "from_account_number": "1234567890",
  "to_account_number": "0987654321",
  "amount": 5000,
  "description": "Payment"
}
```

### 6. Apply for Loan
```bash
POST /loans/apply
{
  "loan_type": "home",
  "amount": 500000,
  "tenure_months": 120
}
```

---

## 🔐 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt encryption for passwords
- **Role-Based Access**: Customer, Admin, Auditor roles
- **Protected Endpoints**: Authorization required for sensitive operations
- **Audit Logging**: Complete activity tracking

---

## 🤖 Fraud Detection Rules

The system automatically flags suspicious transactions based on:

1. **Daily Limit Exceeded**: Transactions over ₹50,000
2. **Multiple Large Transactions**: 3+ transactions over ₹10,000 in 1 hour
3. **Large Withdrawals**: Single withdrawal >80% of balance and >₹50,000

Flagged transactions are marked with `is_flagged: true` and include a `flag_reason`.

---

## 📊 Database Schema

### Tables
- **users**: User accounts with authentication
- **accounts**: Bank accounts with balances
- **transactions**: All financial transactions
- **loans**: Loan applications and approvals
- **audit_logs**: System activity logs

### Relationships
- User → Accounts (One-to-Many)
- User → Loans (One-to-Many)
- Account → Transactions (One-to-Many)
- User → AuditLogs (One-to-Many)

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| FastAPI | Web framework |
| SQLAlchemy | ORM for database operations |
| SQLite | Database |
| Pydantic | Data validation |
| JWT | Authentication tokens |
| Bcrypt | Password hashing |
| Uvicorn | ASGI server |

---

## 📁 Project Structure

```
smartbank/
├── app/
│   ├── __init__.py
│   ├── main.py          # API endpoints
│   ├── models.py        # Database models
│   └── database.py      # Database configuration
├── smartbank.db         # SQLite database
├── create_admin.py      # Admin user creation script
└── README.md            # This file
```

---

## 👨‍💼 Creating an Admin User

Run the admin creation script:
```bash
python create_admin.py
```

**Default Admin Credentials:**
- Email: `admin@smartbank.com`
- Password: `admin123`

---

## 🎯 Use Cases Covered

✅ User Registration & KYC  
✅ Account Creation (Savings/Current/FD)  
✅ Money Transfer with Validations  
✅ Loan Application & EMI Calculation  
✅ Fraud Detection  
✅ Audit Logging  
✅ Admin Dashboard  

---

## 🚀 Future Enhancements

- [ ] ML-based fraud detection with Isolation Forest
- [ ] KYC document upload and verification
- [ ] Email notifications
- [ ] SMS alerts for transactions
- [ ] Rate limiting for API endpoints
- [ ] Redis caching for performance
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Frontend dashboard
- [ ] Mobile app integration

---

## 📝 License

This project is created for educational purposes as part of the HCL Hackathon.

---

## 👤 Author

**Your Name**  
Built for HCL Hackathon 2025

---

## 📞 Support

For questions or issues, please refer to the API documentation at `/docs` endpoint.

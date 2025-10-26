from fastapi import FastAPI, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, Field
import random
import string
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app import models
from app.database import engine, SessionLocal

# Create tables
models.Base.metadata.create_all(bind=engine)

# Configuration
SECRET_KEY = "smartbank-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# FastAPI app
app = FastAPI(
    title="SmartBank API - HCL Hackathon",
    description="Secure Banking System with Account Management, Transactions, Loans & Fraud Detection",
    version="1.0.0"
)

# ========== PYDANTIC SCHEMAS ==========

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: Optional[str] = None

class KYCUpload(BaseModel):
    document_type: str = Field(..., description="aadhar, pan, passport")
    document_number: str
    document_data: str = Field(..., description="Base64 encoded or simulated")

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: models.UserRole
    kyc_verified: bool
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AccountCreate(BaseModel):
    account_type: models.AccountType
    initial_deposit: float = Field(default=0, ge=0)

class AccountResponse(BaseModel):
    id: int
    account_number: str
    account_type: models.AccountType
    balance: float
    is_active: bool
    class Config:
        from_attributes = True

class TransferRequest(BaseModel):
    from_account_number: str
    to_account_number: str
    amount: float = Field(..., gt=0)
    description: Optional[str] = None

class TransactionResponse(BaseModel):
    id: int
    transaction_type: models.TransactionType
    amount: float
    is_flagged: bool
    flag_reason: Optional[str]
    timestamp: datetime
    class Config:
        from_attributes = True

class LoanApplication(BaseModel):
    loan_type: models.LoanType
    amount: float = Field(..., gt=0)
    tenure_months: int = Field(..., gt=0, le=360)

class LoanResponse(BaseModel):
    id: int
    loan_type: models.LoanType
    amount: float
    tenure_months: int
    interest_rate: float
    emi: Optional[float]
    status: models.LoanStatus
    class Config:
        from_attributes = True

# ========== UTILITY FUNCTIONS ==========

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def generate_account_number() -> str:
    return ''.join(random.choices(string.digits, k=10))

def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    monthly_rate = annual_rate / (12 * 100)
    if monthly_rate == 0:
        return principal / tenure_months
    emi = (principal * monthly_rate * (1 + monthly_rate) ** tenure_months) / \
          ((1 + monthly_rate) ** tenure_months - 1)
    return round(emi, 2)

def check_fraud(amount: float, account: models.Account, db: Session) -> tuple[bool, str]:
    # Rule 1: Exceeds daily limit
    if amount > account.daily_limit:
        return True, f"Exceeds daily limit of ₹{account.daily_limit}"
    
    # Rule 2: Multiple large transactions
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_large = db.query(models.Transaction).filter(
        models.Transaction.from_account_id == account.id,
        models.Transaction.timestamp >= one_hour_ago,
        models.Transaction.amount > 10000
    ).count()
    if recent_large >= 3:
        return True, "Multiple large transactions in last hour"
    
    # Rule 3: Large withdrawal (>80% balance)
    if amount > (account.balance * 0.8) and amount > 50000:
        return True, "Large withdrawal >80% of balance"
    
    return False, ""

def create_audit_log(db: Session, user_id: int, action: str, details: str = None):
    log = models.AuditLog(user_id=user_id, action=action, details=details)
    db.add(log)
    db.commit()

# ========== AUTHENTICATION ENDPOINTS ==========

@app.post("/auth/register", response_model=UserResponse, status_code=201, tags=["Authentication"])
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new customer"""
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = models.User(
        name=user.name,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        phone=user.phone,
        role=models.UserRole.CUSTOMER
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    create_audit_log(db, new_user.id, "USER_REGISTERED", f"User {user.name} registered")
    return new_user

@app.post("/auth/login", response_model=Token, tags=["Authentication"])
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login and receive JWT token"""
    user = db.query(models.User).filter(models.User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
    create_audit_log(db, user.id, "LOGIN", "User logged in")
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
def get_me(current_user: models.User = Depends(get_current_user)):
    """Get current user info"""
    return current_user

@app.post("/auth/kyc-upload", tags=["Authentication"])
def upload_kyc(
    kyc_data: KYCUpload,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Simulate KYC document upload"""
    # In real system, you'd save file to storage
    # Here we just mark user as KYC verified
    current_user.kyc_verified = True
    db.commit()
    
    create_audit_log(
        db, current_user.id, "KYC_UPLOADED",
        f"KYC document uploaded: {kyc_data.document_type} - {kyc_data.document_number}"
    )
    
    return {
        "message": "KYC document uploaded successfully",
        "kyc_verified": True,
        "document_type": kyc_data.document_type
    }

# ========== ACCOUNT MANAGEMENT ==========

@app.post("/accounts", response_model=AccountResponse, status_code=201, tags=["Accounts"])
def create_account(
    account_data: AccountCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new bank account"""
    while True:
        account_number = generate_account_number()
        if not db.query(models.Account).filter(models.Account.account_number == account_number).first():
            break
    
    new_account = models.Account(
        account_number=account_number,
        user_id=current_user.id,
        account_type=account_data.account_type,
        balance=account_data.initial_deposit
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    
    create_audit_log(db, current_user.id, "ACCOUNT_CREATED", f"Account {account_number} created")
    return new_account

@app.get("/accounts", response_model=List[AccountResponse], tags=["Accounts"])
def list_accounts(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all my accounts"""
    return db.query(models.Account).filter(models.Account.user_id == current_user.id).all()

@app.get("/accounts/{account_number}", response_model=AccountResponse, tags=["Accounts"])
def get_account(
    account_number: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get account details"""
    account = db.query(models.Account).filter(
        models.Account.account_number == account_number,
        models.Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account

# ========== TRANSACTIONS ==========

@app.post("/transactions/transfer", response_model=TransactionResponse, tags=["Transactions"])
def transfer(
    transfer: TransferRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Transfer money between accounts"""
    from_acc = db.query(models.Account).filter(
        models.Account.account_number == transfer.from_account_number,
        models.Account.user_id == current_user.id
    ).first()
    if not from_acc or not from_acc.is_active:
        raise HTTPException(status_code=404, detail="Source account not found or inactive")
    
    to_acc = db.query(models.Account).filter(
        models.Account.account_number == transfer.to_account_number
    ).first()
    if not to_acc or not to_acc.is_active:
        raise HTTPException(status_code=404, detail="Destination account not found or inactive")
    
    if from_acc.balance < transfer.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # Fraud detection
    is_fraud, reason = check_fraud(transfer.amount, from_acc, db)
    
    # Execute transfer
    from_acc.balance -= transfer.amount
    to_acc.balance += transfer.amount
    
    transaction = models.Transaction(
        transaction_type=models.TransactionType.TRANSFER,
        from_account_id=from_acc.id,
        to_account_id=to_acc.id,
        amount=transfer.amount,
        balance_after=from_acc.balance,
        description=transfer.description,
        is_flagged=is_fraud,
        flag_reason=reason if is_fraud else None
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    create_audit_log(
        db, current_user.id, "TRANSFER",
        f"₹{transfer.amount} from {transfer.from_account_number} to {transfer.to_account_number}"
    )
    
    return transaction

@app.get("/transactions/history/{account_number}", response_model=List[TransactionResponse], tags=["Transactions"])
def transaction_history(
    account_number: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get transaction history"""
    account = db.query(models.Account).filter(
        models.Account.account_number == account_number,
        models.Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return db.query(models.Transaction).filter(
        (models.Transaction.from_account_id == account.id) |
        (models.Transaction.to_account_id == account.id)
    ).order_by(models.Transaction.timestamp.desc()).limit(50).all()

# ========== LOAN MANAGEMENT ==========

@app.post("/loans/apply", response_model=LoanResponse, status_code=201, tags=["Loans"])
def apply_loan(
    loan: LoanApplication,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply for a loan"""
    new_loan = models.Loan(
        user_id=current_user.id,
        loan_type=loan.loan_type,
        amount=loan.amount,
        tenure_months=loan.tenure_months,
        interest_rate=8.5,
        status=models.LoanStatus.PENDING
    )
    db.add(new_loan)
    db.commit()
    db.refresh(new_loan)
    
    create_audit_log(db, current_user.id, "LOAN_APPLIED", f"{loan.loan_type} loan for ₹{loan.amount}")
    return new_loan

@app.get("/loans", response_model=List[LoanResponse], tags=["Loans"])
def my_loans(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all my loans"""
    return db.query(models.Loan).filter(models.Loan.user_id == current_user.id).all()

@app.post("/admin/loans/{loan_id}/approve", response_model=LoanResponse, tags=["Admin"])
def approve_loan(
    loan_id: int,
    approved: bool,
    interest_rate: float = 8.5,
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Admin: Approve or reject loan"""
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    if approved:
        loan.status = models.LoanStatus.APPROVED
        loan.interest_rate = interest_rate
        loan.emi = calculate_emi(loan.amount, interest_rate, loan.tenure_months)
        loan.approved_at = datetime.utcnow()
        loan.approved_by = current_admin.id
    else:
        loan.status = models.LoanStatus.REJECTED
    
    db.commit()
    db.refresh(loan)
    
    create_audit_log(
        db, current_admin.id, "LOAN_APPROVED" if approved else "LOAN_REJECTED",
        f"Loan ID {loan_id} {'approved' if approved else 'rejected'}"
    )
    return loan

# ========== ADMIN ENDPOINTS ==========

@app.get("/admin/users", response_model=List[UserResponse], tags=["Admin"])
def list_all_users(
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Admin: List all users"""
    return db.query(models.User).all()

@app.get("/admin/transactions/flagged", response_model=List[TransactionResponse], tags=["Admin"])
def flagged_transactions(
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Admin: View flagged transactions"""
    return db.query(models.Transaction).filter(
        models.Transaction.is_flagged == True
    ).order_by(models.Transaction.timestamp.desc()).all()

@app.get("/admin/dashboard", tags=["Admin"])
def admin_dashboard(
    current_admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Admin: Dashboard with summary"""
    return {
        "total_users": db.query(models.User).count(),
        "total_accounts": db.query(models.Account).count(),
        "total_transactions": db.query(models.Transaction).count(),
        "flagged_transactions": db.query(models.Transaction).filter(models.Transaction.is_flagged == True).count(),
        "pending_loans": db.query(models.Loan).filter(models.Loan.status == models.LoanStatus.PENDING).count()
    }

# ========== ROOT ==========

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "SmartBank API - HCL Hackathon",
        "docs": "/docs",
        "version": "1.0.0"
    }
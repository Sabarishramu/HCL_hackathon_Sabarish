from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from .models import AccountType, TransactionType, LoanType, LoanStatus, UserRole


# User Schemas
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    role: UserRole
    kyc_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Account Schemas
class AccountCreate(BaseModel):
    account_type: AccountType
    initial_deposit: float = Field(default=0, ge=0)


class AccountResponse(BaseModel):
    id: int
    account_number: str
    account_type: AccountType
    balance: float
    daily_limit: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Transaction Schemas
class TransferRequest(BaseModel):
    from_account_number: str
    to_account_number: str
    amount: float = Field(..., gt=0)
    description: Optional[str] = None


class DepositRequest(BaseModel):
    account_number: str
    amount: float = Field(..., gt=0)
    description: Optional[str] = None


class WithdrawalRequest(BaseModel):
    account_number: str
    amount: float = Field(..., gt=0)
    description: Optional[str] = None


class TransactionResponse(BaseModel):
    id: int
    transaction_type: TransactionType
    amount: float
    balance_after: Optional[float]
    description: Optional[str]
    is_flagged: bool
    flag_reason: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


# Loan Schemas
class LoanApplication(BaseModel):
    loan_type: LoanType
    amount: float = Field(..., gt=0)
    tenure_months: int = Field(..., gt=0, le=360)  # Max 30 years


class LoanResponse(BaseModel):
    id: int
    loan_type: LoanType
    amount: float
    tenure_months: int
    interest_rate: float
    emi: Optional[float]
    status: LoanStatus
    applied_at: datetime
    approved_at: Optional[datetime]

    class Config:
        from_attributes = True


class LoanApproval(BaseModel):
    loan_id: int
    approved: bool
    interest_rate: float = Field(default=8.5, ge=1, le=20)


# Audit Log Schemas
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    details: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


# Dashboard Schemas
class AccountSummary(BaseModel):
    total_accounts: int
    total_balance: float
    savings_accounts: int
    current_accounts: int
    fd_accounts: int


class TransactionSummary(BaseModel):
    total_transactions: int
    total_deposits: float
    total_withdrawals: float
    total_transfers: float
    flagged_transactions: int
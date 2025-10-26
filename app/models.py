from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

# ---------- ENUMS ----------

class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    AUDITOR = "auditor"

class AccountType(str, enum.Enum):
    SAVINGS = "savings"
    CURRENT = "current"
    FD = "fd"

class TransactionType(str, enum.Enum):
    TRANSFER = "transfer"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"

class LoanType(str, enum.Enum):
    HOME = "home"
    PERSONAL = "personal"
    VEHICLE = "vehicle"

class LoanStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# ---------- MODELS ----------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER)
    kyc_verified = Column(Boolean, default=False)

    accounts = relationship("Account", back_populates="user")
    loans = relationship("Loan", back_populates="user")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    account_type = Column(Enum(AccountType), nullable=False)
    balance = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    daily_limit = Column(Float, default=100000)

    user = relationship("User", back_populates="accounts")
    transactions_from = relationship("Transaction", back_populates="from_account", foreign_keys='Transaction.from_account_id')
    transactions_to = relationship("Transaction", back_populates="to_account", foreign_keys='Transaction.to_account_id')


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(Enum(TransactionType))
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    amount = Column(Float)
    balance_after = Column(Float, nullable=True)
    description = Column(String, nullable=True)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="transactions_from")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="transactions_to")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    loan_type = Column(Enum(LoanType))
    amount = Column(Float)
    tenure_months = Column(Integer)
    interest_rate = Column(Float, default=8.5)
    emi = Column(Float, nullable=True)
    status = Column(Enum(LoanStatus), default=LoanStatus.PENDING)
    applied_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, nullable=True)

    user = relationship("User", back_populates="loans")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    details = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

"""
Complete Test Suite for SmartBank API
Place in: tests/test_main.py
Run with: pytest tests/ -v --cov=app
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app, get_db
from app.database import Base
from app import models

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def setup_database():
    """Create fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ========== AUTHENTICATION TESTS ==========

def test_register_user(setup_database):
    """Test user registration"""
    response = client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "password123",
            "phone": "9876543210"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert "id" in data


def test_register_duplicate_email(setup_database):
    """Test duplicate email registration fails"""
    # Register first user
    client.post(
        "/auth/register",
        json={
            "name": "User One",
            "email": "duplicate@example.com",
            "password": "password123"
        }
    )
    
    # Try to register with same email
    response = client.post(
        "/auth/register",
        json={
            "name": "User Two",
            "email": "duplicate@example.com",
            "password": "password456"
        }
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_login_success(setup_database):
    """Test successful login"""
    # Register user first
    client.post(
        "/auth/register",
        json={
            "name": "Login Test",
            "email": "login@example.com",
            "password": "password123"
        }
    )
    
    # Login
    response = client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(setup_database):
    """Test login with wrong password"""
    # Register user
    client.post(
        "/auth/register",
        json={
            "name": "Wrong Pass",
            "email": "wrong@example.com",
            "password": "correctpassword"
        }
    )
    
    # Try wrong password
    response = client.post(
        "/auth/login",
        json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401


def test_get_current_user(setup_database):
    """Test getting current user info"""
    # Register and login
    client.post(
        "/auth/register",
        json={
            "name": "Current User",
            "email": "current@example.com",
            "password": "password123"
        }
    )
    
    login_response = client.post(
        "/auth/login",
        json={"email": "current@example.com", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    # Get current user
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "current@example.com"


# ========== ACCOUNT TESTS ==========

def test_create_account(setup_database):
    """Test account creation"""
    # Register and login
    client.post(
        "/auth/register",
        json={"name": "Account Test", "email": "account@example.com", "password": "pass123"}
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "account@example.com", "password": "pass123"}
    )
    token = login_response.json()["access_token"]
    
    # Create account
    response = client.post(
        "/accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={"account_type": "savings", "initial_deposit": 10000}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["account_type"] == "savings"
    assert data["balance"] == 10000
    assert len(data["account_number"]) == 10


def test_list_accounts(setup_database):
    """Test listing user accounts"""
    # Setup user with account
    client.post(
        "/auth/register",
        json={"name": "List Test", "email": "list@example.com", "password": "pass123"}
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "list@example.com", "password": "pass123"}
    )
    token = login_response.json()["access_token"]
    
    # Create two accounts
    client.post(
        "/accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={"account_type": "savings", "initial_deposit": 5000}
    )
    client.post(
        "/accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={"account_type": "current", "initial_deposit": 3000}
    )
    
    # List accounts
    response = client.get(
        "/accounts",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


# ========== TRANSACTION TESTS ==========

def test_transfer_success(setup_database):
    """Test successful money transfer"""
    # Create two users with accounts
    client.post("/auth/register", json={"name": "User1", "email": "user1@test.com", "password": "pass"})
    client.post("/auth/register", json={"name": "User2", "email": "user2@test.com", "password": "pass"})
    
    # Login as user1
    login1 = client.post("/auth/login", json={"email": "user1@test.com", "password": "pass"})
    token1 = login1.json()["access_token"]
    
    # Login as user2
    login2 = client.post("/auth/login", json={"email": "user2@test.com", "password": "pass"})
    token2 = login2.json()["access_token"]
    
    # Create accounts
    acc1_resp = client.post("/accounts", headers={"Authorization": f"Bearer {token1}"}, 
                           json={"account_type": "savings", "initial_deposit": 10000})
    acc1_number = acc1_resp.json()["account_number"]
    
    acc2_resp = client.post("/accounts", headers={"Authorization": f"Bearer {token2}"}, 
                           json={"account_type": "savings", "initial_deposit": 1000})
    acc2_number = acc2_resp.json()["account_number"]
    
    # Transfer money
    response = client.post(
        "/transactions/transfer",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "from_account_number": acc1_number,
            "to_account_number": acc2_number,
            "amount": 2000,
            "description": "Test transfer"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 2000
    assert data["transaction_type"] == "transfer"


def test_transfer_insufficient_funds(setup_database):
    """Test transfer with insufficient funds"""
    client.post("/auth/register", json={"name": "Poor User", "email": "poor@test.com", "password": "pass"})
    client.post("/auth/register", json={"name": "Rich User", "email": "rich@test.com", "password": "pass"})
    
    login1 = client.post("/auth/login", json={"email": "poor@test.com", "password": "pass"})
    token1 = login1.json()["access_token"]
    
    login2 = client.post("/auth/login", json={"email": "rich@test.com", "password": "pass"})
    token2 = login2.json()["access_token"]
    
    # Create accounts with low balance
    acc1_resp = client.post("/accounts", headers={"Authorization": f"Bearer {token1}"}, 
                           json={"account_type": "savings", "initial_deposit": 100})
    acc1_number = acc1_resp.json()["account_number"]
    
    acc2_resp = client.post("/accounts", headers={"Authorization": f"Bearer {token2}"}, 
                           json={"account_type": "savings", "initial_deposit": 1000})
    acc2_number = acc2_resp.json()["account_number"]
    
    # Try to transfer more than balance
    response = client.post(
        "/transactions/transfer",
        headers={"Authorization": f"Bearer {token1}"},
        json={
            "from_account_number": acc1_number,
            "to_account_number": acc2_number,
            "amount": 5000
        }
    )
    assert response.status_code == 400
    assert "insufficient" in response.json()["detail"].lower()


# ========== LOAN TESTS ==========

def test_apply_for_loan(setup_database):
    """Test loan application"""
    client.post("/auth/register", json={"name": "Loan User", "email": "loan@test.com", "password": "pass"})
    login_resp = client.post("/auth/login", json={"email": "loan@test.com", "password": "pass"})
    token = login_resp
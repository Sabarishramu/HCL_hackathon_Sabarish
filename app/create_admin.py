from app.database import SessionLocal
from app.models import User, UserRole
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()
admin = User(
    name="Admin User",
    email="admin@smartbank.com",
    hashed_password=pwd_context.hash("admin123"),
    role=UserRole.ADMIN,
    kyc_verified=True
)
db.add(admin)
db.commit()
print("✅ Admin created: admin@smartbank.com / admin123")
db.close()
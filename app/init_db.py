from app.database import Base, engine
from app import models

# Create tables
Base.metadata.create_all(bind=engine)
print("Tables created!")

from sqlalchemy import create_engine, text

# SQLite database (file-based)
DATABASE_URL = "sqlite:///smartbank.db"  # DB file will be created in the project folder

# Create engine
engine = create_engine(DATABASE_URL, echo=True, future=True)

# Create a simple test table (optional)
with engine.connect() as conn:
    conn.execute(text("CREATE TABLE IF NOT EXISTS test_table(id INTEGER PRIMARY KEY, name TEXT)"))
    conn.commit()

print("SQLite database 'smartbank.db' created successfully!")

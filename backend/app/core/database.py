from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# In PostgreSQL, we can use pgvector. 
# The engine is configured with standard pooling.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator:
    """
    Dependency generator that yields a database session and closes it 
    after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

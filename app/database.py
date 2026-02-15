from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL, DB_MAX_OVERFLOW, DB_POOL_PRE_PING, DB_POOL_RECYCLE, DB_POOL_SIZE

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=DB_POOL_PRE_PING,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

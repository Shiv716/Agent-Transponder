"""
Database connection and SQLAlchemy models.
"""

import asyncio
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import uuid

from app.core.config import settings


# Convert sync URL to async (postgresql:// -> postgresql+asyncpg://)
def get_async_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


# Async engine
async_engine = create_async_engine(
    get_async_database_url(settings.database_url),
    echo=settings.debug,
    pool_pre_ping=True,
)

# Session factory
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


class Meeting(Base):
    """Processed meeting record."""
    
    __tablename__ = "meetings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Fathom data
    fathom_recording_id = Column(String(100), unique=True, index=True)
    fathom_url = Column(Text)
    fathom_share_url = Column(Text)
    meeting_title = Column(String(500))
    
    # Extracted data
    company_name = Column(String(255))
    company_domain = Column(String(255))
    attendees = Column(Text)  # JSON string
    crm_note = Column(Text)
    action_items = Column(Text)  # JSON string
    full_summary = Column(Text)
    
    # HubSpot data
    hubspot_company_id = Column(String(50))
    hubspot_note_id = Column(String(50))
    
    # Email status
    email_sent_at = Column(DateTime, nullable=True)
    email_recipient = Column(String(255))
    
    # Timestamps
    meeting_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, default=datetime.utcnow)


async def get_db() -> AsyncSession:
    """Dependency for FastAPI routes."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")


async def drop_db():
    """Drop all tables (use with caution)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("⚠️ Database tables dropped")


# CLI support
if __name__ == "__main__":
    import sys
    
    if "--init" in sys.argv:
        asyncio.run(init_db())
    elif "--drop" in sys.argv:
        confirm = input("Are you sure you want to drop all tables? (yes/no): ")
        if confirm.lower() == "yes":
            asyncio.run(drop_db())
        else:
            print("Cancelled.")
    else:
        print("Usage: python -m app.core.database [--init|--drop]")

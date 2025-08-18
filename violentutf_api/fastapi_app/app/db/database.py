# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Database configuration and session management."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# Use SQLite for simplicity (can be changed to PostgreSQL later)
DATABASE_URL = settings.DATABASE_URL or f"sqlite+aiosqlite:///{settings.APP_DATA_DIR}/violentutf_api.db"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=settings.DEBUG, future=True)

# Create async session factory
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class for models
Base = declarative_base()


async def init_db() -> None:
    """Initialize database tables."""
    # Ensure the database directory exists
    if "sqlite" in DATABASE_URL:
        db_path = DATABASE_URL.split("///")[1]
        db_dir = os.path.dirname(db_path)
        Path(db_dir).mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

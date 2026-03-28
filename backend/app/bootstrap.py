"""
First-run bootstrap: creates the admin user if no users exist.
Run automatically on container startup before uvicorn.
"""
import asyncio
import logging
from app.database import engine, AsyncSessionLocal, Base
from app.models.user import User
from app.models.property import Property
from app.models.indicator import PropertyIndicator
from app.models.score import PropertyScore
from app.models.data_source import DataSourceConfig, DataSourceRun
from app.services.auth import hash_password
from app.config import get_settings
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


async def bootstrap():
    # Ensure all tables exist (Alembic handles migrations, but this is a safety net)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            logger.info("Admin user already exists, skipping bootstrap.")
            return

        admin = User(
            email=settings.admin_email,
            name="Admin",
            hashed_password=hash_password(settings.admin_password),
            is_admin=True,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        logger.info(f"✓ Admin user created: {settings.admin_email}")


if __name__ == "__main__":
    asyncio.run(bootstrap())

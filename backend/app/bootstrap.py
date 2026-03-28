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
        user_result = await db.execute(select(User).limit(1))
        if not user_result.scalar_one_or_none():
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
        else:
            logger.info("Admin user already exists, skipping.")

        # Auto-fetch property data on first run if DB is empty
        prop_result = await db.execute(select(Property).limit(1))
        if not prop_result.scalar_one_or_none():
            logger.info("No properties found — queuing initial data fetch for Allegheny County, PA...")
            from app.tasks.refresh_data import run_data_source_task
            run_data_source_task.delay("county_assessor", "Allegheny", "PA")
            logger.info("✓ Data fetch queued. Properties will appear once the task completes (~30 sec).")


if __name__ == "__main__":
    asyncio.run(bootstrap())

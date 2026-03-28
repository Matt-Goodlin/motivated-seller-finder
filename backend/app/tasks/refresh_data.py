"""
Celery tasks for fetching data from all configured sources.
Upserts properties and indicators into the database.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app
from app.config import get_settings
from app.data_sources.registry import get_source_class, ALL_SOURCES
from app.models.indicator import INDICATOR_CATEGORIES

logger = logging.getLogger(__name__)
settings = get_settings()


def _run_async(coro):
    """Run async coroutine from sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        # Dispose asyncpg connection pool before closing the loop to prevent
        # "attached to a different loop" errors on subsequent tasks.
        from app.database import engine
        try:
            loop.run_until_complete(engine.dispose())
        except Exception:
            pass
        loop.close()
        asyncio.set_event_loop(None)


async def _execute_source_fetch(source_name: str, county: str, state: str, zip_code: str | None = None):
    from app.database import AsyncSessionLocal
    from app.models.property import Property, MarketStatus
    from app.models.indicator import PropertyIndicator
    from app.models.data_source import DataSourceConfig, DataSourceRun
    from sqlalchemy import select, update

    source_class = get_source_class(source_name)
    if not source_class:
        return

    async with AsyncSessionLocal() as db:
        # Get config / API key
        cfg_result = await db.execute(
            select(DataSourceConfig).where(DataSourceConfig.source_name == source_name)
        )
        config = cfg_result.scalar_one_or_none()

        if config and not config.enabled:
            logger.info(f"Source {source_name} is disabled, skipping.")
            return

        api_key = config.api_key_encrypted if config else None
        source_config = dict(config.config_json) if config and config.config_json else {}
        if zip_code:
            source_config["zip_code"] = zip_code
        source = source_class(api_key=api_key, config=source_config)

        if not source.is_configured():
            logger.warning(f"Source {source_name} not configured, skipping.")
            return

        # Create run record
        run = DataSourceRun(
            source_name=source_name,
            location=f"{county}, {state}",
            status="running",
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        try:
            result = await source.fetch(county, state)

            created = 0
            updated = 0

            # Upsert properties
            for raw_prop in result.properties:
                key_val = raw_prop.parcel_id or raw_prop.address

                # Look up existing property
                existing_q = await db.execute(
                    select(Property).where(
                        (Property.parcel_id == raw_prop.parcel_id) if raw_prop.parcel_id
                        else (Property.address == raw_prop.address)
                    )
                )
                prop = existing_q.scalar_one_or_none()

                if not prop:
                    prop = Property(
                        address=raw_prop.address,
                        city=raw_prop.city,
                        state=raw_prop.state,
                        zip_code=raw_prop.zip_code,
                        county=raw_prop.county,
                        parcel_id=raw_prop.parcel_id,
                        data_sources=source_name,
                    )
                    db.add(prop)
                    created += 1
                else:
                    # Merge source name
                    sources = set((prop.data_sources or "").split(","))
                    sources.add(source_name)
                    prop.data_sources = ",".join(filter(None, sources))
                    updated += 1

                # Update fields from raw record
                if raw_prop.owner_name:
                    prop.owner_name = raw_prop.owner_name
                if raw_prop.owner_mailing_address:
                    prop.owner_mailing_address = raw_prop.owner_mailing_address
                if raw_prop.assessed_value:
                    prop.assessed_value = raw_prop.assessed_value
                if raw_prop.last_sale_price:
                    prop.last_sale_price = raw_prop.last_sale_price
                if raw_prop.latitude:
                    prop.latitude = raw_prop.latitude
                if raw_prop.longitude:
                    prop.longitude = raw_prop.longitude

                # Extra fields from Zillow/MLS
                extra = raw_prop.extra or {}
                if extra.get("market_status"):
                    prop.market_status = MarketStatus(extra["market_status"])
                if extra.get("list_price"):
                    prop.list_price = extra["list_price"]
                if extra.get("days_on_market"):
                    prop.days_on_market = extra["days_on_market"]
                if extra.get("price_reductions") is not None:
                    prop.price_reductions = extra["price_reductions"]
                if extra.get("mls_id"):
                    prop.mls_id = extra["mls_id"]
                if extra.get("zillow_url"):
                    prop.zillow_url = extra["zillow_url"]
                if extra.get("owner_phone"):
                    prop.owner_phone = extra["owner_phone"]
                if extra.get("owner_email"):
                    prop.owner_email = extra["owner_email"]

                await db.flush()

                # Write indicators
                prop_key = raw_prop.parcel_id or raw_prop.address
                for indicator in result.indicators.get(prop_key, []):
                    from datetime import timedelta
                    expires = None
                    if indicator.expires_days:
                        expires = datetime.now(timezone.utc) + timedelta(days=indicator.expires_days)

                    db.add(PropertyIndicator(
                        property_id=prop.id,
                        indicator_type=indicator.indicator_type,
                        category=INDICATOR_CATEGORIES[indicator.indicator_type],
                        confidence=indicator.confidence,
                        source_name=indicator.source_name or source_name,
                        notes=indicator.notes,
                        raw_data=indicator.raw_data,
                        expires_at=expires,
                    ))

            await db.commit()

            # Update run record
            run.status = "success"
            run.records_fetched = result.records_fetched
            run.records_created = created
            run.records_updated = updated
            run.finished_at = datetime.now(timezone.utc)

            if config:
                config.last_run_at = datetime.now(timezone.utc)

            await db.commit()

            # Trigger score recalculation and geocoding
            from app.tasks.recalculate_scores import recalculate_all_scores
            from app.tasks.geocode_properties import geocode_properties
            recalculate_all_scores.delay()
            if created > 0:
                geocode_properties.delay()

        except Exception as e:
            logger.error(f"Source {source_name} failed: {e}", exc_info=True)
            run.status = "failed"
            run.error_message = str(e)
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()


@celery_app.task(name="app.tasks.refresh_data.run_data_source_task")
def run_data_source_task(source_name: str, county: str, state: str, zip_code: str | None = None):
    _run_async(_execute_source_fetch(source_name, county, state, zip_code))


@celery_app.task(name="app.tasks.refresh_data.refresh_all_sources")
def refresh_all_sources():
    """Nightly task: refresh all enabled sources for the target counties."""
    target_counties = [
        ("Allegheny", "PA"),
        ("Westmoreland", "PA"),
    ]
    for county, state in target_counties:
        for source_class in ALL_SOURCES:
            run_data_source_task.delay(source_class.name, county, state)

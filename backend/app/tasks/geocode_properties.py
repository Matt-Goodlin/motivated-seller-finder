"""
Celery task to batch-geocode properties that are missing lat/lng.
Uses the US Census Geocoder API (free, no key needed, ~1000 addresses per request).
"""
import asyncio
import csv
import io
import logging
import httpx

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

CENSUS_BATCH_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"
BATCH_SIZE = 500  # Census allows up to 1000; 500 is safer for timeouts


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        from app.database import engine
        try:
            loop.run_until_complete(engine.dispose())
        except Exception:
            pass
        loop.close()
        asyncio.set_event_loop(None)


async def _geocode_batch(rows: list[tuple]) -> dict[str, tuple[float, float]]:
    """Submit a batch to Census geocoder. rows = [(id, street, city, state, zip), ...]"""
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(row)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                CENSUS_BATCH_URL,
                data={"benchmark": "Public_AR_Current", "vintage": "Current_Current"},
                files={"addressFile": ("addresses.csv", buf.getvalue(), "text/csv")},
            )
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning(f"Census geocoder error: {e}")
        return {}

    # Response columns (all quoted CSV):
    # 0: ID, 1: Input address, 2: Match ("Match"/"No_Match"), 3: Match type,
    # 4: Matched address, 5: Coordinates as "lng,lat", 6: Tiger ID, 7: Side
    results: dict[str, tuple[float, float]] = {}
    reader = csv.reader(resp.text.splitlines())
    for parts in reader:
        if len(parts) < 6 or parts[2].strip().lower() != "match":
            continue
        try:
            prop_id = parts[0].strip()
            lng_lat = parts[5].strip()
            lng_str, lat_str = lng_lat.split(",")
            lat = float(lat_str.strip())
            lng = float(lng_str.strip())
            results[prop_id] = (lat, lng)
        except (ValueError, IndexError):
            continue
    return results


async def _run_geocoding():
    from app.database import AsyncSessionLocal
    from app.models.property import Property
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Property)
            .where(Property.latitude.is_(None))
            .where(Property.address.isnot(None))
            .order_by(Property.id)
            .limit(5000)
        )
        props = result.scalars().all()

    if not props:
        logger.info("No properties need geocoding.")
        return

    logger.info(f"Geocoding {len(props)} properties...")
    total_geocoded = 0

    for i in range(0, len(props), BATCH_SIZE):
        batch = props[i:i + BATCH_SIZE]
        rows = [
            (str(p.id), p.address or "", p.city or "", p.state or "PA", p.zip_code or "")
            for p in batch
        ]
        geo_results = await _geocode_batch(rows)

        if not geo_results:
            continue

        async with AsyncSessionLocal() as db:
            for p in batch:
                coords = geo_results.get(str(p.id))
                if coords:
                    prop = await db.get(Property, p.id)
                    if prop:
                        prop.latitude, prop.longitude = coords
                        total_geocoded += 1
            await db.commit()

        logger.info(f"  Geocoded {total_geocoded} so far (batch {i // BATCH_SIZE + 1})")

    logger.info(f"Geocoding complete: {total_geocoded} properties updated.")


@celery_app.task(name="app.tasks.geocode_properties.geocode_properties")
def geocode_properties():
    _run_async(_run_geocoding())

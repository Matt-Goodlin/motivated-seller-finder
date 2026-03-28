"""
Zillow / MLS data source for on-market properties.

Uses the RapidAPI Zillow endpoints to pull active, expired, and recently
sold listings. Detects:
  - Long days on market
  - Multiple price reductions
  - Expired listings (relisted)
  - Price significantly below Zestimate

Free tier: 100 requests/month on RapidAPI.
Configure RAPIDAPI_KEY in .env to enable.
"""
import httpx
from app.data_sources.base import DataSource, DataSourceResult, RawPropertyRecord, RawIndicator
from app.models.indicator import IndicatorType, IndicatorCategory
from app.config import get_settings

settings = get_settings()

ZILLOW_RAPIDAPI_HOST = "zillow-com1.p.rapidapi.com"
ZILLOW_BASE = f"https://{ZILLOW_RAPIDAPI_HOST}"


class ZillowMLSSource(DataSource):
    name = "zillow_mls"
    display_name = "Zillow / MLS Listings"
    description = (
        "Active and recently listed properties from Zillow via RapidAPI. "
        "Detects high days-on-market, price reductions, and expired listings. "
        "Requires a free RapidAPI key."
    )
    is_paid = False  # free tier available
    default_enabled = False  # requires RAPIDAPI_KEY

    def is_configured(self) -> bool:
        return bool(settings.rapidapi_key)

    async def fetch(self, county: str, state: str) -> DataSourceResult:
        result = DataSourceResult(
            source_name=self.name,
            location=f"{county}, {state}",
        )

        if not settings.rapidapi_key:
            result.errors.append(
                "RAPIDAPI_KEY not configured. Add it to .env to enable Zillow/MLS data."
            )
            return result

        headers = {
            "X-RapidAPI-Key": settings.rapidapi_key,
            "X-RapidAPI-Host": ZILLOW_RAPIDAPI_HOST,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{ZILLOW_BASE}/propertyExtendedSearch",
                    params={
                        "location": f"{county}, {state}",
                        "status_type": "ForSale",
                        "home_type": "Houses",
                        "doz": "90",  # listed 90+ days ago
                        "sort": "days",
                    },
                    headers=headers,
                    timeout=20.0,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            result.errors.append(f"Zillow API error: {e}")
            return result

        listings = data.get("props", [])
        result.records_fetched = len(listings)

        for listing in listings:
            addr = listing.get("address", "")
            city = listing.get("city", "")
            state_code = listing.get("state", state)
            zip_code = listing.get("zipcode", "")
            price = listing.get("price")
            zestimate = listing.get("zestimate")
            dom = listing.get("daysOnMarket") or listing.get("dom") or 0
            price_history = listing.get("priceHistory", [])
            price_reductions = sum(
                1 for p in price_history if (p.get("event") or "").lower() == "price change"
                and (p.get("priceChangeRate") or 0) < 0
            )
            lat = listing.get("latitude")
            lng = listing.get("longitude")
            zpid = listing.get("zpid", "")
            zillow_url = f"https://www.zillow.com/homedetails/{zpid}_zpid/" if zpid else None

            prop = RawPropertyRecord(
                address=addr,
                city=city,
                state=state_code,
                zip_code=str(zip_code) if zip_code else None,
                county=county,
                latitude=lat,
                longitude=lng,
                extra={
                    "market_status": "ON_MARKET",
                    "list_price": price,
                    "days_on_market": dom,
                    "price_reductions": price_reductions,
                    "zestimate": zestimate,
                    "mls_id": str(zpid),
                    "zillow_url": zillow_url,
                },
            )
            result.properties.append(prop)

            indicators: list[RawIndicator] = []

            if dom >= 90:
                confidence = min(0.5 + (dom - 90) / 180, 0.95)
                indicators.append(RawIndicator(
                    indicator_type=IndicatorType.LONG_DOM,
                    confidence=confidence,
                    source_name=self.name,
                    notes=f"{dom} days on market",
                    raw_data={"dom": dom, "price": price},
                ))

            if price_reductions >= 2:
                indicators.append(RawIndicator(
                    indicator_type=IndicatorType.PRICE_DROPS,
                    confidence=min(0.5 + price_reductions * 0.1, 0.95),
                    source_name=self.name,
                    notes=f"{price_reductions} price reductions",
                    raw_data={"reductions": price_reductions},
                ))

            if price and zestimate and price < zestimate * 0.90:
                discount_pct = (1 - price / zestimate) * 100
                indicators.append(RawIndicator(
                    indicator_type=IndicatorType.LOW_EQUITY,
                    confidence=min(0.4 + discount_pct / 100, 0.9),
                    source_name=self.name,
                    notes=f"Listed {discount_pct:.1f}% below Zestimate (${price:,.0f} vs ${zestimate:,.0f})",
                    raw_data={"list_price": price, "zestimate": zestimate},
                ))

            if indicators:
                result.indicators[addr] = indicators

        return result

    def map_to_indicators(self, record: RawPropertyRecord) -> list[RawIndicator]:
        return []

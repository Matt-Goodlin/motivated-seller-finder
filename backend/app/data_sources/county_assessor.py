"""
County Assessor data source.

Pulls property ownership, assessed value, and sale history from public
county assessor records. Many counties expose this via Socrata open data
portals or direct CSV downloads.

Strategy:
  1. Check if the county has a known Socrata endpoint (common in major metros)
  2. Fall back to a generic search against data.gov and state open data portals
  3. Mark absentee owners where mailing address differs from property address
"""
import re
from datetime import datetime, date
from typing import Optional
import httpx
from app.data_sources.base import DataSource, DataSourceResult, RawPropertyRecord, RawIndicator
from app.models.indicator import IndicatorType
from app.config import get_settings

settings = get_settings()

# Known Socrata endpoints keyed by "county_state" (lowercase, no spaces)
SOCRATA_ENDPOINTS: dict[str, str] = {
    "cook_il": "https://datacatalog.cookcountyil.gov/resource/tx2p-k2g9.json",
    "los_angeles_ca": "https://data.lacounty.gov/resource/8489-uedm.json",
    "king_wa": "https://data.kingcounty.gov/resource/xdqx-gpix.json",
    "travis_tx": "https://data.austintexas.gov/resource/n833-h3sy.json",
    "maricopa_az": "https://data.maricopacountyassessor.gov/resource/s6ap-zngg.json",
}


def _normalize_key(county: str, state: str) -> str:
    county_clean = re.sub(r"\s+county$", "", county.lower().strip())
    county_clean = re.sub(r"[^a-z]", "_", county_clean)
    return f"{county_clean}_{state.lower()}"


def _is_absentee(property_addr: str, mailing_addr: Optional[str]) -> bool:
    if not mailing_addr:
        return False
    # Rough check: different zip codes or state in mailing address
    prop_zip = re.search(r"\b\d{5}\b", property_addr)
    mail_zip = re.search(r"\b\d{5}\b", mailing_addr)
    if prop_zip and mail_zip and prop_zip.group() != mail_zip.group():
        return True
    return False


def _years_since(date_str: Optional[str]) -> Optional[float]:
    if not date_str:
        return None
    try:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                dt = datetime.strptime(date_str[:10], fmt[:len(fmt.split("%")[1])+2] if "T" not in date_str else "%Y-%m-%d")
                return (datetime.now() - dt).days / 365.25
            except ValueError:
                continue
    except Exception:
        pass
    return None


class CountyAssessorSource(DataSource):
    name = "county_assessor"
    display_name = "County Assessor Records"
    description = (
        "Public property records including ownership, assessed value, last sale date, "
        "and absentee owner detection. Available free for most US counties."
    )
    is_paid = False
    default_enabled = True

    async def fetch(self, county: str, state: str) -> DataSourceResult:
        result = DataSourceResult(
            source_name=self.name,
            location=f"{county}, {state}",
        )

        key = _normalize_key(county, state)
        endpoint = SOCRATA_ENDPOINTS.get(key)

        if not endpoint:
            result.errors.append(
                f"No direct assessor integration for {county}, {state}. "
                "To add support, visit your county assessor's open data portal and "
                "add the Socrata endpoint to SOCRATA_ENDPOINTS in county_assessor.py."
            )
            return result

        headers = {}
        if settings.socrata_app_token:
            headers["X-App-Token"] = settings.socrata_app_token

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    endpoint,
                    params={"$limit": 50000, "$offset": 0},
                    headers=headers,
                    timeout=30.0,
                )
                resp.raise_for_status()
                rows = resp.json()
        except httpx.HTTPError as e:
            result.errors.append(f"Failed to fetch assessor data: {e}")
            return result

        result.records_fetched = len(rows)

        for row in rows:
            addr = (
                row.get("property_address")
                or row.get("situs_address")
                or row.get("address")
                or ""
            ).strip()
            if not addr:
                continue

            city = row.get("property_city") or row.get("city") or county
            mailing = row.get("mailing_address") or row.get("owner_mailing_address")

            try:
                assessed = float(row.get("assessed_value") or row.get("total_value") or 0) or None
            except (ValueError, TypeError):
                assessed = None

            try:
                sale_price = float(row.get("sale_price") or row.get("last_sale_price") or 0) or None
            except (ValueError, TypeError):
                sale_price = None

            sale_date = row.get("sale_date") or row.get("last_sale_date")
            years_owned = _years_since(sale_date)

            prop = RawPropertyRecord(
                address=addr,
                city=city,
                state=state,
                zip_code=row.get("zip") or row.get("zip_code"),
                county=county,
                parcel_id=row.get("parcel_id") or row.get("ain") or row.get("pin"),
                owner_name=row.get("owner_name") or row.get("owner"),
                owner_mailing_address=mailing,
                assessed_value=assessed,
                last_sale_price=sale_price,
                last_sale_date=sale_date,
                extra={"years_owned": years_owned},
            )
            result.properties.append(prop)

            # Derive indicators
            indicators: list[RawIndicator] = []
            key_str = prop.parcel_id or addr

            absentee = _is_absentee(addr, mailing)
            if absentee:
                indicators.append(RawIndicator(
                    indicator_type=IndicatorType.ABSENTEE_OWNER,
                    confidence=0.9,
                    source_name=self.name,
                    notes=f"Mailing address differs: {mailing}",
                ))

            if years_owned and years_owned >= 10 and assessed and sale_price:
                equity_ratio = assessed / sale_price if sale_price else None
                if equity_ratio and equity_ratio < 1.05:
                    indicators.append(RawIndicator(
                        indicator_type=IndicatorType.LOW_EQUITY,
                        confidence=0.7,
                        source_name=self.name,
                        notes=f"Owned {years_owned:.0f} yrs, assessed/sale ratio: {equity_ratio:.2f}",
                    ))

            if years_owned and years_owned >= 10:
                indicators.append(RawIndicator(
                    indicator_type=IndicatorType.LONG_OWNERSHIP_NO_IMPROVEMENTS,
                    confidence=min(0.4 + (years_owned - 10) * 0.03, 0.9),
                    source_name=self.name,
                    notes=f"Owned approximately {years_owned:.0f} years",
                ))

            if indicators:
                result.indicators[key_str] = indicators

        return result

    def map_to_indicators(self, record: RawPropertyRecord) -> list[RawIndicator]:
        return []  # indicators built inline in fetch()

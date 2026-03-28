"""
County Assessor data source.

Pulls property ownership, assessed value, sale history, and property details
from public county assessor records.

Supports:
  - WPRDC/CKAN API (Allegheny County, PA) — uses CKAN datastore search
  - Socrata API — most other major counties

Pass zip_code in config to filter results to a specific zip code area.
"""
import re
import json
from datetime import datetime
from typing import Optional
import httpx
from app.data_sources.base import DataSource, DataSourceResult, RawPropertyRecord, RawIndicator
from app.models.indicator import IndicatorType
from app.config import get_settings

settings = get_settings()

# CKAN-based endpoints (WPRDC and similar) — use different query format
CKAN_ENDPOINTS: dict[str, dict] = {
    "allegheny_pa": {
        "url": "https://data.wprdc.org/api/3/action/datastore_search",
        "resource_id": "9a1c60bd-f9f7-4aba-aeb7-af8c3aaa44e5",
        "zip_field": "PROPERTYZIP",
    },
}

# Socrata endpoints for other counties
SOCRATA_ENDPOINTS: dict[str, str] = {
    "cook_il":      "https://datacatalog.cookcountyil.gov/resource/tx2p-k2g9.json",
    "los_angeles_ca": "https://data.lacounty.gov/resource/8489-uedm.json",
    "king_wa":      "https://data.kingcounty.gov/resource/xdqx-gpix.json",
    "travis_tx":    "https://data.austintexas.gov/resource/n833-h3sy.json",
    "maricopa_az":  "https://data.maricopacountyassessor.gov/resource/s6ap-zngg.json",
}


def _normalize_key(county: str, state: str) -> str:
    county_clean = re.sub(r"\s+county$", "", county.lower().strip())
    county_clean = re.sub(r"[^a-z]", "_", county_clean)
    return f"{county_clean}_{state.lower()}"


def _years_since(date_str: Optional[str]) -> Optional[float]:
    if not date_str:
        return None
    for fmt in ("%m-%d-%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(date_str[:10], fmt)
            return (datetime.now() - dt).days / 365.25
        except ValueError:
            continue
    return None


def _safe_float(val) -> Optional[float]:
    try:
        v = float(val or 0)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> Optional[int]:
    try:
        v = int(val or 0)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


class CountyAssessorSource(DataSource):
    name = "county_assessor"
    display_name = "County Assessor Records"
    description = (
        "Public property records including ownership, assessed value, sale history, "
        "bedrooms/baths, year built, and absentee owner detection. "
        "Supported: Allegheny County PA, Cook IL, LA County CA, King WA, Travis TX, Maricopa AZ."
    )
    is_paid = False
    default_enabled = True

    async def fetch(self, county: str, state: str) -> DataSourceResult:
        result = DataSourceResult(source_name=self.name, location=f"{county}, {state}")
        key = _normalize_key(county, state)
        zip_code = self.config.get("zip_code")

        if key in CKAN_ENDPOINTS:
            return await self._fetch_ckan(key, county, state, zip_code, result)
        elif key in SOCRATA_ENDPOINTS:
            return await self._fetch_socrata(key, county, state, zip_code, result)
        else:
            all_supported = list(CKAN_ENDPOINTS.keys()) + list(SOCRATA_ENDPOINTS.keys())
            result.errors.append(
                f"No assessor integration for {county}, {state}. "
                f"Supported: {', '.join(all_supported)}."
            )
            return result

    async def _fetch_ckan(self, key: str, county: str, state: str,
                          zip_code: Optional[str], result: DataSourceResult) -> DataSourceResult:
        """Fetch from WPRDC/CKAN-style datastore API."""
        cfg = CKAN_ENDPOINTS[key]
        limit = 5000
        offset = 0
        all_records = []

        filters = {}
        if zip_code:
            filters[cfg["zip_field"]] = int(zip_code) if zip_code.isdigit() else zip_code

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                while True:
                    params: dict = {
                        "resource_id": cfg["resource_id"],
                        "limit": limit,
                        "offset": offset,
                    }
                    if filters:
                        params["filters"] = json.dumps(filters)

                    resp = await client.get(cfg["url"], params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    records = data.get("result", {}).get("records", [])
                    all_records.extend(records)

                    total = data.get("result", {}).get("total", 0)
                    offset += limit
                    if offset >= total or not records:
                        break
        except httpx.HTTPError as e:
            result.errors.append(f"CKAN fetch error: {e}")
            return result

        result.records_fetched = len(all_records)

        for row in all_records:
            house_num = str(row.get("PROPERTYHOUSENUM") or "").strip()
            street = str(row.get("PROPERTYADDRESS") or "").strip()
            addr = f"{house_num} {street}".strip() if house_num else street
            if not addr:
                continue

            city = str(row.get("PROPERTYCITY") or county).strip().title()
            prop_zip = str(row.get("PROPERTYZIP") or "").strip()
            parcel_id = str(row.get("PARID") or "").strip()

            # Owner / mailing
            owner = str(row.get("CHANGENOTICEADDRESS1") or "").strip()
            mail_addr2 = str(row.get("CHANGENOTICEADDRESS2") or "").strip()
            mail_city_state = str(row.get("CHANGENOTICEADDRESS3") or "").strip()
            mail_zip = str(row.get("CHANGENOTICEADDRESS4") or "").strip()
            mailing = " ".join(filter(None, [owner, mail_addr2, mail_city_state, mail_zip])).strip()

            # Financials
            assessed = _safe_float((row.get("COUNTYTOTAL") or 0))
            fair_market = _safe_float(row.get("FAIRMARKETTOTAL"))
            sale_price = _safe_float(row.get("SALEPRICE"))
            sale_date = str(row.get("SALEDATE") or "").strip() or None
            years_owned = _years_since(sale_date)

            prop = RawPropertyRecord(
                address=addr,
                city=city,
                state=state,
                zip_code=prop_zip or zip_code,
                county=county,
                parcel_id=parcel_id,
                owner_name=owner or None,
                owner_mailing_address=mailing or None,
                assessed_value=assessed,
                last_sale_price=sale_price,
                last_sale_date=sale_date,
                extra={
                    "years_owned": years_owned,
                    "market_value_estimate": fair_market,
                    "year_built": _safe_int(row.get("YEARBLT")),
                    "sq_ft": _safe_int(row.get("FINISHEDLIVINGAREA")),
                    "bedrooms": _safe_int(row.get("BEDROOMS")),
                    "bathrooms": (_safe_float(row.get("FULLBATHS")) or 0) + ((_safe_float(row.get("HALFBATHS")) or 0) * 0.5) or None,
                    "property_type": str(row.get("USEDESC") or "").strip().title() or None,
                    "lot_size_sqft": _safe_int(row.get("LOTAREA")),
                },
            )
            result.properties.append(prop)

            # Indicators
            indicators: list[RawIndicator] = []
            ind_key = parcel_id or addr

            # Absentee owner: mailing zip differs from property zip
            if mail_zip.strip() and prop_zip.strip() and mail_zip.strip() != prop_zip.strip():
                indicators.append(RawIndicator(
                    indicator_type=IndicatorType.ABSENTEE_OWNER,
                    confidence=0.9,
                    source_name=self.name,
                    notes=f"Owner mail zip {mail_zip} ≠ property zip {prop_zip}",
                ))

            if years_owned and years_owned >= 10:
                conf = min(0.4 + (years_owned - 10) * 0.03, 0.9)
                indicators.append(RawIndicator(
                    indicator_type=IndicatorType.LONG_OWNERSHIP_NO_IMPROVEMENTS,
                    confidence=conf,
                    source_name=self.name,
                    notes=f"Owned ~{years_owned:.0f} years (sold {sale_date})",
                ))

            if years_owned and years_owned >= 10 and assessed and sale_price and sale_price > 0:
                if assessed / sale_price < 1.1:
                    indicators.append(RawIndicator(
                        indicator_type=IndicatorType.LOW_EQUITY,
                        confidence=0.65,
                        source_name=self.name,
                        notes=f"Assessed ${assessed:,.0f} vs sale ${sale_price:,.0f} — possible low equity",
                    ))

            if indicators:
                result.indicators[ind_key] = indicators

        return result

    async def _fetch_socrata(self, key: str, county: str, state: str,
                             zip_code: Optional[str], result: DataSourceResult) -> DataSourceResult:
        """Fetch from standard Socrata JSON API."""
        endpoint = SOCRATA_ENDPOINTS[key]
        headers = {}
        if settings.socrata_app_token:
            headers["X-App-Token"] = settings.socrata_app_token

        params: dict = {"$limit": 5000}
        if zip_code:
            params["$where"] = f"zip_code = '{zip_code}' OR zip = '{zip_code}'"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(endpoint, params=params, headers=headers)
                resp.raise_for_status()
                rows = resp.json()
        except httpx.HTTPError as e:
            result.errors.append(f"Socrata fetch error: {e}")
            return result

        result.records_fetched = len(rows)

        for row in rows:
            addr = (row.get("property_address") or row.get("situs_address") or row.get("address") or "").strip()
            if not addr:
                continue

            city = row.get("property_city") or row.get("city") or county
            prop_zip = row.get("zip") or row.get("zip_code")
            mailing = row.get("mailing_address") or row.get("owner_mailing_address")
            sale_date = row.get("sale_date") or row.get("last_sale_date")
            years_owned = _years_since(sale_date)
            assessed = _safe_float(row.get("assessed_value") or row.get("total_value"))
            sale_price = _safe_float(row.get("sale_price") or row.get("last_sale_price"))

            mail_zip = re.search(r"\b(\d{5})\b", mailing or "")
            mail_zip_str = mail_zip.group(1) if mail_zip else None

            prop = RawPropertyRecord(
                address=addr, city=city, state=state,
                zip_code=str(prop_zip) if prop_zip else None, county=county,
                parcel_id=row.get("parcel_id") or row.get("ain") or row.get("pin"),
                owner_name=row.get("owner_name") or row.get("owner"),
                owner_mailing_address=mailing,
                assessed_value=assessed, last_sale_price=sale_price, last_sale_date=sale_date,
                extra={"years_owned": years_owned},
            )
            result.properties.append(prop)

            indicators: list[RawIndicator] = []
            ind_key = prop.parcel_id or addr
            if prop_zip and mail_zip_str and str(prop_zip)[:5] != mail_zip_str:
                indicators.append(RawIndicator(indicator_type=IndicatorType.ABSENTEE_OWNER, confidence=0.9, source_name=self.name, notes=f"Mailing: {mailing}"))
            if years_owned and years_owned >= 10:
                indicators.append(RawIndicator(indicator_type=IndicatorType.LONG_OWNERSHIP_NO_IMPROVEMENTS, confidence=min(0.4 + (years_owned - 10) * 0.03, 0.9), source_name=self.name, notes=f"Owned ~{years_owned:.0f} yrs"))
            if years_owned and years_owned >= 10 and assessed and sale_price and sale_price > 0 and assessed / sale_price < 1.1:
                indicators.append(RawIndicator(indicator_type=IndicatorType.LOW_EQUITY, confidence=0.65, source_name=self.name, notes=f"Assessed ${assessed:,.0f} vs sale ${sale_price:,.0f}"))
            if indicators:
                result.indicators[ind_key] = indicators

        return result

    def map_to_indicators(self, record: RawPropertyRecord) -> list[RawIndicator]:
        return []

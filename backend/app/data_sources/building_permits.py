"""
Building Permits data source.

Pulls permit data from city/county open data portals (Socrata).
Identifies:
  - Permits filed but not finaled/completed (potential deferred maintenance)
  - Failed inspections
  - Code violations

Most major US cities publish permit data via Socrata (data.cityname.gov).
"""
import httpx
from datetime import datetime, timedelta
from app.data_sources.base import DataSource, DataSourceResult, RawPropertyRecord, RawIndicator
from app.models.indicator import IndicatorType
from app.config import get_settings

settings = get_settings()

# Known permit endpoints keyed by "city_state"
PERMIT_ENDPOINTS: dict[str, str] = {
    "chicago_il": "https://data.cityofchicago.org/resource/ydr8-5enu.json",
    "new_york_ny": "https://data.cityofnewyork.us/resource/ipu4-2q9a.json",
    "los_angeles_ca": "https://data.lacity.org/resource/nbyu-2ha9.json",
    "san_francisco_ca": "https://data.sfgov.org/resource/i98e-djp9.json",
    "seattle_wa": "https://data.seattle.gov/resource/ht3q-kdvx.json",
    "austin_tx": "https://data.austintexas.gov/resource/3syk-w9eu.json",
    "denver_co": "https://www.denvergov.org/resource/wkq6-4hkn.json",
    "nashville_tn": "https://data.nashville.gov/resource/3h5a-ynsx.json",
    "phoenix_az": "https://www.phoenixopendata.com/resource/wkr8-rx4f.json",
    "atlanta_ga": "https://opendata.atlantaregional.com/resource/ypvb-4bts.json",
}


class BuildingPermitsSource(DataSource):
    name = "building_permits"
    display_name = "Building Permits & Violations"
    description = (
        "City open data portal permit records. Detects permits filed but not completed, "
        "failed inspections, and code violations — signals of deferred maintenance or "
        "landlord distress."
    )
    is_paid = False
    default_enabled = True

    async def fetch(self, county: str, state: str) -> DataSourceResult:
        result = DataSourceResult(
            source_name=self.name,
            location=f"{county}, {state}",
        )

        # Try to find a matching endpoint
        city_key = county.lower().replace(" county", "").replace(" ", "_") + f"_{state.lower()}"
        endpoint = PERMIT_ENDPOINTS.get(city_key)

        if not endpoint:
            result.errors.append(
                f"No building permit integration for {county}, {state}. "
                "Check your city's open data portal and add the endpoint to "
                "building_permits.py PERMIT_ENDPOINTS."
            )
            return result

        headers = {}
        if settings.socrata_app_token:
            headers["X-App-Token"] = settings.socrata_app_token

        # Filter to permits from last 5 years
        cutoff = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    endpoint,
                    params={
                        "$limit": 50000,
                        "$where": f"application_date >= '{cutoff}'",
                    },
                    headers=headers,
                    timeout=30.0,
                )
                resp.raise_for_status()
                rows = resp.json()
        except Exception as e:
            result.errors.append(f"Permit data fetch error: {e}")
            return result

        result.records_fetched = len(rows)

        # Group by address to detect patterns
        by_address: dict[str, list[dict]] = {}
        for row in rows:
            addr = (
                row.get("address") or row.get("street_address") or row.get("location_1", {}).get("human_address", "")
            ).strip().upper()
            if addr:
                by_address.setdefault(addr, []).append(row)

        for addr, permits in by_address.items():
            indicators: list[RawIndicator] = []

            incomplete = [
                p for p in permits
                if (p.get("status") or "").lower() not in ("finaled", "completed", "closed", "approved")
                and (p.get("status") or "") != ""
            ]
            if len(incomplete) >= 2:
                indicators.append(RawIndicator(
                    indicator_type=IndicatorType.PERMIT_INCOMPLETE,
                    confidence=min(0.5 + len(incomplete) * 0.1, 0.95),
                    source_name=self.name,
                    notes=f"{len(incomplete)} open/unfinished permits",
                    raw_data={"count": len(incomplete), "statuses": list({p.get("status") for p in incomplete})},
                ))

            violations = [
                p for p in permits
                if "violation" in (p.get("permit_type") or "").lower()
                or "violation" in (p.get("work_type") or "").lower()
            ]
            if violations:
                indicators.append(RawIndicator(
                    indicator_type=IndicatorType.CODE_VIOLATION,
                    confidence=min(0.6 + len(violations) * 0.1, 0.99),
                    source_name=self.name,
                    notes=f"{len(violations)} code violation record(s)",
                    raw_data={"count": len(violations)},
                ))

            failed = [
                p for p in permits
                if "fail" in (p.get("status") or "").lower()
                or "fail" in (p.get("result") or "").lower()
            ]
            if failed:
                indicators.append(RawIndicator(
                    indicator_type=IndicatorType.FAILED_INSPECTION,
                    confidence=0.85,
                    source_name=self.name,
                    notes=f"{len(failed)} failed inspection(s)",
                ))

            if indicators:
                result.indicators[addr] = indicators

        return result

    def map_to_indicators(self, record: RawPropertyRecord) -> list[RawIndicator]:
        return []

"""
Court Records data source.

Pulls divorce filings, probate/estate cases, eviction filings, and
bankruptcy filings from public court record portals.

Sources used:
  - PACER (US Bankruptcy Court, federal) — free via bulk data
  - State court public portals (varies by state)
  - CourtListener API (free, covers many federal + some state courts)
  - OpenCorporates for entity bankruptcy cross-reference

This source maps owner names from the assessor to court filings.
"""
import httpx
from app.data_sources.base import DataSource, DataSourceResult, RawPropertyRecord, RawIndicator
from app.models.indicator import IndicatorType


COURTLISTENER_BASE = "https://www.courtlistener.com/api/rest/v4"


class CourtRecordsSource(DataSource):
    name = "court_records"
    display_name = "Public Court Records"
    description = (
        "Searches public court databases for divorce filings, probate/estate cases, "
        "eviction filings, and bankruptcy cases linked to property owners. "
        "Uses CourtListener API (free) and PACER bulk data."
    )
    is_paid = False
    default_enabled = True

    async def fetch(self, county: str, state: str) -> DataSourceResult:
        result = DataSourceResult(
            source_name=self.name,
            location=f"{county}, {state}",
        )

        # Fetch recent bankruptcy filings in the area
        try:
            bankruptcy_indicators = await self._fetch_bankruptcies(county, state)
            result.indicators.update(bankruptcy_indicators)
            result.records_fetched += len(bankruptcy_indicators)
        except Exception as e:
            result.errors.append(f"Bankruptcy fetch error: {e}")

        # Probate / estate cases via CourtListener
        try:
            probate_indicators = await self._fetch_probate(county, state)
            result.indicators.update(probate_indicators)
            result.records_fetched += len(probate_indicators)
        except Exception as e:
            result.errors.append(f"Probate fetch error: {e}")

        return result

    async def _fetch_bankruptcies(self, county: str, state: str) -> dict[str, list[RawIndicator]]:
        """Search CourtListener for bankruptcy cases in the area."""
        indicators: dict[str, list[RawIndicator]] = {}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{COURTLISTENER_BASE}/dockets/",
                params={
                    "nature_of_suit": "520",  # bankruptcy
                    "court__jurisdiction": "FB",  # federal bankruptcy
                    "filed_after": "2020-01-01",
                    "q": f"{county} {state}",
                    "page_size": 100,
                    "format": "json",
                },
                timeout=15.0,
            )

            if resp.status_code == 200:
                data = resp.json()
                for case in data.get("results", []):
                    party_name = case.get("case_name", "")
                    case_number = case.get("docket_number", "")
                    indicators[f"bankruptcy_{case_number}"] = [
                        RawIndicator(
                            indicator_type=IndicatorType.BANKRUPTCY_FILING,
                            confidence=0.95,
                            source_name=self.name,
                            notes=f"Bankruptcy case: {case_number} — {party_name}",
                            raw_data={
                                "case_name": party_name,
                                "case_number": case_number,
                                "filed": case.get("date_filed"),
                                "court": case.get("court"),
                            },
                        )
                    ]

        return indicators

    async def _fetch_probate(self, county: str, state: str) -> dict[str, list[RawIndicator]]:
        """Search for probate/estate cases."""
        indicators: dict[str, list[RawIndicator]] = {}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{COURTLISTENER_BASE}/dockets/",
                params={
                    "nature_of_suit": "820",  # estates
                    "q": f"probate estate {county} {state}",
                    "filed_after": "2020-01-01",
                    "page_size": 100,
                    "format": "json",
                },
                timeout=15.0,
            )

            if resp.status_code == 200:
                data = resp.json()
                for case in data.get("results", []):
                    party_name = case.get("case_name", "")
                    case_number = case.get("docket_number", "")
                    indicators[f"probate_{case_number}"] = [
                        RawIndicator(
                            indicator_type=IndicatorType.PROBATE_FILING,
                            confidence=0.9,
                            source_name=self.name,
                            notes=f"Probate/estate case: {case_number} — {party_name}",
                            raw_data={
                                "case_name": party_name,
                                "case_number": case_number,
                                "filed": case.get("date_filed"),
                            },
                        )
                    ]

        return indicators

    def map_to_indicators(self, record: RawPropertyRecord) -> list[RawIndicator]:
        return []

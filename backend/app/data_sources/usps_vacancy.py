"""
USPS Vacancy / HUD data source.

Uses HUD's USPS Vacancy datasets (published quarterly) to identify
vacant and no-stat addresses. Data is available at the zip code level.

HUD data portal: https://www.huduser.gov/portal/datasets/usps.html
"""
import httpx
from app.data_sources.base import DataSource, DataSourceResult, RawPropertyRecord, RawIndicator
from app.models.indicator import IndicatorType

HUD_API_BASE = "https://www.huduser.gov/hudapi/public"


class USPSVacancySource(DataSource):
    name = "usps_vacancy"
    display_name = "USPS Vacancy Data (HUD)"
    description = (
        "USPS vacancy and no-stat address data published quarterly by HUD. "
        "Identifies zip codes and addresses with unusually high vacancy rates "
        "or properties flagged as vacant by mail carriers."
    )
    is_paid = False
    default_enabled = True

    async def fetch(self, county: str, state: str) -> DataSourceResult:
        result = DataSourceResult(
            source_name=self.name,
            location=f"{county}, {state}",
        )

        if not self.api_key:
            result.errors.append(
                "HUD API token required for USPS vacancy data. "
                "Register free at https://www.huduser.gov/portal/datasets/usps.html "
                "and add HUD_API_KEY to your .env file."
            )
            return result

        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            # Get vacancy data by zip for the state
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{HUD_API_BASE}/usps",
                    params={
                        "type": "county",
                        "query": state,
                        "year": "2024",
                        "quarter": "4",
                    },
                    headers=headers,
                    timeout=15.0,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            result.errors.append(f"HUD API error: {e}")
            return result

        for row in data.get("data", {}).get("results", []):
            zip_code = row.get("zip")
            vacancy_rate = float(row.get("res_vacp", 0) or 0)

            if vacancy_rate > 0.10:  # >10% vacancy rate in this zip
                result.indicators[f"zip_{zip_code}_vacancy"] = [
                    RawIndicator(
                        indicator_type=IndicatorType.USPS_VACANCY,
                        confidence=min(vacancy_rate * 5, 1.0),
                        source_name=self.name,
                        notes=f"Zip {zip_code}: {vacancy_rate*100:.1f}% residential vacancy rate",
                        raw_data=row,
                    )
                ]
                result.records_fetched += 1

        return result

    def map_to_indicators(self, record: RawPropertyRecord) -> list[RawIndicator]:
        return []

"""
BatchData connector (paid).

Provides pre-foreclosure lists, skip tracing (owner phone/email),
and motivated seller lists.

API docs: https://batchdata.com/api-docs
Configure BATCHDATA_API_KEY in .env.
"""
import httpx
from app.data_sources.base import DataSource, DataSourceResult, RawPropertyRecord, RawIndicator
from app.models.indicator import IndicatorType
from app.config import get_settings

settings = get_settings()

BATCHDATA_BASE = "https://api.batchdata.com/api/v1"


class BatchDataSource(DataSource):
    name = "batchdata"
    display_name = "BatchData — Skip Tracing & Pre-Foreclosure (Paid)"
    description = (
        "Pre-foreclosure lists and owner contact information (phone, email) via skip tracing. "
        "Allows direct outreach to motivated sellers. "
        "Paid API — configure BATCHDATA_API_KEY in .env."
    )
    is_paid = True
    default_enabled = False

    async def fetch(self, county: str, state: str) -> DataSourceResult:
        result = DataSourceResult(
            source_name=self.name,
            location=f"{county}, {state}",
        )

        if not self.api_key:
            result.errors.append("BATCHDATA_API_KEY not configured.")
            return result

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{BATCHDATA_BASE}/property/search",
                    json={
                        "requests": [{
                            "county": county,
                            "state": state,
                            "filters": {
                                "preForeclosure": True,
                                "includeOwnerInfo": True,
                            },
                            "limit": 500,
                        }]
                    },
                    headers=headers,
                    timeout=30.0,
                )
                resp.raise_for_status()
                data = resp.json()

            for prop_data in data.get("results", {}).get("properties", []):
                address = prop_data.get("address", {})
                owner = prop_data.get("owner", {})
                contact = prop_data.get("contact", {})

                addr_str = address.get("street", "")
                city = address.get("city", "")
                state_code = address.get("state", state)
                zip_code = address.get("zip", "")

                prop = RawPropertyRecord(
                    address=addr_str,
                    city=city,
                    state=state_code,
                    zip_code=zip_code,
                    county=county,
                    parcel_id=prop_data.get("apn"),
                    owner_name=f"{owner.get('firstName', '')} {owner.get('lastName', '')}".strip(),
                    extra={
                        "owner_phone": contact.get("phone1"),
                        "owner_email": contact.get("email"),
                    },
                )
                result.properties.append(prop)

                indicators: list[RawIndicator] = [
                    RawIndicator(
                        indicator_type=IndicatorType.PRE_FORECLOSURE,
                        confidence=0.98,
                        source_name=self.name,
                        notes=f"Pre-foreclosure from BatchData. Contact: {contact.get('phone1', 'N/A')}",
                        raw_data={
                            "foreclosure_type": prop_data.get("foreclosureType"),
                            "recording_date": prop_data.get("recordingDate"),
                            "contact": contact,
                        },
                    )
                ]
                result.indicators[addr_str] = indicators
                result.records_fetched += 1

        except Exception as e:
            result.errors.append(f"BatchData API error: {e}")

        return result

    def map_to_indicators(self, record: RawPropertyRecord) -> list[RawIndicator]:
        return []

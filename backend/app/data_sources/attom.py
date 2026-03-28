"""
ATTOM Data Solutions connector (paid).

Provides comprehensive property data including:
  - Pre-foreclosure / NOD filings
  - Tax delinquency
  - AVM (automated valuation model)
  - Owner demographics and equity estimates

API docs: https://api.developer.attomdata.com/docs
Pricing: ~$300+/month. Configure ATTOM_API_KEY in .env.
"""
import httpx
from app.data_sources.base import DataSource, DataSourceResult, RawPropertyRecord, RawIndicator
from app.models.indicator import IndicatorType
from app.config import get_settings

settings = get_settings()

ATTOM_BASE = "https://api.gateway.attomdata.com/propertyapi/v1.0.0"


class ATTOMSource(DataSource):
    name = "attom"
    display_name = "ATTOM Data (Paid)"
    description = (
        "Comprehensive property data including pre-foreclosure, NOD filings, "
        "tax delinquency, equity estimates, and owner demographics. "
        "Paid API — ~$300+/month. Configure ATTOM_API_KEY in .env."
    )
    is_paid = True
    default_enabled = False

    async def fetch(self, county: str, state: str) -> DataSourceResult:
        result = DataSourceResult(
            source_name=self.name,
            location=f"{county}, {state}",
        )

        if not self.api_key:
            result.errors.append("ATTOM_API_KEY not configured.")
            return result

        headers = {
            "apikey": self.api_key,
            "Accept": "application/json",
        }

        try:
            # Pre-foreclosure / NOD search
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{ATTOM_BASE}/foreclosure/search",
                    params={
                        "county": county,
                        "state": state,
                        "recordType": "N",  # Notice of Default
                        "startcutoffdate": "2020-01-01",
                        "pagesize": 500,
                    },
                    headers=headers,
                    timeout=20.0,
                )
                resp.raise_for_status()
                data = resp.json()

            for item in data.get("property", []):
                addr_obj = item.get("address", {})
                addr = addr_obj.get("line1", "")
                city = addr_obj.get("locality", "")
                state_code = addr_obj.get("countrySubd", state)
                zip_code = addr_obj.get("postal1", "")

                prop = RawPropertyRecord(
                    address=addr,
                    city=city,
                    state=state_code,
                    zip_code=zip_code,
                    county=county,
                    parcel_id=item.get("identifier", {}).get("attomId"),
                )
                result.properties.append(prop)

                result.indicators[addr] = [
                    RawIndicator(
                        indicator_type=IndicatorType.PRE_FORECLOSURE,
                        confidence=0.99,
                        source_name=self.name,
                        notes=f"NOD filing from ATTOM: {item.get('foreclosure', {}).get('recordingDate')}",
                        raw_data=item,
                    )
                ]
                result.records_fetched += 1

        except Exception as e:
            result.errors.append(f"ATTOM API error: {e}")

        # Tax delinquency search
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{ATTOM_BASE}/assessment/detail",
                    params={
                        "county": county,
                        "state": state,
                        "taxCodeArea": "*",
                        "pagesize": 500,
                    },
                    headers=headers,
                    timeout=20.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("property", []):
                        tax = item.get("assessment", {}).get("tax", {})
                        if tax.get("taxDelqYr") and int(tax.get("taxDelqYr", 0)) >= 2:
                            addr = item.get("address", {}).get("line1", "")
                            existing = result.indicators.get(addr, [])
                            existing.append(RawIndicator(
                                indicator_type=IndicatorType.TAX_DELINQUENT,
                                confidence=0.97,
                                source_name=self.name,
                                notes=f"Tax delinquent for {tax.get('taxDelqYr')} years",
                                raw_data=tax,
                            ))
                            result.indicators[addr] = existing
        except Exception as e:
            result.errors.append(f"ATTOM tax delinquency error: {e}")

        return result

    def map_to_indicators(self, record: RawPropertyRecord) -> list[RawIndicator]:
        return []

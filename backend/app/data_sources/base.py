"""Abstract base class for all data source connectors."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from app.models.indicator import IndicatorType, IndicatorCategory, INDICATOR_CATEGORIES


@dataclass
class RawPropertyRecord:
    """Normalized property data returned by any data source."""
    address: str
    city: str
    state: str
    zip_code: Optional[str] = None
    county: Optional[str] = None
    parcel_id: Optional[str] = None
    owner_name: Optional[str] = None
    owner_mailing_address: Optional[str] = None
    assessed_value: Optional[float] = None
    last_sale_price: Optional[float] = None
    last_sale_date: Optional[str] = None  # ISO date string
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    extra: dict = field(default_factory=dict)


@dataclass
class RawIndicator:
    """A single motivation indicator detected for a property."""
    indicator_type: IndicatorType
    confidence: float = 1.0
    source_name: str = ""
    notes: Optional[str] = None
    raw_data: Optional[dict] = None
    expires_days: Optional[int] = None  # None = never expires

    @property
    def category(self) -> IndicatorCategory:
        return INDICATOR_CATEGORIES[self.indicator_type]


@dataclass
class DataSourceResult:
    """Complete result from a single data source run."""
    source_name: str
    location: str
    properties: list[RawPropertyRecord] = field(default_factory=list)
    indicators: dict[str, list[RawIndicator]] = field(default_factory=dict)
    # indicators keyed by parcel_id or address string
    errors: list[str] = field(default_factory=list)
    records_fetched: int = 0


class DataSource(ABC):
    """
    Base class for all data source connectors.

    To add a new data source:
    1. Subclass DataSource
    2. Implement fetch() and map_to_indicators()
    3. Register in registry.py
    """

    name: str  # unique identifier, e.g. "county_assessor"
    display_name: str  # human-readable, e.g. "County Assessor Records"
    description: str
    is_paid: bool = False
    default_enabled: bool = True

    def __init__(self, api_key: Optional[str] = None, config: Optional[dict] = None):
        self.api_key = api_key
        self.config = config or {}

    @abstractmethod
    async def fetch(self, county: str, state: str) -> DataSourceResult:
        """
        Fetch data for the given county/state.
        Return a DataSourceResult with properties and indicators.
        """
        ...

    def is_configured(self) -> bool:
        """Return True if the source has everything it needs to run."""
        if self.is_paid:
            return bool(self.api_key)
        return True

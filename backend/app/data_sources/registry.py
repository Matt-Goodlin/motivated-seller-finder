"""
Registry of all available data source connectors.
Import order determines display order in the UI.
"""
from app.data_sources.base import DataSource
from app.data_sources.county_assessor import CountyAssessorSource
from app.data_sources.court_records import CourtRecordsSource
from app.data_sources.usps_vacancy import USPSVacancySource
from app.data_sources.building_permits import BuildingPermitsSource
from app.data_sources.zillow_mls import ZillowMLSSource
from app.data_sources.attom import ATTOMSource
from app.data_sources.batchdata import BatchDataSource
from app.data_sources.street_view import StreetViewSource

ALL_SOURCES: list[type[DataSource]] = [
    CountyAssessorSource,
    CourtRecordsSource,
    USPSVacancySource,
    BuildingPermitsSource,
    ZillowMLSSource,
    ATTOMSource,
    BatchDataSource,
    StreetViewSource,
]

SOURCE_MAP: dict[str, type[DataSource]] = {s.name: s for s in ALL_SOURCES}


def get_source_class(name: str) -> type[DataSource] | None:
    return SOURCE_MAP.get(name)


def get_all_source_metadata() -> list[dict]:
    return [
        {
            "name": s.name,
            "display_name": s.display_name,
            "description": s.description,
            "is_paid": s.is_paid,
            "default_enabled": s.default_enabled,
        }
        for s in ALL_SOURCES
    ]

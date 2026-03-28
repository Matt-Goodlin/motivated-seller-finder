from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str
    postgres_user: str = "msf"
    postgres_password: str = "changeme"
    postgres_db: str = "motivated_seller"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Admin bootstrap
    admin_email: str
    admin_password: str

    # App
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    # Free data sources
    nominatim_user_agent: str = "motivated-seller-finder/1.0"
    census_api_key: str = ""
    socrata_app_token: str = ""

    # Paid data sources (all optional)
    attom_api_key: str = ""
    batchdata_api_key: str = ""
    propstream_email: str = ""
    propstream_password: str = ""
    rapidapi_key: str = ""
    google_street_view_api_key: str = ""
    mapillary_client_token: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()

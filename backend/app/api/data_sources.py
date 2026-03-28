"""Data source configuration and manual run triggering."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.data_source import DataSourceConfig, DataSourceRun
from app.schemas.data_source import DataSourceOut, DataSourceUpdate, DataSourceRunOut
from app.services.auth import get_current_user, require_admin
from app.data_sources.registry import get_all_source_metadata, get_source_class
from app.tasks.refresh_data import run_data_source_task
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/data-sources", tags=["data-sources"])


@router.get("", response_model=list[DataSourceOut])
async def list_data_sources(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List all data sources with their enabled status and configuration."""
    all_metadata = get_all_source_metadata()

    result = await db.execute(select(DataSourceConfig))
    configs = {c.source_name: c for c in result.scalars().all()}

    output = []
    for meta in all_metadata:
        name = meta["name"]
        config = configs.get(name)
        source_class = get_source_class(name)

        source_instance = source_class(
            api_key=config.api_key_encrypted if config else None,
            config=config.config_json if config else {},
        ) if source_class else None

        output.append(DataSourceOut(
            source_name=name,
            display_name=meta["display_name"],
            description=meta["description"],
            is_paid=meta["is_paid"],
            enabled=config.enabled if config else meta["default_enabled"],
            is_configured=source_instance.is_configured() if source_instance else False,
            last_run_at=config.last_run_at if config else None,
        ))

    return output


@router.put("/{source_name}", response_model=DataSourceOut)
async def update_data_source(
    source_name: str,
    body: DataSourceUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    source_class = get_source_class(source_name)
    if not source_class:
        raise HTTPException(status_code=404, detail=f"Data source '{source_name}' not found")

    result = await db.execute(
        select(DataSourceConfig).where(DataSourceConfig.source_name == source_name)
    )
    config = result.scalar_one_or_none()

    if not config:
        config = DataSourceConfig(
            source_name=source_name,
            enabled=False,
            is_paid=source_class.is_paid,
        )
        db.add(config)

    if body.enabled is not None:
        config.enabled = body.enabled
    if body.api_key is not None:
        # Store API key - in production, encrypt with Fernet before storing
        config.api_key_encrypted = body.api_key
    if body.config_json is not None:
        config.config_json = body.config_json

    await db.commit()

    instance = source_class(api_key=config.api_key_encrypted)
    return DataSourceOut(
        source_name=source_name,
        display_name=source_class.display_name,
        description=source_class.description,
        is_paid=source_class.is_paid,
        enabled=config.enabled,
        is_configured=instance.is_configured(),
        last_run_at=config.last_run_at,
    )


@router.post("/{source_name}/run")
async def trigger_data_source_run(
    source_name: str,
    county: str,
    state: str,
    zip_code: str = "",
    _admin: User = Depends(require_admin),
):
    """Trigger a manual data fetch for the given source and location."""
    source_class = get_source_class(source_name)
    if not source_class:
        raise HTTPException(status_code=404, detail=f"Data source '{source_name}' not found")

    task = run_data_source_task.delay(source_name, county, state, zip_code or None)
    return {"message": f"Data fetch started for {source_name}", "task_id": task.id}


@router.get("/{source_name}/runs", response_model=list[DataSourceRunOut])
async def get_run_history(
    source_name: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DataSourceRun)
        .where(DataSourceRun.source_name == source_name)
        .order_by(DataSourceRun.started_at.desc())
        .limit(50)
    )
    return [DataSourceRunOut.model_validate(r) for r in result.scalars().all()]

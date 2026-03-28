from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "motivated_seller",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.refresh_data", "app.tasks.recalculate_scores"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

# Scheduled tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    "nightly-data-refresh": {
        "task": "app.tasks.refresh_data.refresh_all_sources",
        "schedule": crontab(hour=2, minute=0),  # 2am UTC daily
        "args": [],
    },
    "recalculate-scores-after-refresh": {
        "task": "app.tasks.recalculate_scores.recalculate_all_scores",
        "schedule": crontab(hour=3, minute=0),  # 3am UTC daily
        "args": [],
    },
}

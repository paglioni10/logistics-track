from celery import Celery
from celery.schedules import schedule

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "logistics_track",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.beat_schedule = {
    "poll-active-shipments": {
        "task": "app.workers.tasks.poll_active_shipments",
        "schedule": schedule(run_every=settings.polling_interval_seconds),
    },
}
celery_app.conf.timezone = "America/Sao_Paulo"

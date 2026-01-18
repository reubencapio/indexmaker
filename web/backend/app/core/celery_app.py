import os

from celery import Celery


def get_broker_url() -> str:
    """Get Redis URL for Celery broker, with fallback to localhost."""
    # Try CELERY_BROKER_URL first (if explicitly set and not empty)
    broker = os.environ.get("CELERY_BROKER_URL", "").strip()
    if broker:
        return broker

    # Fall back to REDIS_URL
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if redis_url:
        return redis_url

    # Ultimate fallback to localhost
    return "redis://localhost:6379/0"


BROKER_URL = get_broker_url()
RESULT_BACKEND = BROKER_URL  # Use same URL for results

celery_app = Celery("indexmaker", broker=BROKER_URL, include=["app.tasks"])

celery_app.conf.task_routes = {
    "app.tasks.*": {"queue": "main-queue"},
}

celery_app.conf.update(
    result_backend=RESULT_BACKEND,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


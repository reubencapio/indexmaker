from celery import Celery
from app.core.config import settings

celery_app = Celery("indexmaker", broker=settings.CELERY_BROKER_URL, include=["app.tasks"])

celery_app.conf.task_routes = {
    "app.tasks.*": {"queue": "main-queue"},
}

celery_app.conf.update(
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

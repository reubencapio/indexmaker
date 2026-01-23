import os

from celery import Celery


def get_broker_url() -> str:
    """Get Redis URL for Celery broker, with fallback to localhost."""
    # Try CELERY_BROKER_URL first (if explicitly set and not empty)
    broker = os.environ.get("CELERY_BROKER_URL", "").strip()
    if broker:
        return _ensure_ssl_params(broker)

    # Fall back to REDIS_URL
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if redis_url:
        return _ensure_ssl_params(redis_url)

    # Ultimate fallback to localhost
    return "redis://localhost:6379/0"


def _ensure_ssl_params(url: str) -> str:
    """Add SSL parameters for rediss:// URLs (required by Celery for TLS)."""
    if url.startswith("rediss://"):
        # Check if ssl_cert_reqs is already in the URL
        if "ssl_cert_reqs" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}ssl_cert_reqs=CERT_REQUIRED"
    return url


BROKER_URL = get_broker_url()
RESULT_BACKEND = BROKER_URL  # Use same URL for results

celery_app = Celery("indexforge", broker=BROKER_URL, include=["app.tasks"])

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

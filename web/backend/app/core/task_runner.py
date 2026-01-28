"""
Task runner utility.

Provides a unified interface for dispatching tasks that works in both
development (synchronous) and production (async via Celery) modes.
"""

import logging
from collections.abc import Coroutine
from typing import Any, Callable

from app.core.config import settings

logger = logging.getLogger(__name__)


def run_task(
    celery_task: Any,
    sync_func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Run a task either synchronously or via Celery based on configuration.

    In development (CELERY_ENABLED=False):
        - Runs the sync_func directly in the current process
        - Blocks until complete
        - No Redis/Celery required

    In production (CELERY_ENABLED=True):
        - Dispatches to Celery via .delay()
        - Returns immediately
        - Requires Redis + Celery worker

    Args:
        celery_task: The Celery task to dispatch (when CELERY_ENABLED=True)
        sync_func: The synchronous function to run (when CELERY_ENABLED=False)
        *args: Positional arguments to pass to the task
        **kwargs: Keyword arguments to pass to the task

    Returns:
        In sync mode: The result of sync_func
        In async mode: The Celery AsyncResult

    Example:
        from app.tasks import generate_report_task, generate_report_sync
        from app.core.task_runner import run_task

        run_task(generate_report_task, generate_report_sync, report_id)
    """
    if settings.CELERY_ENABLED:
        logger.debug(f"Dispatching task to Celery: {celery_task.name}")
        return celery_task.delay(*args, **kwargs)
    else:
        logger.debug(f"Running task synchronously: {sync_func.__name__}")
        return sync_func(*args, **kwargs)


async def run_task_async(
    celery_task: Any,
    async_func: Callable[..., Coroutine[Any, Any, Any]],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Run an async task either directly or via Celery.

    In development (CELERY_ENABLED=False):
        - Awaits the async_func directly
        - Runs in the current event loop
        - No Redis/Celery required

    In production (CELERY_ENABLED=True):
        - Dispatches to Celery via .delay()
        - Returns immediately (non-blocking)
        - Requires Redis + Celery worker

    IMPORTANT: This function must be awaited!

    Example:
        await run_task_async(generate_report_task, generate_report_async, report_id)
    """
    if settings.CELERY_ENABLED:
        logger.debug(f"Dispatching task to Celery: {celery_task.name}")
        return celery_task.delay(*args, **kwargs)
    else:
        logger.debug(f"Running async task directly: {async_func.__name__}")
        # Run in background so API doesn't block (similar to Celery behavior)
        # But for dev purposes, we await it to completion
        result = await async_func(*args, **kwargs)
        return result

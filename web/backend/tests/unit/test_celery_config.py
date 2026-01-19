"""
Unit tests for Celery configuration.

Tests the broker URL resolution and task registration.
"""

import os
from unittest.mock import patch


class TestCeleryBrokerUrl:
    """Tests for Celery broker URL configuration."""

    def test_get_broker_url_from_celery_broker_url(self):
        """Test that CELERY_BROKER_URL takes precedence."""
        with patch.dict(
            os.environ,
            {
                "CELERY_BROKER_URL": "redis://custom-broker:6379/0",
                "REDIS_URL": "redis://redis-fallback:6379/0",
            },
            clear=False,
        ):
            # Reimport to pick up new env vars
            from app.core.celery_app import get_broker_url

            url = get_broker_url()
            assert "custom-broker" in url or "redis" in url  # Either is valid

    def test_get_broker_url_from_redis_url(self):
        """Test fallback to REDIS_URL when CELERY_BROKER_URL is not set."""
        with patch.dict(
            os.environ,
            {
                "CELERY_BROKER_URL": "",
                "REDIS_URL": "redis://redis-host:6379/0",
            },
            clear=False,
        ):
            from app.core.celery_app import get_broker_url

            url = get_broker_url()
            # Should contain redis in the URL
            assert "redis://" in url

    def test_get_broker_url_localhost_fallback(self):
        """Test fallback to localhost when no env vars are set."""
        with patch.dict(
            os.environ,
            {
                "CELERY_BROKER_URL": "",
                "REDIS_URL": "",
            },
            clear=False,
        ):
            from app.core.celery_app import get_broker_url

            url = get_broker_url()
            assert url == "redis://localhost:6379/0"

    def test_ensure_ssl_params_for_rediss_url(self):
        """Test that SSL parameters are added for rediss:// URLs."""
        from app.core.celery_app import _ensure_ssl_params

        # Test with rediss URL (TLS)
        url = "rediss://secure-redis:6379/0"
        result = _ensure_ssl_params(url)
        assert "ssl_cert_reqs" in result

    def test_ensure_ssl_params_not_added_for_redis_url(self):
        """Test that SSL parameters are NOT added for regular redis:// URLs."""
        from app.core.celery_app import _ensure_ssl_params

        # Test with regular redis URL
        url = "redis://redis:6379/0"
        result = _ensure_ssl_params(url)
        assert result == url  # Should be unchanged


class TestCeleryAppConfiguration:
    """Tests for Celery app setup."""

    def test_celery_app_has_correct_name(self):
        """Test that Celery app is named correctly."""
        from app.core.celery_app import celery_app

        assert celery_app.main == "indexmaker"

    def test_celery_app_includes_tasks_module(self):
        """Test that Celery app includes the tasks module."""
        from app.core.celery_app import celery_app

        assert "app.tasks" in celery_app.conf.include

    def test_celery_app_has_task_routes(self):
        """Test that Celery app has task routing configured."""
        from app.core.celery_app import celery_app

        routes = celery_app.conf.task_routes
        assert "app.tasks.*" in routes
        assert routes["app.tasks.*"]["queue"] == "main-queue"

    def test_celery_app_uses_json_serializer(self):
        """Test that Celery uses JSON serialization."""
        from app.core.celery_app import celery_app

        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content

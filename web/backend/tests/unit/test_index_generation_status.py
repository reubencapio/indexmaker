"""
Unit tests for index generation status bookkeeping.

A failed AI generation used to leave the index sitting in "building" (or in an
"error" status that was not part of IndexStatus at all), which the UI rendered as
"Draft". These tests pin down the status transitions the UI depends on.
"""

from unittest.mock import MagicMock, patch

from app.models.index import IndexStatus
from app.tasks import MAX_ERROR_MESSAGE_LENGTH, _mark_index_error, is_transient_error


class TestIndexStatusEnum:
    """The UI branches on these exact values."""

    def test_error_is_a_real_status(self):
        assert IndexStatus.ERROR.value == "error"

    def test_building_is_a_real_status(self):
        assert IndexStatus.BUILDING.value == "building"


class TestMarkIndexError:
    """Tests for the failure-bookkeeping helper."""

    def _patched_session(self, index):
        """Build a SessionLocal stub whose query chain returns `index`."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = index
        return db

    def test_sets_error_status_and_message(self):
        index = MagicMock()
        db = self._patched_session(index)

        with patch("app.tasks.SessionLocal", return_value=db):
            _mark_index_error("some-index-id", "AI generation failed: boom")

        assert index.status == IndexStatus.ERROR.value
        assert index.error_message == "AI generation failed: boom"
        db.commit.assert_called_once()
        db.close.assert_called_once()

    def test_truncates_long_messages(self):
        index = MagicMock()
        db = self._patched_session(index)

        with patch("app.tasks.SessionLocal", return_value=db):
            _mark_index_error("some-index-id", "x" * (MAX_ERROR_MESSAGE_LENGTH + 250))

        assert len(index.error_message) == MAX_ERROR_MESSAGE_LENGTH

    def test_missing_index_does_not_raise(self):
        db = self._patched_session(None)

        with patch("app.tasks.SessionLocal", return_value=db):
            _mark_index_error("does-not-exist", "boom")

        db.commit.assert_not_called()
        db.close.assert_called_once()

    def test_db_failure_is_swallowed(self):
        """Bookkeeping must never mask the original generation error."""
        db = MagicMock()
        db.query.side_effect = RuntimeError("connection lost")

        with patch("app.tasks.SessionLocal", return_value=db):
            _mark_index_error("some-index-id", "boom")

        db.close.assert_called_once()


class TestTransientErrorClassification:
    """
    Retrying a permanent error burns quota and delays the user seeing the real
    reason, so the classifier is deliberately conservative.
    """

    def test_retired_model_is_permanent(self):
        """The failure that actually took generation down for two days."""
        assert not is_transient_error(
            "404 POST https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-3-pro-preview:generateContent: This model is no longer available."
        )

    def test_missing_api_key_is_permanent(self):
        assert not is_transient_error("GEMINI_API_KEY not configured")

    def test_malformed_response_is_permanent(self):
        assert not is_transient_error("Could not parse LLM response as JSON")

    def test_rate_limit_is_transient(self):
        assert is_transient_error("429 Too Many Requests")

    def test_service_unavailable_is_transient(self):
        assert is_transient_error("503 Service Unavailable")

    def test_timeout_is_transient(self):
        assert is_transient_error("Deadline Exceeded while awaiting response")

    def test_overload_is_transient(self):
        assert is_transient_error("The model is overloaded. Please try again later.")

    def test_classification_is_case_insensitive(self):
        assert is_transient_error("CONNECTION RESET by peer")

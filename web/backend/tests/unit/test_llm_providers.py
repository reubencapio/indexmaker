"""
Tests for AI provider selection and fallback in the LLM service.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services import llm_service
from app.services.llm_service import AIUnavailableError

VALID_JSON = '{"name": "Dividend Leaders", "identifier": "DIVLEAD", "tickers": ["KO", "PG"]}'


def _keys(monkeypatch, *, anthropic=None, gemini=None, openai=None):
    monkeypatch.setattr(llm_service.settings, "ANTHROPIC_API_KEY", anthropic)
    monkeypatch.setattr(llm_service.settings, "GEMINI_API_KEY", gemini)
    monkeypatch.setattr(llm_service.settings, "OPENAI_API_KEY", openai)


def _claude_response(text, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)] if text is not None else [],
    )


class TestProviderOrder:
    @pytest.mark.asyncio
    async def test_claude_is_used_first_when_configured(self, monkeypatch):
        _keys(monkeypatch, anthropic="k", gemini="k")
        claude = AsyncMock(return_value=VALID_JSON)
        gemini = AsyncMock(return_value=VALID_JSON)
        monkeypatch.setattr(llm_service, "call_claude", claude)
        monkeypatch.setattr(llm_service, "call_gemini", gemini)

        config = await llm_service.generate_index_config_from_llm("dividend payers")

        assert config["name"] == "Dividend Leaders"
        claude.assert_awaited_once()
        gemini.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_gemini_is_used_without_a_claude_key(self, monkeypatch):
        _keys(monkeypatch, gemini="k")
        claude = AsyncMock(return_value=VALID_JSON)
        gemini = AsyncMock(return_value=VALID_JSON)
        monkeypatch.setattr(llm_service, "call_claude", claude)
        monkeypatch.setattr(llm_service, "call_gemini", gemini)

        await llm_service.generate_index_config_from_llm("dividend payers")

        claude.assert_not_awaited()
        gemini.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_keys_is_a_clear_error(self, monkeypatch):
        _keys(monkeypatch)
        with pytest.raises(ValueError, match="No AI API key configured"):
            await llm_service.generate_index_config_from_llm("anything")


class TestFallback:
    @pytest.mark.asyncio
    async def test_falls_back_to_gemini_when_claude_fails(self, monkeypatch):
        _keys(monkeypatch, anthropic="k", gemini="k")
        monkeypatch.setattr(
            llm_service, "call_claude", AsyncMock(side_effect=RuntimeError("529 overloaded"))
        )
        gemini = AsyncMock(return_value=VALID_JSON)
        monkeypatch.setattr(llm_service, "call_gemini", gemini)

        config = await llm_service.generate_index_config_from_llm("dividend payers")

        assert config["identifier"] == "DIVLEAD"
        gemini.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_provider_error_text_never_reaches_the_user(self, monkeypatch):
        _keys(monkeypatch, gemini="k")
        raw = "429 POST https://generativelanguage.googleapis.com/v1beta/models/x: quota"
        monkeypatch.setattr(llm_service, "call_gemini", AsyncMock(side_effect=RuntimeError(raw)))

        with pytest.raises(AIUnavailableError) as excinfo:
            await llm_service.generate_index_config_from_llm("dividend payers")

        assert "googleapis" not in str(excinfo.value)
        assert "try again" in str(excinfo.value).lower()

    @pytest.mark.asyncio
    async def test_user_facing_error_is_kept_when_every_provider_fails(self, monkeypatch):
        _keys(monkeypatch, anthropic="k", gemini="k")
        monkeypatch.setattr(
            llm_service,
            "call_claude",
            AsyncMock(
                side_effect=ValueError("Request was filtered. Please try a simpler description.")
            ),
        )
        monkeypatch.setattr(llm_service, "call_gemini", AsyncMock(side_effect=RuntimeError("503")))

        with pytest.raises(ValueError, match="Request was filtered"):
            await llm_service.generate_index_config_from_llm("dividend payers")


class TestCallClaude:
    def _patch_client(self, response):
        client = SimpleNamespace(messages=SimpleNamespace(create=AsyncMock(return_value=response)))
        return patch("anthropic.AsyncAnthropic", return_value=client), client

    @pytest.mark.asyncio
    async def test_sends_system_prompt_and_configured_model(self, monkeypatch):
        _keys(monkeypatch, anthropic="k")
        monkeypatch.setattr(llm_service.settings, "ANTHROPIC_MODEL", "claude-test-model")
        patcher, client = self._patch_client(_claude_response(VALID_JSON))

        with patcher:
            text = await llm_service.call_claude("top dividend payers")

        assert text == VALID_JSON
        kwargs = client.messages.create.await_args.kwargs
        assert kwargs["model"] == "claude-test-model"
        assert kwargs["system"] == llm_service.SYSTEM_PROMPT
        assert "top dividend payers" in kwargs["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_refusal_becomes_a_user_facing_error(self, monkeypatch):
        _keys(monkeypatch, anthropic="k")
        patcher, _ = self._patch_client(_claude_response(None, stop_reason="refusal"))

        with patcher, pytest.raises(ValueError, match="filtered"):
            await llm_service.call_claude("anything")

    @pytest.mark.asyncio
    async def test_empty_response_is_an_error(self, monkeypatch):
        _keys(monkeypatch, anthropic="k")
        patcher, _ = self._patch_client(_claude_response("  "))

        with patcher, pytest.raises(ValueError, match="Empty response"):
            await llm_service.call_claude("anything")

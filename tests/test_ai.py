"""
Tests for the AI-powered index creation module.
"""

import importlib.util
import json
from unittest.mock import MagicMock, patch

import pytest

# IndexAI resolves the OpenAI client lazily inside `_get_client` via
# `from openai import OpenAI`, so the attribute is looked up on the `openai`
# module at call time -- that module is the correct patch target.
OPENAI_CLIENT = "openai.OpenAI"

requires_openai = pytest.mark.skipif(
    importlib.util.find_spec("openai") is None,
    reason="openai package not installed",
)


class TestIndexAI:
    """Tests for IndexAI class."""

    def test_import_without_openai(self):
        """Test that import works even without openai package."""
        # The import should not fail
        from indexforge import IndexAI

        # But IndexAI might be None if openai is not installed
        # This is expected behavior
        assert IndexAI is None or callable(IndexAI)

    def test_ai_module_structure(self):
        """Test that the AI module has the expected exports."""
        from indexforge import ai

        assert hasattr(ai, "IndexAI")
        assert hasattr(ai, "IndexAIConfig")

    @pytest.fixture
    def mock_openai(self):
        """Mock the OpenAI client."""
        with patch(OPENAI_CLIENT) as mock:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(
                            {
                                "name": "Test Index",
                                "identifier": "TESTIDX",
                                "currency": "USD",
                                "base_date": "2024-01-01",
                                "base_value": 1000,
                                "index_type": "PRICE_RETURN",
                                "universe": {"tickers": ["AAPL", "MSFT", "GOOGL"]},
                                "weighting": {"scheme": "EQUAL_WEIGHT"},
                                "rebalancing": {"frequency": "QUARTERLY"},
                                "explanation": "Test index created successfully",
                            }
                        )
                    )
                )
            ]
            mock_client.chat.completions.create.return_value = mock_response
            mock.return_value = mock_client
            yield mock

    @requires_openai
    def test_create_index_from_description(self, mock_openai):
        """Test creating an index from a description."""
        from indexforge.ai import IndexAI

        ai = IndexAI(api_key="test-key")
        result = ai.create_index("Create a test index with FAANG stocks")

        assert result.index is not None
        assert result.index.name == "Test Index"
        assert result.index.identifier == "TESTIDX"
        assert result.explanation == "Test index created successfully"

    @requires_openai
    def test_config_options(self):
        """Test IndexAIConfig options."""
        from indexforge.ai import IndexAIConfig

        config = IndexAIConfig(
            api_key="test-key",
            model="gpt-4",
            temperature=0.5,
            max_tokens=1500,
        )

        assert config.api_key == "test-key"
        assert config.model == "gpt-4"
        assert config.temperature == 0.5
        assert config.max_tokens == 1500


class TestIndexAIParseResponse:
    """Tests for response parsing."""

    @requires_openai
    def test_parse_json_response(self):
        """Test parsing a clean JSON response."""
        from indexforge.ai import IndexAI

        with patch(OPENAI_CLIENT):
            ai = IndexAI(api_key="test-key")

            response = '{"name": "Test", "identifier": "TEST"}'
            result = ai._parse_response(response)

            assert result["name"] == "Test"
            assert result["identifier"] == "TEST"

    @requires_openai
    def test_parse_markdown_json(self):
        """Test parsing JSON in markdown code blocks."""
        from indexforge.ai import IndexAI

        with patch(OPENAI_CLIENT):
            ai = IndexAI(api_key="test-key")

            response = """
Here is the configuration:

```json
{"name": "Test", "identifier": "TEST"}
```
"""
            result = ai._parse_response(response)

            assert result["name"] == "Test"


class TestBuildIndex:
    """Tests for building indices from configuration."""

    @requires_openai
    def test_build_basic_index(self):
        """Test building a basic index from config."""
        from indexforge.ai import IndexAI

        with patch(OPENAI_CLIENT):
            ai = IndexAI(api_key="test-key")

            config = {
                "name": "Test Index",
                "identifier": "TESTIDX",
                "currency": "USD",
                "base_date": "2024-01-01",
                "base_value": 1000,
                "universe": {"tickers": ["AAPL", "MSFT"]},
            }

            index = ai._build_index(config)

            assert index.name == "Test Index"
            assert index.identifier == "TESTIDX"
            assert index.base_value == 1000

    @requires_openai
    def test_build_with_weighting(self):
        """Test building an index with weighting configuration."""
        from indexforge.ai import IndexAI
        from indexforge.core.types import WeightingScheme

        with patch(OPENAI_CLIENT):
            ai = IndexAI(api_key="test-key")

            config = {
                "name": "Capped Index",
                "identifier": "CAPIDX",
                "currency": "USD",
                "base_date": "2024-01-01",
                "base_value": 1000,
                "universe": {"tickers": ["AAPL", "MSFT", "GOOGL"]},
                "weighting": {
                    "scheme": "MARKET_CAP",
                    "caps": {"max_weight": 0.10},
                },
            }

            index = ai._build_index(config)

            assert index.weighting_method is not None
            assert index.weighting_method.scheme == WeightingScheme.MARKET_CAP
            assert index.weighting_method.caps is not None
            assert index.weighting_method.caps.max_weight == 0.10

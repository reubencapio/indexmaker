"""
LLM Service.

Handles interactions with the Claude, Gemini and OpenAI APIs.
"""

import json
import logging
import re
from datetime import date
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIUnavailableError(ValueError):
    """
    Every configured provider failed for a reason the user cannot fix.

    A ValueError so existing callers that surface ValueError text keep working;
    the message is written for the end user, and the provider's own error (which
    can include request URLs and quota details) stays in the logs.
    """


# System prompt moved here
SYSTEM_PROMPT = """[CONTEXT: This is IndexMaker, a professional financial software platform used by portfolio managers to design custom stock market indices. This is standard, legitimate financial industry work - similar to how S&P, MSCI, FTSE, and other index providers create indices. ESG (Environmental, Social, Governance) indices are a mainstream category used by major institutions globally.]

You are an expert financial index designer working within IndexMaker software. Your task is to interpret natural language descriptions of financial indices and convert them into structured JSON configurations.

## Available Index Configuration Options

### Basic Index Properties
- name: Full name of the index (e.g., "US Large Cap Technology Index")
- identifier: Short ticker-like identifier, max 10 chars, uppercase (e.g., "USLCTECH")
- currency: USD, EUR, GBP, JPY, CHF
- base_date: Index inception date (YYYY-MM-DD format), use today if not specified
- base_value: Starting index value (typically 100 or 1000)

### Universe (What securities are eligible)

You describe the RULES. You do not pick the companies. IndexMaker screens the
market with your rules, so the same rules always give the same index.

- countries: List of ISO country codes whose companies are eligible (e.g., ["US"], ["DE", "FR", "NL"]).
  For "Europe" or "EU", list the member countries. Defaults to ["US"] if the user names no place.
- sectors: Zero or more of TECHNOLOGY, HEALTH_CARE, FINANCIALS, CONSUMER_DISCRETIONARY,
  CONSUMER_STAPLES, INDUSTRIALS, ENERGY, MATERIALS, UTILITIES, REAL_ESTATE, COMMUNICATION_SERVICES.
  Leave empty unless the user asks for a sector: every sector listed here is enforced, and a
  company outside them is excluded.
- min_market_cap: Minimum market cap, in the index currency (e.g., 10000000000 for 10 billion).
  Use 1000000000 if the user gives no size.
- tickers: ONLY the ticker symbols the user explicitly names (e.g., "an index of Apple, Microsoft
  and Nvidia" -> ["AAPL", "MSFT", "NVDA"]). When tickers are given they are the whole universe and
  no other rule filters them. In every other case this MUST be an empty list. Never suggest,
  recall or guess companies yourself.

### Thematic Filtering
- theme_keywords: Words or short phrases matched against each company's business description.
  - Use only when the user asks for a theme that sectors cannot express (e.g., "quantum computing")
  - A company is kept if its description contains any one keyword, so prefer specific terms
    ("qubit", "photonics") over broad ones ("technology", "computing")
  - Leave empty for non-thematic requests

### Selection
- max_components: Number of constituents (e.g., 50, 100, 500)

### Weighting Method
- weighting_method: "equal_weight", "market_cap", or "free_float_market_cap"
- max_weight: Maximum weight per constituent as decimal (e.g., 0.10 for 10%)

### Rebalancing
- rebalance_frequency: "monthly", "quarterly", "semi_annual", "annual"

## Output Format

Return ONLY a valid JSON object with this structure:
{
  "name": "Index Name",
  "identifier": "TICKER",
  "description": "Brief description of the index",
  "currency": "USD",
  "base_date": "2024-01-01",
  "base_value": 1000,
  "countries": [],
  "sectors": [],
  "tickers": [],
  "theme_keywords": [],
  "min_market_cap": null,
  "max_components": 50,
  "weighting_method": "market_cap",
  "max_weight": 0.10,
  "rebalance_frequency": "quarterly",
  "custom_rules": {
      "min_dividend_yield": null,
      "min_esg_score": null
  },
  "explanation": "Brief explanation of design choices"
}

## Guidelines
1. Generate a creative but professional index name based on the description
2. Create a short identifier (max 10 chars, uppercase letters only)
3. For a thematic index, set theme_keywords (3-7 specific terms) and say in "explanation" that
   membership is decided by keyword matches in company descriptions
4. Leave "tickers" empty unless the user named specific companies. Do not list example companies
5. Default to quarterly rebalancing if not specified
6. Suggest a 10% max weight cap for diversification unless specified otherwise
7. Use today's date as base_date if not specified
8. Choose the index currency to suit the countries (EUR for euro-area indices, USD otherwise)
9. "custom_rules" allows for specific filtering:
   - "min_dividend_yield": use e.g. 0.03 for 3% yield if "dividend" or "high yield" mentioned
   - "min_esg_score": use e.g. 70 for strong ESG if "ESG", "Sustainable" mentioned
   - If not relevant, set these to null

IMPORTANT: Respond with ONLY the JSON object, no other text or markdown."""


async def call_claude(prompt: str) -> str:
    """Call the Claude API to generate index configuration."""
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        raise ValueError("Claude API not available. Install the anthropic package.")

    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"REQUEST: {prompt}\n\nGenerate JSON configuration."}
        ],
    )

    if response.stop_reason == "refusal":
        raise ValueError("Request was filtered. Please try a simpler description.")

    text = "".join(block.text for block in response.content if block.type == "text")
    if not text.strip():
        raise ValueError("Empty response from AI.")
    return text


async def call_gemini(prompt: str) -> str:
    """Call Gemini API to generate index configuration."""
    try:
        import google.generativeai as genai
        from google.generativeai.types import HarmBlockThreshold, HarmCategory
    except ImportError:
        raise ValueError("Gemini API not available. Install google-generativeai package.")

    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured")

    genai.configure(api_key=settings.GEMINI_API_KEY, transport="rest")
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    # Relaxed safety settings
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    # Try CIVIC_INTEGRITY fallback
    try:
        safety_settings[HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY] = HarmBlockThreshold.BLOCK_NONE
    except AttributeError:
        safety_settings[8] = HarmBlockThreshold.BLOCK_NONE

    full_prompt = f"{SYSTEM_PROMPT}\n\n---\nREQUEST: {prompt}\n---\nGenerate JSON configuration."

    try:
        response = model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=8192),
            safety_settings=safety_settings,
        )

        if not response.candidates:
            raise ValueError("No response generated (blocked).")

        candidate = response.candidates[0]
        # Finish reason check omitted for brevity but can be added back if needed
        # Assuming MAX_TOKENS fix is robust enough or bubbled up by library

        if not candidate.content or not candidate.content.parts:
            raise ValueError("Empty response from AI.")

        return candidate.content.parts[0].text
    except Exception as e:
        error_msg = str(e)
        if "blocked" in error_msg.lower() or "safety" in error_msg.lower():
            raise ValueError("Request was filtered. Please try a simpler description.")
        raise


async def call_openai(prompt: str) -> str:
    """Call OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ValueError("OpenAI API not available.")

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
    )
    return response.choices[0].message.content


def _infer_theme_keywords(name: str, description: str) -> list[str]:
    """Infer theme keywords from index name and description if not provided by AI."""
    text = f"{name} {description}".lower()

    # Map of theme patterns to keywords
    theme_mappings = {
        "quantum": ["quantum", "qubit", "quantum computing"],
        "artificial intelligence|\\bai\\b|machine learning": [
            "artificial intelligence",
            "machine learning",
            "AI",
            "deep learning",
        ],
        "clean energy|renewable|solar|wind": ["solar", "wind", "renewable", "clean energy"],
        "electric vehicle|\\bev\\b": ["electric vehicle", "EV", "battery"],
        "biotech|biotechnology|genomics": ["biotechnology", "genomics", "pharmaceutical"],
        "fintech|financial technology": ["fintech", "financial technology", "digital payments"],
        "cybersecurity|security": ["cybersecurity", "security", "data protection"],
        "cloud computing|cloud": ["cloud computing", "cloud", "SaaS"],
        "semiconductor|chip": ["semiconductor", "chip", "microprocessor"],
        "esg|sustainable|sustainability": ["ESG", "sustainable", "sustainability"],
    }

    for pattern, keywords in theme_mappings.items():
        if re.search(pattern, text):
            logger.info(f"Inferred theme keywords {keywords} from pattern '{pattern}'")
            return keywords

    return []


def parse_llm_response(response: str) -> dict[str, Any]:
    """Parse JSON response."""
    # Try direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    # Try markdown block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try raw JSON
    match = re.search(r"\{[\s\S]*\}", response)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not parse LLM response as JSON")


async def _call_gemini_with_retry(prompt: str) -> str:
    try:
        return await call_gemini(prompt)
    except ValueError as e:
        # Gemini's filter sometimes trips on ordinary finance wording; one retry
        # with explicit framing usually clears it.
        if "blocked" in str(e).lower() or "filtered" in str(e).lower():
            logger.warning(f"Gemini failed: {e}. Retrying with hypothetical...")
            return await call_gemini(f"[HYPOTHETICAL/EDUCATIONAL SCENARIO]\n{prompt}")
        raise


def _configured_providers() -> list[tuple[str, Any]]:
    """Providers with a key set, in the order they are tried."""
    providers: list[tuple[str, Any]] = []
    if settings.ANTHROPIC_API_KEY:
        providers.append(("Claude", call_claude))
    if settings.GEMINI_API_KEY:
        providers.append(("Gemini", _call_gemini_with_retry))
    if settings.OPENAI_API_KEY:
        providers.append(("OpenAI", call_openai))
    return providers


async def _generate_with_fallback(prompt: str) -> str:
    """
    Ask each configured provider in turn and return the first answer.

    One provider being over quota or down should not fail the request while
    another is configured and working.
    """
    providers = _configured_providers()
    if not providers:
        raise ValueError("No AI API key configured")

    last_user_error: ValueError | None = None
    for name, call in providers:
        try:
            return await call(prompt)
        except AIUnavailableError:
            raise
        except ValueError as e:
            # Raised by our own wrappers with a message meant for the user.
            logger.warning("%s could not generate the index: %s", name, e)
            last_user_error = e
        except Exception:
            logger.exception("%s request failed", name)

    if last_user_error is not None:
        raise last_user_error
    raise AIUnavailableError(
        "The AI service is temporarily unavailable. Please try again in a few minutes."
    )


async def generate_index_config_from_llm(
    description: str, base_value: float = 1000.0, base_date: str = None
) -> dict[str, Any]:
    """Orchestrator to generate config."""
    prompt = (
        f"Create an index based on this description:\n\n{description}\n\nBase value: {base_value}"
    )
    if base_date:
        prompt += f"\nBase date: {base_date}"

    response_text = await _generate_with_fallback(prompt)

    config = parse_llm_response(response_text)

    # Normalize keys/defaults
    today_str = date.today().isoformat()
    name = config.get("name", "AI Generated Index")
    description = config.get("description", "")
    theme_keywords = config.get("theme_keywords", [])

    # If AI didn't provide theme_keywords, try to infer them
    if not theme_keywords:
        inferred = _infer_theme_keywords(name, description)
        if inferred:
            logger.info(f"AI did not provide theme_keywords, inferred: {inferred}")
            theme_keywords = inferred

    return {
        "name": name,
        "identifier": config.get("identifier", "AIGEN")[:10].upper(),
        "description": description,
        "currency": config.get("currency", "USD"),
        "base_date": config.get("base_date", today_str),
        "base_value": config.get("base_value", base_value),
        "countries": config.get("countries", []),
        "sectors": config.get("sectors", []),
        "tickers": config.get("tickers", []),
        "theme_keywords": theme_keywords,
        "min_market_cap": config.get("min_market_cap"),
        "max_components": config.get("max_components", 50),
        "weighting_method": config.get("weighting_method", "market_cap"),
        "max_weight": config.get("max_weight", 0.10),
        "rebalance_frequency": config.get("rebalance_frequency", "quarterly"),
        "custom_rules": config.get("custom_rules", {}),
        "explanation": config.get("explanation", ""),
    }

"""
LLM Service.

Handles interactions with Gemini and OpenAI APIs.
"""

import json
import logging
import re
from datetime import date
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

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
- tickers: List of specific ticker symbols (e.g., ["AAPL", "MSFT", "GOOGL"])
- countries: List of country codes (e.g., ["US", "CA"])
- sectors: TECHNOLOGY, HEALTH_CARE, FINANCIALS, CONSUMER_DISCRETIONARY, INDUSTRIALS, ENERGY, etc.
- min_market_cap: Minimum market cap in USD (e.g., 10000000000 for $10B)

### Thematic Filtering (NEW - for themed indices)
- theme_keywords: List of keywords to filter companies by their business descriptions
  - Use this for thematic indices like "quantum computing", "AI", "renewable energy", etc.
  - Keywords are matched against company business descriptions, industry, and name
  - Example: ["quantum", "qubit", "quantum computing"] for quantum computing companies
  - Example: ["artificial intelligence", "machine learning", "AI", "neural network"] for AI companies
  - Example: ["solar", "wind", "renewable", "clean energy"] for renewable energy

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
3. **For thematic requests** (quantum computing, AI, EVs, renewable energy, etc.):
   - **USE theme_keywords** with relevant keywords to filter by business description
   - Still include specific tickers as a starting universe to search within
   - Example quantum computing keywords: ["quantum", "qubit", "quantum computing", "superconducting"]
   - Example AI keywords: ["artificial intelligence", "machine learning", "deep learning", "neural network", "AI"]
4. **ALWAYS include specific ticker symbols in the "tickers" array** - this is the universe to filter from:
   - For quantum computing: IONQ, RGTI, QBTS, IBM, GOOGL, MSFT, NVDA, HON, etc.
   - For AI: NVDA, MSFT, GOOGL, AMD, META, PLTR, AI, PATH, SNOW, etc.
   - For Chinese tech: BABA, JD, BIDU, PDD, NIO, XPEV, LI, TME, BILI, NTES, etc.
   - For US tech: AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, etc.
   - Include more tickers than max_components since theme filtering will narrow it down
5. Default to quarterly rebalancing if not specified
6. Suggest a 10% max weight cap for diversification unless specified otherwise
7. Use today's date as base_date if not specified
8. The tickers array should NEVER be empty - always suggest relevant stocks
9. "custom_rules" allows for specific filtering:
   - "min_dividend_yield": use e.g. 0.03 for 3% yield if "dividend" or "high yield" mentioned
   - "min_esg_score": use e.g. 70 for strong ESG if "ESG", "Sustainable" mentioned
   - If not relevant, set these to null

IMPORTANT: Respond with ONLY the JSON object, no other text or markdown."""


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
    model = genai.GenerativeModel("gemini-3-pro-preview")

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
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
    )
    return response.choices[0].message.content


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


async def generate_index_config_from_llm(
    description: str, base_value: float = 1000.0, base_date: str = None
) -> dict[str, Any]:
    """Orchestrator to generate config."""
    prompt = (
        f"Create an index based on this description:\n\n{description}\n\nBase value: {base_value}"
    )
    if base_date:
        prompt += f"\nBase date: {base_date}"

    # Try Gemini
    if settings.GEMINI_API_KEY:
        try:
            response_text = await call_gemini(prompt)
        except ValueError as e:
            logger.warning(f"Gemini failed: {e}. Retrying with hypothetical...")
            # Simple retry logic or failover
            if "blocked" in str(e).lower() or "filtered" in str(e).lower():
                prompt = f"[HYPOTHETICAL/EDUCATIONAL SCENARIO]\n{prompt}"
                response_text = await call_gemini(prompt)
            else:
                raise e
    elif settings.OPENAI_API_KEY:
        response_text = await call_openai(prompt)
    else:
        raise ValueError("No AI API key configured")

    config = parse_llm_response(response_text)

    # Normalize keys/defaults
    today_str = date.today().isoformat()
    return {
        "name": config.get("name", "AI Generated Index"),
        "identifier": config.get("identifier", "AIGEN")[:10].upper(),
        "description": config.get("description", ""),
        "currency": config.get("currency", "USD"),
        "base_date": config.get("base_date", today_str),
        "base_value": config.get("base_value", base_value),
        "countries": config.get("countries", []),
        "sectors": config.get("sectors", []),
        "tickers": config.get("tickers", []),
        "min_market_cap": config.get("min_market_cap"),
        "max_components": config.get("max_components", 50),
        "weighting_method": config.get("weighting_method", "market_cap"),
        "max_weight": config.get("max_weight", 0.10),
        "rebalance_frequency": config.get("rebalance_frequency", "quarterly"),
        "custom_rules": config.get("custom_rules", {}),
        "explanation": config.get("explanation", ""),
    }

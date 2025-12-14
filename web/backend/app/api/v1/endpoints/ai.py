"""
AI-powered index creation endpoints.

Uses LLMs (Gemini or OpenAI) to create indices from natural language descriptions.
"""

import json
import logging
import re
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.core.config import settings
from app.models.index import Index

logger = logging.getLogger(__name__)

router = APIRouter()


# System prompt for the LLM
SYSTEM_PROMPT = """You are an expert financial index designer. Your task is to interpret natural language descriptions of financial indices and convert them into structured JSON configurations.

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
  "min_market_cap": null,
  "max_components": 50,
  "weighting_method": "market_cap",
  "max_weight": 0.10,
  "rebalance_frequency": "quarterly",
  "explanation": "Brief explanation of design choices"
}

## Guidelines
1. Generate a creative but professional index name based on the description
2. Create a short identifier (max 10 chars, uppercase letters only)
3. If specific tickers are mentioned, include them
4. Default to quarterly rebalancing if not specified
5. Suggest a 10% max weight cap for diversification unless specified otherwise
6. Use today's date as base_date if not specified

IMPORTANT: Respond with ONLY the JSON object, no other text or markdown."""


class AICreateIndexRequest(BaseModel):
    """Request model for AI index creation."""

    description: str
    base_date: str | None = None
    base_value: float = 1000.0


class AICreateIndexResponse(BaseModel):
    """Response model for AI index creation."""

    index: dict[str, Any]
    explanation: str
    config: dict[str, Any]


async def call_gemini(prompt: str) -> str:
    """Call Gemini API to generate index configuration."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API not available. Install google-generativeai package.",
        )

    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY not configured",
        )

    genai.configure(api_key=settings.GEMINI_API_KEY)

    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(
        [
            {"role": "user", "parts": [SYSTEM_PROMPT]},
            {"role": "model", "parts": ["I understand. I will respond with only valid JSON."]},
            {"role": "user", "parts": [prompt]},
        ],
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=2000,
        ),
    )

    return response.text


async def call_openai(prompt: str) -> str:
    """Call OpenAI API to generate index configuration."""
    try:
        from openai import OpenAI
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API not available. Install openai package.",
        )

    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY not configured",
        )

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


def parse_llm_response(response: str) -> dict:
    """Parse the LLM response into a configuration dictionary."""
    # Try direct JSON parsing
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in markdown code blocks
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON object
    json_match = re.search(r"\{[\s\S]*\}", response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse LLM response as JSON: {response[:200]}...")


@router.post("/generate", response_model=AICreateIndexResponse)
async def generate_index_from_description(
    request: AICreateIndexRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AICreateIndexResponse:
    """
    Generate an index configuration from a natural language description.

    Uses AI (Gemini or OpenAI) to interpret the description and generate
    a complete index configuration.
    """
    # Build the prompt
    today = date.today().isoformat()
    prompt = f"""Create an index based on this description:

{request.description}

Today's date is {today}.
Base value should be {request.base_value}.
"""
    if request.base_date:
        prompt += f"Use {request.base_date} as the base date.\n"

    # Try Gemini first, then OpenAI
    try:
        if settings.GEMINI_API_KEY:
            logger.info("Using Gemini API for index generation")
            response_text = await call_gemini(prompt)
        elif settings.OPENAI_API_KEY:
            logger.info("Using OpenAI API for index generation")
            response_text = await call_openai(prompt)
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No AI API key configured. Set GEMINI_API_KEY or OPENAI_API_KEY.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI API call failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI generation failed: {str(e)}",
        )

    # Parse the response
    try:
        config = parse_llm_response(response_text)
    except ValueError as e:
        logger.error(f"Failed to parse AI response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse AI response. Please try again.",
        )

    explanation = config.pop("explanation", "Index generated from your description.")

    # Build the index response (matching what the frontend expects)
    index_data = {
        "name": config.get("name", "AI Generated Index"),
        "identifier": config.get("identifier", "AIGEN")[:10].upper(),
        "description": config.get("description", ""),
        "currency": config.get("currency", "USD"),
        "base_date": config.get("base_date", today),
        "base_value": config.get("base_value", request.base_value),
        "countries": config.get("countries", []),
        "sectors": config.get("sectors", []),
        "tickers": config.get("tickers", []),
        "min_market_cap": config.get("min_market_cap"),
        "max_components": config.get("max_components", 50),
        "weighting_method": config.get("weighting_method", "market_cap"),
        "max_weight": config.get("max_weight", 0.10),
        "rebalance_frequency": config.get("rebalance_frequency", "quarterly"),
    }

    return AICreateIndexResponse(
        index=index_data,
        explanation=explanation,
        config=config,
    )


@router.post("/create", response_model=dict)
async def create_index_from_ai(
    request: AICreateIndexRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Generate and immediately create an index from a natural language description.

    This endpoint combines AI generation with index creation in one step.
    """
    # First generate the configuration
    result = await generate_index_from_description(request, current_user, db)

    # Create the index in the database
    index_data = result.index

    new_index = Index(
        name=index_data["name"],
        identifier=index_data["identifier"],
        description=index_data.get("description"),
        currency=index_data.get("currency", "USD"),
        base_date=date.fromisoformat(index_data["base_date"]),
        base_value=index_data.get("base_value", 1000.0),
        owner_id=current_user.id,
        countries=index_data.get("countries", []),
        sectors=index_data.get("sectors", []),
        min_market_cap=index_data.get("min_market_cap"),
        max_components=index_data.get("max_components", 50),
        weighting_method=index_data.get("weighting_method", "market_cap"),
        max_weight=index_data.get("max_weight"),
        rebalance_frequency=index_data.get("rebalance_frequency", "quarterly"),
    )

    db.add(new_index)
    await db.commit()
    await db.refresh(new_index)

    return {
        "id": str(new_index.id),
        "name": new_index.name,
        "identifier": new_index.identifier,
        "explanation": result.explanation,
        "message": "Index created successfully from AI description",
    }


@router.get("/status")
async def get_ai_status() -> dict:
    """Check if AI features are available."""
    gemini_available = bool(settings.GEMINI_API_KEY)
    openai_available = bool(settings.OPENAI_API_KEY)

    return {
        "available": gemini_available or openai_available,
        "provider": "gemini" if gemini_available else ("openai" if openai_available else None),
        "gemini": gemini_available,
        "openai": openai_available,
    }

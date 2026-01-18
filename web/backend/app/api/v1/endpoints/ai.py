"""
AI-powered index creation endpoints.

Uses LLMs (Gemini or OpenAI) to create indices from natural language descriptions.
"""

import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.core.config import settings
from app.models.index import Index
from app.services.llm_service import generate_index_config_from_llm
from app.tasks import generate_and_populate_index_task

logger = logging.getLogger(__name__)

router = APIRouter()


class AIStatusResponse(BaseModel):
    """Response model for AI availability status."""

    available: bool
    provider: str | None


@router.get("/status", response_model=AIStatusResponse)
async def check_ai_status() -> AIStatusResponse:
    """Check if AI service is configured and available."""
    if settings.GEMINI_API_KEY:
        return AIStatusResponse(available=True, provider="gemini")
    elif settings.OPENAI_API_KEY:
        return AIStatusResponse(available=True, provider="openai")
    return AIStatusResponse(available=False, provider=None)


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
    try:
        config = await generate_index_config_from_llm(
            description=request.description,
            base_value=request.base_value,
            base_date=request.base_date,
        )
    except ValueError as e:
        logger.warning(f"AI generation issue: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"AI API call failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI generation failed. Please try again.",
        )

    explanation = config.get("explanation", "Index generated from your description.")

    # Build the index response (matching what the frontend expects)
    # The config returned by service matches the dict structure we need
    # We just ensure it's returned in the 'index' field for compatibility
    index_data = config.copy()

    # Remove some fields from index_data if they are only for config/exp
    if "explanation" in index_data:
        del index_data["explanation"]

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
    Immediately create an index placeholder and trigger background generation.

    This endpoint returns immediately so the user doesn't have to wait for the LLM.
    """
    # Create the index in the database immediately
    # We use a placeholder name/description until the AI updates it
    today = date.today()

    new_index = Index(
        name=f"Building: {request.description[:30]}...",
        identifier="BUILDING",
        description=f"AI generating index from: {request.description}",
        currency="USD",
        base_date=today,
        base_value=request.base_value,
        owner_id=current_user.id,
        status="building",  # Set initial status
        # Other fields will be populated by the background task
    )

    db.add(new_index)
    await db.commit()
    await db.refresh(new_index)

    # Trigger background task for full generation and population
    generate_and_populate_index_task.delay(
        index_id=str(new_index.id),
        user_id=str(current_user.id),
        description=request.description,
        base_value=request.base_value,
        base_date=request.base_date,
    )

    # Return the index data immediately
    return {
        "id": str(new_index.id),
        "name": new_index.name,
        "status": new_index.status,
        "description": new_index.description,
    }

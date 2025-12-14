"""
Authentication endpoints.

Handles user login, registration, token refresh, and password reset.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, Token
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    db: DBSession,
    user_in: UserCreate,
) -> User:
    """
    Register a new user.

    Creates a new user account with email/password authentication.

    Args:
        user_in: User registration data

    Returns:
        Created user

    Raises:
        HTTPException: If email already exists
    """
    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/login", response_model=Token)
async def login(
    db: DBSession,
    login_data: LoginRequest,
) -> Token:
    """
    Login with email and password.

    Returns access and refresh tokens on successful authentication.

    Args:
        login_data: Email and password

    Returns:
        JWT tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    # Create tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    db: DBSession,
    refresh_data: RefreshRequest,
) -> Token:
    """
    Refresh access token using refresh token.

    Args:
        refresh_data: Refresh token

    Returns:
        New JWT tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
    user_id = verify_token(refresh_data.refresh_token, token_type="refresh")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
) -> User:
    """
    Get current user information.

    Returns the authenticated user's profile.
    """
    return current_user


@router.post("/logout")
async def logout() -> dict[str, str]:
    """
    Logout current user.

    Note: JWT tokens are stateless, so this is mainly for client-side cleanup.
    For true token invalidation, consider implementing a token blacklist.
    """
    return {"message": "Successfully logged out"}

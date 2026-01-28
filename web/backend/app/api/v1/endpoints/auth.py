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


@router.post("/forgot-password")
async def forgot_password(
    db: DBSession,
    request: "PasswordResetRequest",
) -> dict[str, str]:
    """
    Request a password reset email.

    Always returns success to prevent email enumeration attacks.
    Rate limited to 3 requests per hour per email.
    """
    from datetime import timedelta

    from app.api.v1.endpoints.support import send_email
    from app.core.config import settings
    from app.models.password_reset import PasswordResetToken, generate_reset_token, hash_token

    # Find user (but don't reveal if they exist)
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user:
        # Check rate limit: max 3 tokens in last hour
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        result = await db.execute(
            select(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id)
            .where(PasswordResetToken.created_at > one_hour_ago)
        )
        recent_tokens = result.scalars().all()

        if len(recent_tokens) < 3:
            # Generate token
            raw_token = generate_reset_token()
            token_hash = hash_token(raw_token)

            # Store token
            reset_token = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
            )
            db.add(reset_token)
            await db.commit()

            # Build reset URL
            frontend_url = "https://www.indexmaker.ai"
            if settings.DEBUG:
                frontend_url = "http://localhost:3000"
            reset_url = f"{frontend_url}/reset-password?token={raw_token}"

            # Send email
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #2563eb;">Reset Your Password</h2>
                <p>Hi{' ' + user.full_name if user.full_name else ''},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <p style="margin: 30px 0;">
                    <a href="{reset_url}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Reset Password
                    </a>
                </p>
                <p style="color: #666; font-size: 14px;">
                    This link will expire in 1 hour. If you didn't request this, you can safely ignore this email.
                </p>
                <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
                <p style="color: #999; font-size: 12px;">IndexMaker - Build custom financial indices</p>
            </body>
            </html>
            """

            text_body = f"""
Reset Your Password

Hi{' ' + user.full_name if user.full_name else ''},

We received a request to reset your password. Click the link below to create a new password:

{reset_url}

This link will expire in 1 hour. If you didn't request this, you can safely ignore this email.

---
IndexMaker - Build custom financial indices
            """

            send_email(
                to_email=user.email,
                subject="Reset your IndexMaker password",
                html_body=html_body,
                text_body=text_body,
            )

    # Always return success (security: don't reveal if email exists)
    return {
        "message": "If an account exists with this email, you will receive a password reset link."
    }


@router.post("/reset-password")
async def reset_password(
    db: DBSession,
    request: "PasswordResetConfirm",
) -> dict[str, str]:
    """
    Reset password using a valid token.

    Validates the token, updates the password, and marks the token as used.
    """
    from app.models.password_reset import PasswordResetToken, hash_token

    # Hash the provided token to compare with stored hash
    token_hash = hash_token(request.token)

    # Find the token
    result = await db.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash)
        .where(PasswordResetToken.used_at.is_(None))
        .where(PasswordResetToken.expires_at > datetime.now(timezone.utc))
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token. Please request a new password reset.",
        )

    # Validate password length
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )

    # Get user and update password
    result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found.",
        )

    # Update password
    user.hashed_password = get_password_hash(request.new_password)

    # Mark token as used
    reset_token.mark_used()

    await db.commit()

    return {"message": "Password reset successfully. You can now log in with your new password."}


# Import schemas at module level for type hints
from app.schemas.auth import PasswordResetConfirm, PasswordResetRequest  # noqa: E402

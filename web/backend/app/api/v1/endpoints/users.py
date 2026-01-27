"""
User management endpoints.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentAdminUser, CurrentUser, DBSession
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: CurrentUser,
) -> User:
    """Get current user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    db: DBSession,
    current_user: CurrentUser,
    user_update: UserUpdate,
) -> User:
    """
    Update current user's profile.

    Can update full_name and password.
    """
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    if user_update.password is not None:
        current_user.hashed_password = get_password_hash(user_update.password)

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/", response_model=list[UserResponse])
async def list_users(
    db: DBSession,
    admin_user: CurrentAdminUser,
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    """
    List all users (admin only).

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    db: DBSession,
    admin_user: CurrentAdminUser,
    user_id: str,
) -> User:
    """Get user by ID (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    db: DBSession,
    admin_user: CurrentAdminUser,
    user_id: str,
) -> None:
    """Delete user by ID (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-deletion
    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    await db.delete(user)
    await db.commit()


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    db: DBSession,
    admin_user: CurrentAdminUser,
    user_id: str,
    user_update: UserUpdate,
) -> User:
    """
    Update any user (admin only).

    Can update role, tier, active status, as well as profile fields.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-demotion or banning
    if user.id == admin_user.id:
        # Check if admin is trying to remove their own admin role or deactivate themselves
        if (user_update.role and user_update.role != "admin") or (user_update.is_active is False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote or deactivate your own admin account",
            )

    update_data = user_update.model_dump(exclude_unset=True)

    # Handle password hashing if included
    if "password" in update_data and update_data["password"]:
        user.hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]

    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user

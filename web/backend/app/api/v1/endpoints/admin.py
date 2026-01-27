"""
Admin dashboard endpoints.
"""

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentAdminUser, DBSession
from app.models.index import Index
from app.models.user import User

router = APIRouter()


@router.get("/stats")
async def get_admin_stats(
    db: DBSession,
    admin_user: CurrentAdminUser,
) -> dict:
    """Get global platform statistics (admin only)."""

    # Total Users
    result_users = await db.execute(select(func.count(User.id)))
    total_users = result_users.scalar() or 0

    # Active Users
    result_active = await db.execute(select(func.count(User.id)).where(User.is_active))
    active_users = result_active.scalar() or 0

    # Total Indices
    result_indices = await db.execute(select(func.count(Index.id)))
    total_indices = result_indices.scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_indices": total_indices,
    }

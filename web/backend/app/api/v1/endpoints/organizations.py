"""
Organization and Team management API endpoints.

Provides endpoints for:
- Organization CRUD
- Team member management
- Project management
- Invitations
- Activity feed
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, get_db
from app.models.organization import (
    Activity,
    ActivityType,
    InvitationStatus,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    OrganizationRole,
    Project,
    ProjectMembership,
    ProjectRole,
)
from app.models.index import Index

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class OrganizationCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    billing_email: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    logo_url: Optional[str]
    tier: str
    created_at: datetime
    member_count: Optional[int] = None
    project_count: Optional[int] = None
    my_role: Optional[str] = None

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: Optional[str]
    role: str
    joined_at: datetime


class ProjectCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_archived: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    color: Optional[str]
    icon: Optional[str]
    is_archived: bool
    created_at: datetime
    index_count: Optional[int] = None
    member_count: Optional[int] = None
    my_role: Optional[str] = None

    class Config:
        from_attributes = True


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = OrganizationRole.MEMBER.value


class InvitationResponse(BaseModel):
    id: str
    email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime


class ActivityResponse(BaseModel):
    id: str
    activity_type: str
    user_id: str
    user_name: Optional[str]
    target_type: Optional[str]
    target_id: Optional[str]
    target_name: Optional[str]
    created_at: datetime
    extra_data: Optional[dict] = None


class ProjectMemberAdd(BaseModel):
    user_id: str
    role: str = ProjectRole.VIEWER.value


# ============================================================================
# Organization Endpoints
# ============================================================================

@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """Create a new organization and make the current user the owner."""
    
    # Check if slug is unique
    existing = await db.execute(
        select(Organization).where(Organization.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization slug already exists",
        )
    
    # Create organization
    org = Organization(
        name=data.name,
        slug=data.slug,
        description=data.description,
    )
    db.add(org)
    await db.flush()
    
    # Add current user as owner
    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=current_user.id,
        role=OrganizationRole.OWNER.value,
    )
    db.add(membership)
    
    # Log activity
    activity = Activity(
        organization_id=org.id,
        user_id=current_user.id,
        activity_type=ActivityType.ORG_CREATED.value,
        target_type="organization",
        target_id=org.id,
        target_name=org.name,
    )
    db.add(activity)
    
    await db.commit()
    await db.refresh(org)
    
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        tier=org.tier,
        created_at=org.created_at,
        member_count=1,
        project_count=0,
        my_role=OrganizationRole.OWNER.value,
    )


@router.get("/", response_model=list[OrganizationResponse])
async def list_my_organizations(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationResponse]:
    """List all organizations the current user belongs to."""
    
    result = await db.execute(
        select(Organization, OrganizationMembership.role)
        .join(OrganizationMembership)
        .where(OrganizationMembership.user_id == current_user.id)
        .options(selectinload(Organization.memberships))
        .options(selectinload(Organization.projects))
    )
    
    orgs = []
    for org, role in result.all():
        orgs.append(OrganizationResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            logo_url=org.logo_url,
            tier=org.tier,
            created_at=org.created_at,
            member_count=len(org.memberships),
            project_count=len([p for p in org.projects if not p.is_archived]),
            my_role=role,
        ))
    
    return orgs


@router.get("/{org_slug}", response_model=OrganizationResponse)
async def get_organization(
    org_slug: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """Get organization details."""
    
    result = await db.execute(
        select(Organization, OrganizationMembership.role)
        .join(OrganizationMembership)
        .where(
            Organization.slug == org_slug,
            OrganizationMembership.user_id == current_user.id,
        )
        .options(selectinload(Organization.memberships))
        .options(selectinload(Organization.projects))
    )
    
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or access denied",
        )
    
    org, role = row
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        tier=org.tier,
        created_at=org.created_at,
        member_count=len(org.memberships),
        project_count=len([p for p in org.projects if not p.is_archived]),
        my_role=role,
    )


@router.patch("/{org_slug}", response_model=OrganizationResponse)
async def update_organization(
    org_slug: str,
    data: OrganizationUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """Update organization (admin/owner only)."""
    
    # Check membership and role
    result = await db.execute(
        select(Organization, OrganizationMembership.role)
        .join(OrganizationMembership)
        .where(
            Organization.slug == org_slug,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org, role = row
    if role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized to update organization")
    
    # Update fields
    if data.name is not None:
        org.name = data.name
    if data.description is not None:
        org.description = data.description
    if data.logo_url is not None:
        org.logo_url = data.logo_url
    if data.billing_email is not None:
        org.billing_email = data.billing_email
    
    # Log activity
    activity = Activity(
        organization_id=org.id,
        user_id=current_user.id,
        activity_type=ActivityType.ORG_UPDATED.value,
        target_type="organization",
        target_id=org.id,
        target_name=org.name,
    )
    db.add(activity)
    
    await db.commit()
    await db.refresh(org)
    
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        logo_url=org.logo_url,
        tier=org.tier,
        created_at=org.created_at,
        my_role=role,
    )


# ============================================================================
# Member Endpoints
# ============================================================================

@router.get("/{org_slug}/members", response_model=list[MemberResponse])
async def list_organization_members(
    org_slug: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[MemberResponse]:
    """List all members of an organization."""
    
    # Verify access
    org_result = await db.execute(
        select(Organization)
        .join(OrganizationMembership)
        .where(
            Organization.slug == org_slug,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Get members
    from app.models.user import User
    result = await db.execute(
        select(OrganizationMembership, User)
        .join(User)
        .where(OrganizationMembership.organization_id == org.id)
    )
    
    members = []
    for membership, user in result.all():
        members.append(MemberResponse(
            id=membership.id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=membership.role,
            joined_at=membership.joined_at,
        ))
    
    return members


@router.post("/{org_slug}/invitations", response_model=InvitationResponse)
async def invite_member(
    org_slug: str,
    data: InvitationCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> InvitationResponse:
    """Invite a new member to the organization."""
    
    # Check membership and role
    result = await db.execute(
        select(Organization, OrganizationMembership.role)
        .join(OrganizationMembership)
        .where(
            Organization.slug == org_slug,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org, role = row
    if role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized to invite members")
    
    # Check if already invited or member
    from app.models.user import User
    existing_user = await db.execute(
        select(User).where(User.email == data.email)
    )
    user = existing_user.scalar_one_or_none()
    
    if user:
        existing_member = await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == org.id,
                OrganizationMembership.user_id == user.id,
            )
        )
        if existing_member.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User is already a member")
    
    # Check for pending invitation
    existing_invite = await db.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.organization_id == org.id,
            OrganizationInvitation.email == data.email,
            OrganizationInvitation.status == InvitationStatus.PENDING.value,
        )
    )
    if existing_invite.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invitation already pending")
    
    # Create invitation
    invitation = OrganizationInvitation(
        organization_id=org.id,
        email=data.email,
        role=data.role,
        token=secrets.token_urlsafe(32),
        invited_by_id=current_user.id,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invitation)
    
    # Log activity
    activity = Activity(
        organization_id=org.id,
        user_id=current_user.id,
        activity_type=ActivityType.INVITATION_SENT.value,
        target_type="invitation",
        target_id=invitation.id,
        target_name=data.email,
    )
    db.add(activity)
    
    await db.commit()
    await db.refresh(invitation)
    
    # TODO: Send invitation email
    
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
    )


@router.get("/{org_slug}/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    org_slug: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
) -> list[InvitationResponse]:
    """List all invitations for an organization."""
    
    # Verify access (admin/owner)
    result = await db.execute(
        select(Organization, OrganizationMembership.role)
        .join(OrganizationMembership)
        .where(
            Organization.slug == org_slug,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org, role = row
    if role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get invitations
    query = select(OrganizationInvitation).where(
        OrganizationInvitation.organization_id == org.id
    )
    if status_filter:
        query = query.where(OrganizationInvitation.status == status_filter)
    
    result = await db.execute(query.order_by(OrganizationInvitation.created_at.desc()))
    
    return [
        InvitationResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role,
            status=inv.status,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in result.scalars().all()
    ]


@router.delete("/{org_slug}/members/{user_id}")
async def remove_member(
    org_slug: str,
    user_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove a member from the organization."""
    
    # Check membership and role
    result = await db.execute(
        select(Organization, OrganizationMembership.role)
        .join(OrganizationMembership)
        .where(
            Organization.slug == org_slug,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org, my_role = row
    
    # Can't remove self if owner
    if user_id == current_user.id and my_role == OrganizationRole.OWNER.value:
        raise HTTPException(status_code=400, detail="Owner cannot remove themselves")
    
    # Only owner/admin can remove others
    if user_id != current_user.id and my_role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="Not authorized to remove members")
    
    # Get target membership
    target_result = await db.execute(
        select(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == org.id,
            OrganizationMembership.user_id == user_id,
        )
    )
    target_membership = target_result.scalar_one_or_none()
    if not target_membership:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Can't remove owner
    if target_membership.role == OrganizationRole.OWNER.value:
        raise HTTPException(status_code=400, detail="Cannot remove organization owner")
    
    # Log activity
    from app.models.user import User
    target_user = await db.execute(select(User).where(User.id == user_id))
    target = target_user.scalar_one_or_none()
    
    activity = Activity(
        organization_id=org.id,
        user_id=current_user.id,
        activity_type=ActivityType.MEMBER_REMOVED.value,
        target_type="user",
        target_id=user_id,
        target_name=target.full_name or target.email if target else None,
    )
    db.add(activity)
    
    await db.delete(target_membership)
    await db.commit()
    
    return {"message": "Member removed successfully"}


# ============================================================================
# Project Endpoints
# ============================================================================

@router.post("/{org_slug}/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    org_slug: str,
    data: ProjectCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new project in the organization."""
    
    # Check membership
    result = await db.execute(
        select(Organization, OrganizationMembership.role)
        .join(OrganizationMembership)
        .where(
            Organization.slug == org_slug,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org, role = row
    if role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value, OrganizationRole.MEMBER.value]:
        raise HTTPException(status_code=403, detail="Not authorized to create projects")
    
    # Check slug uniqueness within org
    existing = await db.execute(
        select(Project).where(
            Project.organization_id == org.id,
            Project.slug == data.slug,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Project slug already exists in this organization")
    
    # Create project
    project = Project(
        organization_id=org.id,
        name=data.name,
        slug=data.slug,
        description=data.description,
        color=data.color,
        icon=data.icon,
        created_by_id=current_user.id,
    )
    db.add(project)
    await db.flush()
    
    # Add creator as project admin
    project_membership = ProjectMembership(
        project_id=project.id,
        user_id=current_user.id,
        role=ProjectRole.ADMIN.value,
        added_by_id=current_user.id,
    )
    db.add(project_membership)
    
    # Log activity
    activity = Activity(
        organization_id=org.id,
        project_id=project.id,
        user_id=current_user.id,
        activity_type=ActivityType.PROJECT_CREATED.value,
        target_type="project",
        target_id=project.id,
        target_name=project.name,
    )
    db.add(activity)
    
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        color=project.color,
        icon=project.icon,
        is_archived=project.is_archived,
        created_at=project.created_at,
        index_count=0,
        member_count=1,
        my_role=ProjectRole.ADMIN.value,
    )


@router.get("/{org_slug}/projects", response_model=list[ProjectResponse])
async def list_projects(
    org_slug: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    include_archived: bool = False,
) -> list[ProjectResponse]:
    """List all projects in the organization that the user has access to."""
    
    # Verify org access
    org_result = await db.execute(
        select(Organization, OrganizationMembership.role)
        .join(OrganizationMembership)
        .where(
            Organization.slug == org_slug,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    
    row = org_result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org, org_role = row
    
    # Org owners/admins see all projects
    if org_role in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
        query = select(Project).where(Project.organization_id == org.id)
        if not include_archived:
            query = query.where(Project.is_archived == False)
        
        result = await db.execute(query.options(
            selectinload(Project.memberships),
            selectinload(Project.indices),
        ))
        projects = result.scalars().all()
        
        return [
            ProjectResponse(
                id=p.id,
                name=p.name,
                slug=p.slug,
                description=p.description,
                color=p.color,
                icon=p.icon,
                is_archived=p.is_archived,
                created_at=p.created_at,
                index_count=len(p.indices),
                member_count=len(p.memberships),
                my_role=ProjectRole.ADMIN.value,
            )
            for p in projects
        ]
    
    # Others only see projects they're members of
    result = await db.execute(
        select(Project, ProjectMembership.role)
        .join(ProjectMembership)
        .where(
            Project.organization_id == org.id,
            ProjectMembership.user_id == current_user.id,
            Project.is_archived == False if not include_archived else True,
        )
        .options(
            selectinload(Project.memberships),
            selectinload(Project.indices),
        )
    )
    
    return [
        ProjectResponse(
            id=project.id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            color=project.color,
            icon=project.icon,
            is_archived=project.is_archived,
            created_at=project.created_at,
            index_count=len(project.indices),
            member_count=len(project.memberships),
            my_role=role,
        )
        for project, role in result.all()
    ]


@router.get("/{org_slug}/projects/{project_slug}", response_model=ProjectResponse)
async def get_project(
    org_slug: str,
    project_slug: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Get project details."""
    
    # Get org and verify access
    org_result = await db.execute(
        select(Organization, OrganizationMembership.role)
        .join(OrganizationMembership)
        .where(
            Organization.slug == org_slug,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    row = org_result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org, org_role = row
    
    # Get project
    project_result = await db.execute(
        select(Project)
        .where(
            Project.organization_id == org.id,
            Project.slug == project_slug,
        )
        .options(
            selectinload(Project.memberships),
            selectinload(Project.indices),
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check project access
    my_role = None
    if org_role in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
        my_role = ProjectRole.ADMIN.value
    else:
        for m in project.memberships:
            if m.user_id == current_user.id:
                my_role = m.role
                break
    
    if not my_role:
        raise HTTPException(status_code=403, detail="Not authorized to view this project")
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        color=project.color,
        icon=project.icon,
        is_archived=project.is_archived,
        created_at=project.created_at,
        index_count=len(project.indices),
        member_count=len(project.memberships),
        my_role=my_role,
    )


@router.post("/{org_slug}/projects/{project_slug}/members", response_model=dict)
async def add_project_member(
    org_slug: str,
    project_slug: str,
    data: ProjectMemberAdd,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add a member to a project."""
    
    # Get org and verify admin access
    org_result = await db.execute(
        select(Organization, OrganizationMembership.role)
        .join(OrganizationMembership)
        .where(
            Organization.slug == org_slug,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    row = org_result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org, org_role = row
    
    # Get project
    project_result = await db.execute(
        select(Project).where(
            Project.organization_id == org.id,
            Project.slug == project_slug,
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if user can add members
    can_add = org_role in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]
    if not can_add:
        project_member = await db.execute(
            select(ProjectMembership).where(
                ProjectMembership.project_id == project.id,
                ProjectMembership.user_id == current_user.id,
                ProjectMembership.role == ProjectRole.ADMIN.value,
            )
        )
        can_add = project_member.scalar_one_or_none() is not None
    
    if not can_add:
        raise HTTPException(status_code=403, detail="Not authorized to add members")
    
    # Verify target user is in the org
    target_member = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org.id,
            OrganizationMembership.user_id == data.user_id,
        )
    )
    if not target_member.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is not a member of this organization")
    
    # Check if already a project member
    existing = await db.execute(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project.id,
            ProjectMembership.user_id == data.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a project member")
    
    # Add membership
    membership = ProjectMembership(
        project_id=project.id,
        user_id=data.user_id,
        role=data.role,
        added_by_id=current_user.id,
    )
    db.add(membership)
    
    # Log activity
    from app.models.user import User
    target_user = await db.execute(select(User).where(User.id == data.user_id))
    target = target_user.scalar_one_or_none()
    
    activity = Activity(
        organization_id=org.id,
        project_id=project.id,
        user_id=current_user.id,
        activity_type=ActivityType.MEMBER_ADDED.value,
        target_type="user",
        target_id=data.user_id,
        target_name=target.full_name or target.email if target else None,
    )
    db.add(activity)
    
    await db.commit()
    
    return {"message": "Member added successfully"}


# ============================================================================
# Activity Feed
# ============================================================================

@router.get("/{org_slug}/activity", response_model=list[ActivityResponse])
async def get_activity_feed(
    org_slug: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, le=100),
    project_slug: Optional[str] = None,
) -> list[ActivityResponse]:
    """Get the activity feed for an organization or project."""
    
    # Verify org access
    org_result = await db.execute(
        select(Organization)
        .join(OrganizationMembership)
        .where(
            Organization.slug == org_slug,
            OrganizationMembership.user_id == current_user.id,
        )
    )
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Build query
    from app.models.user import User
    query = (
        select(Activity, User)
        .join(User)
        .where(Activity.organization_id == org.id)
    )
    
    if project_slug:
        project_result = await db.execute(
            select(Project).where(
                Project.organization_id == org.id,
                Project.slug == project_slug,
            )
        )
        project = project_result.scalar_one_or_none()
        if project:
            query = query.where(Activity.project_id == project.id)
    
    query = query.order_by(Activity.created_at.desc()).limit(limit)
    result = await db.execute(query)
    
    return [
        ActivityResponse(
            id=activity.id,
            activity_type=activity.activity_type,
            user_id=activity.user_id,
            user_name=user.full_name or user.email,
            target_type=activity.target_type,
            target_id=activity.target_id,
            target_name=activity.target_name,
            created_at=activity.created_at,
            extra_data=activity.extra_data,
        )
        for activity, user in result.all()
    ]


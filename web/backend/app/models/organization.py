"""
Organization and Team models for collaborative workflows.

This module provides the foundation for team-based index management:
- Organizations: Top-level entity for companies/teams
- Projects: Workspaces within organizations for grouping indices
- Memberships: User access and roles within orgs/projects
- Activity: Audit trail of all changes
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.index import Index


class OrganizationRole(str, Enum):
    """Roles within an organization."""
    OWNER = "owner"          # Full control, can delete org
    ADMIN = "admin"          # Manage members, projects
    MEMBER = "member"        # Create/edit in allowed projects
    VIEWER = "viewer"        # Read-only access


class ProjectRole(str, Enum):
    """Roles within a project."""
    ADMIN = "admin"          # Full control of project
    EDITOR = "editor"        # Create and edit indices
    REVIEWER = "reviewer"    # Review and approve changes
    VIEWER = "viewer"        # Read-only access


class InvitationStatus(str, Enum):
    """Status of an invitation."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class ActivityType(str, Enum):
    """Types of activities for audit trail."""
    # Index activities
    INDEX_CREATED = "index_created"
    INDEX_UPDATED = "index_updated"
    INDEX_DELETED = "index_deleted"
    INDEX_PUBLISHED = "index_published"
    COMPONENT_ADDED = "component_added"
    COMPONENT_REMOVED = "component_removed"
    REBALANCING_RUN = "rebalancing_run"
    # Project activities
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"
    MEMBER_ROLE_CHANGED = "member_role_changed"
    # Organization activities
    ORG_CREATED = "org_created"
    ORG_UPDATED = "org_updated"
    INVITATION_SENT = "invitation_sent"
    INVITATION_ACCEPTED = "invitation_accepted"


class Organization(Base):
    """
    Organization represents a company or team.
    
    Organizations are the top-level entity for billing and 
    can contain multiple projects and members.
    """
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Billing
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tier: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    
    # Settings
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[list["OrganizationInvitation"]] = relationship(
        "OrganizationInvitation",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    activities: Mapped[list["Activity"]] = relationship(
        "Activity",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization {self.name}>"


class OrganizationMembership(Base):
    """
    Membership linking users to organizations with roles.
    """
    __tablename__ = "organization_memberships"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default=OrganizationRole.MEMBER.value,
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="memberships",
    )
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<OrgMembership {self.user_id} in {self.organization_id}>"


class Project(Base):
    """
    Project is a workspace within an organization for grouping related indices.
    
    Examples: "Q1 2025 Indices", "ESG Portfolio", "Client ABC Indices"
    """
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)  # For UI
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)   # Emoji or icon name
    
    # Settings
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="projects",
    )
    memberships: Mapped[list["ProjectMembership"]] = relationship(
        "ProjectMembership",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    indices: Mapped[list["Index"]] = relationship(
        "Index",
        back_populates="project",
    )
    created_by: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<Project {self.name}>"


class ProjectMembership(Base):
    """
    Membership linking users to specific projects with roles.
    
    Users can have different roles in different projects within the same org.
    """
    __tablename__ = "project_memberships"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default=ProjectRole.VIEWER.value,
        nullable=False,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    added_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="memberships",
    )
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    added_by: Mapped["User"] = relationship("User", foreign_keys=[added_by_id])

    def __repr__(self) -> str:
        return f"<ProjectMembership {self.user_id} in {self.project_id}>"


class OrganizationInvitation(Base):
    """
    Invitation to join an organization.
    """
    __tablename__ = "organization_invitations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50),
        default=OrganizationRole.MEMBER.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=InvitationStatus.PENDING.value,
        nullable=False,
    )
    token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    invited_by_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="invitations",
    )
    invited_by: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<Invitation {self.email} to {self.organization_id}>"


class Activity(Base):
    """
    Activity log for audit trail and activity feed.
    
    Records all significant actions within an organization.
    """
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Target of the activity (e.g., index_id, user_id that was affected)
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Additional data about the activity
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="activities",
    )
    project: Mapped["Project"] = relationship("Project")
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<Activity {self.activity_type} by {self.user_id}>"


class Comment(Base):
    """
    Comments on indices for team discussions.
    """
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    index_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("indices.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    index: Mapped["Index"] = relationship("Index")
    user: Mapped["User"] = relationship("User")
    replies: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    parent: Mapped["Comment"] = relationship(
        "Comment",
        back_populates="replies",
        remote_side=[id],
    )

    def __repr__(self) -> str:
        return f"<Comment {self.id} on {self.index_id}>"


"""
Database models for IndexMaker.
"""

from app.models.backtest import Backtest, BacktestResult
from app.models.corporate_action import CorporateAction, IndexCorporateActionLog
from app.models.data_source import CustomDataSource, CustomSecurity
from app.models.delivery import (
    DeliveryLog,
    EmailSubscription,
    SFTPDestination,
    WebhookEndpoint,
)
from app.models.embed import EmbedWidget, PublicShare
from app.models.index import Index, IndexComponent, IndexSnapshot
from app.models.organization import (
    Activity,
    Comment,
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    Project,
    ProjectMembership,
)
from app.models.report import GeneratedReport, ReportTemplate
from app.models.user import User

__all__ = [
    # Users
    "User",
    # Organizations & Teams
    "Organization",
    "OrganizationMembership",
    "OrganizationInvitation",
    "Project",
    "ProjectMembership",
    "Activity",
    "Comment",
    # Indices
    "Index",
    "IndexComponent",
    "IndexSnapshot",
    # Backtests
    "Backtest",
    "BacktestResult",
    # Data Sources
    "CustomDataSource",
    "CustomSecurity",
    # Corporate Actions
    "CorporateAction",
    "IndexCorporateActionLog",
    # Delivery
    "WebhookEndpoint",
    "SFTPDestination",
    "EmailSubscription",
    "DeliveryLog",
    # Sharing
    "PublicShare",
    "EmbedWidget",
    # Reports
    "ReportTemplate",
    "GeneratedReport",
]

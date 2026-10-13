"""
Company details kept between index builds.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CompanyDetail(Base):
    """
    What a data source said about one company: name, country, sector, description.

    These change rarely, but sources hand them out one company per request and
    limit the requests they accept, so a build that screens a few thousand
    companies cannot ask for all of them every time. Sizes and prices are not
    read from here; they come fresh with each screen.

    A row with `wanted_at` set and no `data` is a company a build needed and
    could not fetch; the scheduled job fetches those first.
    """

    __tablename__ = "company_details"

    source: Mapped[str] = mapped_column(String(60), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(40), primary_key=True)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wanted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_company_details_source_wanted", "source", "wanted_at"),
        Index("ix_company_details_source_fetched", "source", "fetched_at"),
    )

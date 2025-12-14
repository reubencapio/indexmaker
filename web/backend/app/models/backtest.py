"""
Backtest models for strategy validation.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.index import Index


class BacktestStatus(str, Enum):
    """Backtest job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Backtest(Base):
    """
    Backtest configuration and results.

    Stores the parameters and outcome of historical strategy testing.
    """

    __tablename__ = "backtests"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    index_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("indices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Configuration
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    initial_value: Mapped[float] = mapped_column(Float, default=10000.0)
    benchmark_ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default=BacktestStatus.PENDING.value,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100

    # Results summary
    final_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    annualized_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    benchmark_return: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Detailed results (JSON)
    daily_values: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)
    monthly_returns: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)
    drawdown_series: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)
    benchmark_values: Mapped[dict[str, float] | None] = mapped_column(JSON, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    index: Mapped["Index"] = relationship("Index", back_populates="backtests")
    results: Mapped[list["BacktestResult"]] = relationship(
        "BacktestResult",
        back_populates="backtest",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Backtest {self.name}: {self.status}>"


class BacktestResult(Base):
    """
    Detailed daily backtest results.

    Stores granular data for visualization and analysis.
    """

    __tablename__ = "backtest_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    backtest_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("backtests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Daily data
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    portfolio_value: Mapped[float] = mapped_column(Float, nullable=False)
    daily_return: Mapped[float] = mapped_column(Float, default=0.0)
    cumulative_return: Mapped[float] = mapped_column(Float, default=0.0)
    drawdown: Mapped[float] = mapped_column(Float, default=0.0)

    # Benchmark comparison
    benchmark_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    benchmark_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    excess_return: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Component data at this date
    holdings: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    backtest: Mapped["Backtest"] = relationship("Backtest", back_populates="results")

    def __repr__(self) -> str:
        return f"<BacktestResult {self.date.date()}: {self.portfolio_value:.2f}>"


"""
Backtest schemas for API validation.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class BacktestCreate(BaseModel):
    """Schema for creating a backtest."""

    name: str = Field(..., min_length=3, max_length=255)
    start_date: datetime
    end_date: datetime
    initial_value: float = Field(default=10000.0, gt=0)
    benchmark_ticker: str | None = Field(default="SPY", max_length=20)

    # Enhanced options
    include_dividends: bool = Field(default=True)
    rebalance_on_schedule: bool = Field(default=True)
    apply_corporate_actions: bool = Field(default=True)

    # Monte Carlo simulation
    run_monte_carlo: bool = Field(default=False)
    monte_carlo_simulations: int = Field(default=1000, ge=100, le=10000)
    monte_carlo_horizon_days: int = Field(default=252, ge=21, le=1260)

    # Stress testing
    run_stress_test: bool = Field(default=False)
    stress_scenarios: list[str] | None = Field(
        default=None
    )  # e.g., ["2008_crisis", "covid_crash", "custom"]


class BacktestSummary(BaseModel):
    """Summary statistics for a backtest."""

    total_return: float | None
    annualized_return: float | None
    volatility: float | None
    sharpe_ratio: float | None
    max_drawdown: float | None
    benchmark_return: float | None
    alpha: float | None = None
    beta: float | None = None

    # Enhanced metrics
    sortino_ratio: float | None = None
    calmar_ratio: float | None = None
    information_ratio: float | None = None
    treynor_ratio: float | None = None

    # Drawdown analysis
    max_drawdown_duration_days: int | None = None
    avg_drawdown: float | None = None
    avg_drawdown_duration_days: int | None = None

    # Risk metrics
    var_95: float | None = None  # Value at Risk (95%)
    var_99: float | None = None  # Value at Risk (99%)
    cvar_95: float | None = None  # Conditional VaR (Expected Shortfall)

    # Return distribution
    skewness: float | None = None
    kurtosis: float | None = None
    best_day: float | None = None
    worst_day: float | None = None
    positive_days_pct: float | None = None


class MonteCarloResult(BaseModel):
    """Monte Carlo simulation results."""

    simulations_run: int
    horizon_days: int

    # Percentile outcomes
    percentile_5: float  # 5th percentile final value
    percentile_25: float
    percentile_50: float  # Median
    percentile_75: float
    percentile_95: float

    # Probability analysis
    prob_positive_return: float  # Probability of positive return
    prob_beat_benchmark: float | None  # Probability of beating benchmark
    prob_loss_10pct: float  # Probability of 10% loss
    prob_loss_20pct: float  # Probability of 20% loss

    # Expected values
    expected_final_value: float
    expected_return: float
    expected_volatility: float


class StressTestResult(BaseModel):
    """Stress test scenario result."""

    scenario_name: str
    scenario_description: str
    start_date: str
    end_date: str

    # Impact
    portfolio_return: float
    benchmark_return: float | None
    max_drawdown: float
    recovery_days: int | None


class EnhancedBacktestResponse(BaseModel):
    """Extended backtest response with advanced analytics."""

    id: str
    index_id: str
    name: str
    start_date: datetime
    end_date: datetime
    initial_value: float
    benchmark_ticker: str | None

    # Status
    status: str
    error_message: str | None
    progress: float

    # Basic results
    final_value: float | None
    total_return: float | None
    annualized_return: float | None
    volatility: float | None
    sharpe_ratio: float | None
    max_drawdown: float | None
    benchmark_return: float | None

    # Enhanced metrics
    sortino_ratio: float | None = None
    calmar_ratio: float | None = None
    alpha: float | None = None
    beta: float | None = None
    var_95: float | None = None
    cvar_95: float | None = None

    # Time series
    daily_values: dict[str, float] | None
    benchmark_values: dict[str, float] | None
    drawdown_series: dict[str, float] | None
    rolling_sharpe: dict[str, float] | None = None
    rolling_volatility: dict[str, float] | None = None

    # Monte Carlo results
    monte_carlo: MonteCarloResult | None = None

    # Stress test results
    stress_tests: list[StressTestResult] | None = None

    # Monthly returns table
    monthly_returns: dict[str, dict[str, float]] | None = None  # {year: {month: return}}

    # Metadata
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class BacktestResultResponse(BaseModel):
    """Schema for daily backtest result."""

    date: datetime
    portfolio_value: float
    daily_return: float
    cumulative_return: float
    drawdown: float
    benchmark_value: float | None
    benchmark_return: float | None
    excess_return: float | None

    class Config:
        from_attributes = True


class BacktestResponse(BaseModel):
    """Schema for backtest response."""

    id: str
    index_id: str
    name: str
    start_date: datetime
    end_date: datetime
    initial_value: float
    benchmark_ticker: str | None

    # Status
    status: str
    error_message: str | None
    progress: float

    # Results
    final_value: float | None
    total_return: float | None
    annualized_return: float | None
    volatility: float | None
    sharpe_ratio: float | None
    max_drawdown: float | None
    benchmark_return: float | None

    # Time series (for charts)
    daily_values: dict[str, float] | None
    benchmark_values: dict[str, float] | None
    drawdown_series: dict[str, float] | None

    # Metadata
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class BacktestListResponse(BaseModel):
    """Schema for backtest list item."""

    id: str
    index_id: str
    name: str
    status: str
    total_return: float | None
    sharpe_ratio: float | None
    created_at: datetime

    class Config:
        from_attributes = True

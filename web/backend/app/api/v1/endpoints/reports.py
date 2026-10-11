"""
Reports and Factsheets API endpoints.
"""

import io
import secrets
from datetime import datetime, timezone
from html import escape
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.models.index import Index
from app.models.report import GeneratedReport, ReportStatus, ReportTemplate
from app.schemas.report import (
    GeneratedReportResponse,
    GenerateReportRequest,
    ReportTemplateCreate,
    ReportTemplateResponse,
    ReportTemplateUpdate,
)
from app.services import analytics_service
from app.services.analytics_service import AnalyticsUnavailableError

router = APIRouter()


# ============== REPORT TEMPLATES ==============


@router.get("/templates", response_model=list[ReportTemplateResponse])
async def list_report_templates(
    db: DBSession,
    current_user: CurrentUser,
    include_system: bool = Query(default=True),
) -> list[ReportTemplate]:
    """List report templates (user's own + system templates)."""
    query = (
        select(ReportTemplate)
        .where(
            (ReportTemplate.owner_id == current_user.id)
            | (ReportTemplate.is_system_template.is_(True) if include_system else False)
        )
        .order_by(ReportTemplate.name)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post(
    "/templates", response_model=ReportTemplateResponse, status_code=status.HTTP_201_CREATED
)
async def create_report_template(
    db: DBSession,
    current_user: CurrentUser,
    template_in: ReportTemplateCreate,
) -> ReportTemplate:
    """Create a new report template."""
    template = ReportTemplate(
        owner_id=current_user.id,
        name=template_in.name,
        description=template_in.description,
        report_type=template_in.report_type,
        show_logo=template_in.show_logo,
        logo_url=template_in.logo_url,
        header_text=template_in.header_text,
        footer_text=template_in.footer_text,
        sections=template_in.sections
        or {
            "summary": True,
            "performance_chart": True,
            "performance_table": True,
            "risk_metrics": True,
            "top_components": True,
            "all_components": False,
            "sector_breakdown": True,
            "country_breakdown": True,
            "methodology": True,
            "disclaimer": True,
        },
        primary_color=template_in.primary_color,
        secondary_color=template_in.secondary_color,
        font_family=template_in.font_family,
        custom_css=template_in.custom_css,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("/templates/{template_id}", response_model=ReportTemplateResponse)
async def get_report_template(
    db: DBSession,
    current_user: CurrentUser,
    template_id: str,
) -> ReportTemplate:
    """Get a specific report template."""
    result = await db.execute(select(ReportTemplate).where(ReportTemplate.id == template_id))
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if not template.is_system_template and template.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return template


@router.patch("/templates/{template_id}", response_model=ReportTemplateResponse)
async def update_report_template(
    db: DBSession,
    current_user: CurrentUser,
    template_id: str,
    template_in: ReportTemplateUpdate,
) -> ReportTemplate:
    """Update a report template."""
    result = await db.execute(select(ReportTemplate).where(ReportTemplate.id == template_id))
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.is_system_template:
        raise HTTPException(status_code=403, detail="Cannot modify system templates")
    if template.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = template_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_template(
    db: DBSession,
    current_user: CurrentUser,
    template_id: str,
) -> None:
    """Delete a report template."""
    result = await db.execute(select(ReportTemplate).where(ReportTemplate.id == template_id))
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.is_system_template:
        raise HTTPException(status_code=403, detail="Cannot delete system templates")
    if template.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(template)
    await db.commit()


# ============== GENERATED REPORTS ==============


@router.get("/", response_model=list[GeneratedReportResponse])
async def list_generated_reports(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
) -> list[GeneratedReport]:
    """List generated reports for the current user."""
    query = (
        select(GeneratedReport)
        .where(GeneratedReport.owner_id == current_user.id)
        .order_by(GeneratedReport.created_at.desc())
        .limit(limit)
    )

    if index_id:
        query = query.where(GeneratedReport.index_id == index_id)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post(
    "/generate", response_model=GeneratedReportResponse, status_code=status.HTTP_202_ACCEPTED
)
async def generate_report(
    db: DBSession,
    current_user: CurrentUser,
    report_in: GenerateReportRequest,
) -> GeneratedReport:
    """
    Generate a new report for an index.

    The report is generated asynchronously via Celery.
    Poll the report status to check when it's complete.
    """
    # Verify index ownership
    result = await db.execute(
        select(Index).where(Index.id == report_in.index_id).options(selectinload(Index.components))
    )
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(status_code=404, detail="Index not found")
    if index.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Create report record
    report = GeneratedReport(
        index_id=report_in.index_id,
        owner_id=current_user.id,
        template_id=report_in.template_id,
        report_type=report_in.report_type,
        # HTML is the only format produced, so it is the only one recorded.
        report_format="html",
        as_of_date=report_in.as_of_date or datetime.now(timezone.utc),
        period_start=report_in.period_start,
        period_end=report_in.period_end,
        is_public=report_in.is_public,
        public_token=secrets.token_urlsafe(32) if report_in.is_public else None,
        status=ReportStatus.PENDING.value,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Run task (sync in dev, async via Celery in production)
    from app.core.task_runner import run_task_async
    from app.tasks import generate_report_async, generate_report_task

    await run_task_async(generate_report_task, generate_report_async, str(report.id))

    return report


@router.get("/{report_id}", response_model=GeneratedReportResponse)
async def get_report(
    db: DBSession,
    current_user: CurrentUser,
    report_id: str,
) -> GeneratedReport:
    """Get a specific generated report."""
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return report


@router.get("/{report_id}/download")
async def download_report(
    db: DBSession,
    current_user: CurrentUser,
    report_id: str,
) -> StreamingResponse:
    """Download a generated report file."""
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if report.status != ReportStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Report not ready")

    # For now, generate a simple HTML report on-the-fly
    # In production, this would read from stored file
    html_content = await generate_html_report(db, report)

    # Update download count
    report.download_count += 1
    await db.commit()

    # Reports are rendered as HTML. Serving that under a PDF or spreadsheet
    # content type produced files nothing could open.
    filename = f"report_{report.id[:8]}.html"

    return StreamingResponse(
        io.BytesIO(html_content.encode()),
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    db: DBSession,
    current_user: CurrentUser,
    report_id: str,
) -> None:
    """Delete a generated report."""
    result = await db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id))
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(report)
    await db.commit()


# ============== QUICK GENERATE (INSTANT FACTSHEET) ==============


@router.get("/quick/{index_id}")
async def quick_factsheet(
    db: DBSession,
    current_user: CurrentUser,
    index_id: str,
    format: str = Query(default="html", pattern=r"^(html|json)$"),
) -> Any:
    """
    Generate an instant factsheet for an index.

    Returns HTML or JSON immediately (no file storage).
    """
    result = await db.execute(
        select(Index)
        .where(Index.id == index_id)
        .options(
            selectinload(Index.components),
            selectinload(Index.snapshots),
        )
    )
    index = result.scalar_one_or_none()

    if not index:
        raise HTTPException(status_code=404, detail="Index not found")
    if index.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Calculate metrics
    metrics = await calculate_performance_metrics(index)

    if format == "json":
        return {
            "index": {
                "id": index.id,
                "name": index.name,
                "identifier": index.identifier,
                "description": index.description,
                "currency": index.currency,
                "current_value": index.current_value,
                "base_value": index.base_value,
                "base_date": index.base_date.isoformat() if index.base_date else None,
                "weighting_method": index.weighting_method,
                "component_count": len([c for c in index.components if c.is_active]),
            },
            "metrics": metrics,
            "top_components": [
                {
                    "ticker": c.ticker,
                    "name": c.name,
                    "weight": c.weight,
                    "sector": c.sector,
                }
                for c in sorted(
                    [c for c in index.components if c.is_active],
                    key=lambda x: x.weight,
                    reverse=True,
                )[:10]
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Generate HTML factsheet
    html = generate_factsheet_html(index, metrics)
    return StreamingResponse(
        io.BytesIO(html.encode()),
        media_type="text/html",
    )


FACTSHEET_PERIOD = "1Y"


async def calculate_performance_metrics(index: Index) -> dict[str, Any]:
    """
    Factsheet figures for the trailing year, from daily constituent prices.

    Uses the same calculation as the analytics page, so a factsheet and the
    screen it was generated from always agree. Values are percentages; any that
    cannot be computed are None and print as "n/a" -- a factsheet must never show
    a fabricated zero as though it were a measured result.
    """
    metrics: dict[str, Any] = {
        "current_value": index.current_value or index.base_value,
        "period": FACTSHEET_PERIOD,
        "as_of": None,
        "total_return": None,
        "annualized_return": None,
        "volatility": None,
        "sharpe_ratio": None,
        "max_drawdown": None,
        "ytd_return": None,
    }
    try:
        analytics = await analytics_service.compute_index_analytics(index, FACTSHEET_PERIOD)
    except AnalyticsUnavailableError:
        return metrics

    stats = analytics["stats"]

    def pct(value: float | None) -> float | None:
        return None if value is None else round(value * 100, 2)

    sharpe = stats["sharpe_ratio"]
    metrics.update(
        as_of=analytics["as_of"],
        total_return=pct(stats["total_return"]),
        annualized_return=pct(stats["annualized_return"]),
        volatility=pct(stats["volatility"]),
        sharpe_ratio=None if sharpe is None else round(sharpe, 2),
        max_drawdown=pct(stats["max_drawdown"]),
        ytd_return=pct(analytics["trailing_returns"].get("YTD")),
    )
    return metrics


def _fmt(value: float | None, spec: str, suffix: str = "") -> str:
    return "n/a" if value is None else f"{value:{spec}}{suffix}"


def generate_factsheet_html(index: Index, metrics: dict[str, Any]) -> str:
    """Generate HTML factsheet for an index."""
    active_components = [c for c in index.components if c.is_active]
    top_10 = sorted(active_components, key=lambda x: x.weight, reverse=True)[:10]

    # Sector breakdown
    sectors = {}
    for c in active_components:
        sector = c.sector or "Unknown"
        sectors[sector] = sectors.get(sector, 0) + c.weight

    sector_rows = "\n".join(
        [
            f"<tr><td>{escape(sector)}</td><td>{weight*100:.1f}%</td></tr>"
            for sector, weight in sorted(sectors.items(), key=lambda x: x[1], reverse=True)
        ]
    )

    component_rows = "\n".join(
        [
            f"<tr><td>{escape(c.ticker)}</td><td>{escape(c.name or '-')}</td><td>{c.weight*100:.2f}%</td></tr>"
            for c in top_10
        ]
    )

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{escape(index.name)} - Factsheet</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', -apple-system, sans-serif; color: #1a1a1a; line-height: 1.6; background: #f8fafc; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 40px 20px; }}
        .header {{ background: linear-gradient(135deg, #1a56db 0%, #3b82f6 100%); color: white; padding: 40px; border-radius: 16px; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 8px; }}
        .header .identifier {{ opacity: 0.8; font-size: 1.1rem; }}
        .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .card h2 {{ font-size: 1.25rem; margin-bottom: 16px; color: #374151; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; }}
        .metric {{ text-align: center; padding: 16px; background: #f8fafc; border-radius: 8px; }}
        .metric-value {{ font-size: 1.75rem; font-weight: 700; color: #1a56db; }}
        .metric-label {{ font-size: 0.875rem; color: #6b7280; margin-top: 4px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f8fafc; font-weight: 600; color: #374151; }}
        .footer {{ text-align: center; color: #9ca3af; font-size: 0.875rem; margin-top: 40px; }}
        .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        @media (max-width: 640px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{escape(index.name)}</h1>
            <div class="identifier">{escape(index.identifier)} • {escape(index.currency)}</div>
        </div>

        <div class="card">
            <h2>Performance Summary</h2>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{metrics['current_value']:,.2f}</div>
                    <div class="metric-label">Index Level</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{_fmt(metrics['total_return'], '+.2f', '%')}</div>
                    <div class="metric-label">1-Year Return</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{_fmt(metrics['volatility'], '.2f', '%')}</div>
                    <div class="metric-label">Volatility (Ann.)</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{_fmt(metrics['sharpe_ratio'], '.2f')}</div>
                    <div class="metric-label">Sharpe Ratio</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{_fmt(metrics['max_drawdown'], '.2f', '%')}</div>
                    <div class="metric-label">Max Drawdown</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{len(active_components)}</div>
                    <div class="metric-label">Components</div>
                </div>
            </div>
        </div>

        <div class="two-col">
            <div class="card">
                <h2>Top 10 Holdings</h2>
                <table>
                    <thead><tr><th>Ticker</th><th>Name</th><th>Weight</th></tr></thead>
                    <tbody>{component_rows}</tbody>
                </table>
            </div>

            <div class="card">
                <h2>Sector Breakdown</h2>
                <table>
                    <thead><tr><th>Sector</th><th>Weight</th></tr></thead>
                    <tbody>{sector_rows}</tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <h2>Index Methodology</h2>
            <p><strong>Weighting:</strong> {index.weighting_method.replace('_', ' ').title()}</p>
            <p><strong>Rebalancing:</strong> {index.rebalance_frequency.replace('_', ' ').title()}</p>
            <p><strong>Base Date:</strong> {index.base_date.strftime('%B %d, %Y') if index.base_date else 'N/A'}</p>
            <p><strong>Base Value:</strong> {index.base_value:,.2f}</p>
        </div>

        <div class="footer">
            <p>Generated by IndexMaker • {datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')}</p>
            <p style="margin-top: 8px; font-size: 0.75rem;">
                Performance figures cover the trailing year and show the current constituents at
                current share counts; they are hypothetical and do not include past rebalances or
                trading costs. Past performance is not a guide to future results. This factsheet is
                for informational purposes only and does not constitute investment advice.
            </p>
        </div>
    </div>
</body>
</html>
"""
    return html


async def generate_html_report(db, report: GeneratedReport) -> str:
    """Generate HTML content for a report."""
    result = await db.execute(
        select(Index)
        .where(Index.id == report.index_id)
        .options(
            selectinload(Index.components),
            selectinload(Index.snapshots),
        )
    )
    index = result.scalar_one_or_none()

    if not index:
        return "<html><body><h1>Error: Index not found</h1></body></html>"

    metrics = await calculate_performance_metrics(index)
    return generate_factsheet_html(index, metrics)

"""
Index specs: the single definition of how an index is built.

An index used to be whatever list of tickers the AI happened to return, with
rules shown beside it that nothing applied. Now every index has a spec -- the
indexforge format -- and its members are whatever the library produces from
that spec. The AI's only job is to translate a sentence into a spec.

Keeping the spec and the market data each build used means anyone can take the
two files and reproduce the index with the open-source command line tool.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from indexforge import BuildResult, build
from indexforge.core.types import Country, Sector
from indexforge.data.connectors.base import DataConnector
from indexforge.spec import validate_spec
from sqlalchemy.orm import Session

from app.models.index import Index, IndexComponent

logger = logging.getLogger(__name__)

YAHOO = "yahoo"
OPENBB = "openbb"
DEFAULT_SOURCE = YAHOO

#: Smallest company a screen considers when the request names no size, in the
#: index currency. A screen has to be bounded or it walks every listed stock.
DEFAULT_SCREEN_MIN_MARKET_CAP = 1_000_000_000

#: Where a screen looks when the request names no country.
DEFAULT_SCREEN_COUNTRIES = ["United States"]

_COUNTRY_CODES = {
    "US": Country.UNITED_STATES,
    "USA": Country.UNITED_STATES,
    "GB": Country.UNITED_KINGDOM,
    "UK": Country.UNITED_KINGDOM,
    "CA": Country.CANADA,
    "MX": Country.MEXICO,
    "AT": Country.AUSTRIA,
    "BE": Country.BELGIUM,
    "DK": Country.DENMARK,
    "FI": Country.FINLAND,
    "FR": Country.FRANCE,
    "DE": Country.GERMANY,
    "GR": Country.GREECE,
    "IE": Country.IRELAND,
    "IT": Country.ITALY,
    "LU": Country.LUXEMBOURG,
    "NL": Country.NETHERLANDS,
    "NO": Country.NORWAY,
    "PT": Country.PORTUGAL,
    "ES": Country.SPAIN,
    "SE": Country.SWEDEN,
    "CH": Country.SWITZERLAND,
    "CZ": Country.CZECH_REPUBLIC,
    "HU": Country.HUNGARY,
    "PL": Country.POLAND,
    "TR": Country.TURKEY,
    "AU": Country.AUSTRALIA,
    "HK": Country.HONG_KONG,
    "JP": Country.JAPAN,
    "NZ": Country.NEW_ZEALAND,
    "SG": Country.SINGAPORE,
    "CN": Country.CHINA,
    "IN": Country.INDIA,
    "ID": Country.INDONESIA,
    "MY": Country.MALAYSIA,
    "PH": Country.PHILIPPINES,
    "KR": Country.SOUTH_KOREA,
    "TW": Country.TAIWAN,
    "TH": Country.THAILAND,
    "AR": Country.ARGENTINA,
    "BR": Country.BRAZIL,
    "CL": Country.CHILE,
    "CO": Country.COLOMBIA,
    "IL": Country.ISRAEL,
    "SA": Country.SAUDI_ARABIA,
    "ZA": Country.SOUTH_AFRICA,
    "AE": Country.UNITED_ARAB_EMIRATES,
}


class BuildError(ValueError):
    """A build could not produce an index. The message is written for the user."""


def _country(value: str) -> str | None:
    """Library country name for an ISO code, enum name or country name."""
    text = value.strip()
    if text.upper() in _COUNTRY_CODES:
        return _COUNTRY_CODES[text.upper()].value
    for member in Country:
        if text.lower() == member.value.lower() or text.upper().replace(" ", "_") == member.name:
            return member.value
    return None


def _sector(value: str) -> str | None:
    """Library sector name for an enum name ("HEALTH_CARE") or sector name."""
    text = value.strip()
    for member in Sector:
        if text.lower() == member.value.lower() or text.upper().replace(" ", "_") == member.name:
            return member.value
    return None


def _known(values: list[str] | None, convert: Any, kind: str) -> list[str]:
    """Convert each value, dropping (and logging) the ones that do not map."""
    result: list[str] = []
    for value in values or []:
        mapped = convert(value) if isinstance(value, str) else None
        if mapped is None:
            logger.warning("Ignoring unrecognised %s %r in an index configuration", kind, value)
        elif mapped not in result:
            result.append(mapped)
    return result


def spec_from_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    Turn an interpreted request into an indexforge spec.

    If the request names specific companies, they are the universe and nothing
    is filtered out of it. Otherwise the universe is a screen: the rules find
    the companies, so the result does not depend on anyone's recollection of
    which companies exist.

    Raises:
        indexforge.SpecError: If the configuration cannot form a valid spec
    """
    tickers: list[str] = []
    for ticker in config.get("tickers") or []:
        symbol = str(ticker).strip().upper()
        if symbol and symbol not in tickers:
            tickers.append(symbol)

    universe: dict[str, Any]
    if tickers:
        universe = {"tickers": tickers}
    else:
        universe = {
            "screen": True,
            "countries": _known(config.get("countries"), _country, "country")
            or DEFAULT_SCREEN_COUNTRIES,
            "min_market_cap": config.get("min_market_cap") or DEFAULT_SCREEN_MIN_MARKET_CAP,
        }
        sectors = _known(config.get("sectors"), _sector, "sector")
        if sectors:
            universe["sectors"] = sectors

    selection: dict[str, Any] = {"rank_by": "MARKET_CAP"}
    if config.get("max_components"):
        selection["top"] = int(config["max_components"])
    if not tickers and config.get("theme_keywords"):
        selection["theme_keywords"] = [str(k) for k in config["theme_keywords"]]
    min_yield = (config.get("custom_rules") or {}).get("min_dividend_yield")
    if min_yield:
        selection["min_dividend_yield"] = float(min_yield)

    method = config.get("weighting_method") or "equal_weight"
    weighting: dict[str, Any] = {"method": method}
    if method != "equal_weight" and config.get("max_weight"):
        weighting["max_weight"] = float(config["max_weight"])

    spec: dict[str, Any] = {
        "spec_version": 1,
        "name": config.get("name") or "Custom Index",
        "identifier": config.get("identifier") or "CUSTOM",
        "currency": config.get("currency") or "USD",
        "base_date": str(config.get("base_date") or date.today().isoformat()),
        "base_value": config.get("base_value") or 1000,
        "universe": universe,
        "selection": selection,
        "weighting": weighting,
        "rebalancing": {"frequency": config.get("rebalance_frequency") or "quarterly"},
    }
    if config.get("description"):
        spec["description"] = config["description"]
    return validate_spec(spec)


def connector_for(source: str | None) -> DataConnector:
    """The library data connector for a user's chosen data source."""
    if source == OPENBB:
        from indexforge.data.connectors import OpenBBConnector

        if OpenBBConnector is None:
            raise BuildError("The OpenBB data source is not installed on this server.")
        return OpenBBConnector()

    from indexforge.data.connectors.yahoo import YahooFinanceConnector

    return YahooFinanceConnector()


def run_build(spec: dict[str, Any], source: str | None = None) -> BuildResult:
    """
    Build an index from its spec with the chosen data source.

    Raises:
        BuildError: With a message for the user, if no index could be built
    """
    try:
        result = build(spec, connector=connector_for(source))
    except NotImplementedError as e:
        raise BuildError(
            "The selected data source cannot search for companies by rule. "
            "Switch to Yahoo Finance in Data Sources, or name the companies to include."
        ) from e

    if not result.constituents:
        raise BuildError(
            "No company met the rules. Try a lower minimum size, more countries or "
            "sectors, or fewer theme keywords."
        )
    return result


def stored_snapshot(spec: dict[str, Any], result: BuildResult) -> dict[str, Any]:
    """
    The data snapshot to keep with an index.

    Company descriptions are most of a snapshot's size and only a theme filter
    reads them, so they are kept only when the spec has one. Either way the
    stored snapshot replays to the same members and weights.
    """
    snapshot = dict(result.snapshot)
    if not (spec.get("selection") or {}).get("theme_keywords"):
        snapshot["constituents"] = [
            {**row, "business_description": ""} for row in snapshot.get("constituents", [])
        ]
    return snapshot


def apply_build(db: Session, index: Index, spec: dict[str, Any], result: BuildResult) -> int:
    """
    Make an index match a build: its rules, its members and the evidence.

    Replaces the index's components. The caller commits.

    Returns:
        The number of members
    """
    universe = spec["universe"]
    selection = spec.get("selection") or {}
    weighting = spec["weighting"]

    index.currency = spec["currency"]
    index.countries = universe.get("countries")
    index.sectors = universe.get("sectors")
    index.min_market_cap = universe.get("min_market_cap")
    index.max_components = selection.get("top") or len(result.constituents)
    index.weighting_method = weighting["method"]
    index.max_weight = weighting.get("max_weight")
    index.rebalance_frequency = spec["rebalancing"]["frequency"]

    custom_rules = dict(index.custom_rules or {})
    if selection.get("theme_keywords"):
        custom_rules["theme_keywords"] = selection["theme_keywords"]
    else:
        custom_rules.pop("theme_keywords", None)
    index.custom_rules = custom_rules

    index.spec = spec
    index.build_info = {
        "as_of": result.as_of,
        "data_source": result.data_source,
        "candidates": len(result.constituents) + len(result.exclusions),
        "exclusions": dict(sorted(result.exclusions.items())),
        "unconverted": dict(sorted(result.unconverted.items())),
        # Countries in the rules that the data source has no exchange for.
        "unscreened": sorted(result.unscreened),
    }
    index.build_snapshot = stored_snapshot(spec, result)

    db.query(IndexComponent).filter(IndexComponent.index_id == str(index.id)).delete()
    for constituent in result.constituents:
        db.add(
            IndexComponent(
                index_id=str(index.id),
                ticker=constituent.ticker,
                name=constituent.name or constituent.ticker,
                sector=constituent.sector or None,
                industry=constituent.industry or None,
                country=constituent.country or None,
                # Already converted to the index currency by the library.
                market_cap=constituent.market_cap or None,
                price=constituent.price or None,
                avg_volume=constituent.average_daily_volume or None,
                weight=constituent.weight,
                target_weight=constituent.weight,
                is_active=True,
            )
        )
    return len(result.constituents)

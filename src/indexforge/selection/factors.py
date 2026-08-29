"""
The factor registry: the single declaration of which factors this library can
actually compute.

Support used to be asserted in several places that disagreed with each other --
the ``Factor`` enum, two separate ``_get_factor_value`` mappings that covered
different sets, and each connector's field population. A factor missing from a
mapping resolved to ``None``, which the ranking code turned into ``0.0``, so every
constituent scored the same and the "ranking" silently became input order. No
error, no warning, plausible-looking output.

Here support is *derived* from a resolver that exists or does not. Anything not in
``FACTOR_REGISTRY`` raises rather than scoring zero: a methodology that cannot be
computed should fail where someone can see it.

Adding a factor means adding one entry here. Nothing else needs to learn about it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from indexforge.core.constituent import Constituent
from indexforge.core.types import Factor


class UnsupportedFactorError(ValueError):
    """
    Raised when ranking is requested on a factor with no resolver.

    Carries the supported set so the caller can report something actionable
    rather than just naming what failed.
    """

    def __init__(self, factor: Factor) -> None:
        supported = ", ".join(sorted(f.name for f in FACTOR_REGISTRY))
        super().__init__(
            f"Factor.{factor.name} is not supported by this build. "
            f"Supported factors: {supported}"
        )
        self.factor = factor


@dataclass(frozen=True)
class FactorSpec:
    """
    How to compute one factor, and what it needs to do so.

    Attributes:
        factor: The factor this describes.
        resolve: Reads the value off a constituent. Returns None when the data is
            absent for that particular constituent, which is a different situation
            from the factor being unsupported entirely.
        requires: Constituent fields the resolver reads. Lets a connector declare
            coverage, so "unavailable with your data source" can be distinguished
            from "not implemented".
        higher_is_better: Whether a larger value should rank higher. False for
            valuation ratios, where cheap is the point.
    """

    factor: Factor
    resolve: Callable[[Constituent], float | None]
    requires: tuple[str, ...]
    higher_is_better: bool = True


def _positive(value: float | None) -> float | None:
    """
    Treat non-positive values as missing.

    A market cap or volume of zero means the data did not arrive, not that the
    company is worthless. Ratios like P/E are genuinely undefined at or below zero
    (a loss-making company has no meaningful earnings multiple), and ranking on
    them would otherwise place losses at the cheap end.
    """
    if value is None or value <= 0:
        return None
    return value


FACTOR_REGISTRY: dict[Factor, FactorSpec] = {
    Factor.MARKET_CAP: FactorSpec(
        factor=Factor.MARKET_CAP,
        resolve=lambda c: _positive(c.market_cap),
        requires=("market_cap",),
    ),
    Factor.FREE_FLOAT_MARKET_CAP: FactorSpec(
        factor=Factor.FREE_FLOAT_MARKET_CAP,
        resolve=lambda c: _positive(c.free_float_market_cap),
        requires=("free_float_market_cap", "free_float_factor"),
    ),
    Factor.LIQUIDITY: FactorSpec(
        factor=Factor.LIQUIDITY,
        resolve=lambda c: _positive(c.average_daily_volume),
        requires=("average_daily_volume",),
    ),
    Factor.VOLUME: FactorSpec(
        factor=Factor.VOLUME,
        resolve=lambda c: _positive(c.average_daily_volume),
        requires=("average_daily_volume",),
    ),
    Factor.DIVIDEND_YIELD: FactorSpec(
        factor=Factor.DIVIDEND_YIELD,
        resolve=lambda c: _positive(c.dividend_yield),
        requires=("dividend_yield",),
    ),
    Factor.PRICE_TO_EARNINGS: FactorSpec(
        factor=Factor.PRICE_TO_EARNINGS,
        resolve=lambda c: _positive(c.pe_ratio),
        requires=("pe_ratio",),
        # A value screen wants the cheap end. Ranking descending on P/E selected
        # the most expensive companies in the universe.
        higher_is_better=False,
    ),
    Factor.PRICE_TO_BOOK: FactorSpec(
        factor=Factor.PRICE_TO_BOOK,
        resolve=lambda c: _positive(c.pb_ratio),
        requires=("pb_ratio",),
        higher_is_better=False,
    ),
}

#: Factors this build can compute. Derived, never hand-maintained.
SUPPORTED_FACTORS = frozenset(FACTOR_REGISTRY)

#: Factors named by the enum but not yet implemented. Exposed so callers can tell
#: users what is coming rather than pretending these do not exist.
UNSUPPORTED_FACTORS = frozenset(Factor) - SUPPORTED_FACTORS


def is_supported(factor: Factor) -> bool:
    """Whether this build can compute the factor at all."""
    return factor in FACTOR_REGISTRY


def resolve_factor(constituent: Constituent, factor: Factor) -> float | None:
    """
    Read a factor's value off a constituent.

    Returns None when the constituent lacks the underlying data. That is a normal
    condition and callers should handle it; an unsupported factor is not.

    Raises:
        UnsupportedFactorError: if no resolver is registered for the factor.
    """
    spec = FACTOR_REGISTRY.get(factor)
    if spec is None:
        raise UnsupportedFactorError(factor)
    return spec.resolve(constituent)


def sort_key(factor: Factor) -> tuple[bool, float]:
    """
    Ranking direction for a factor, as (higher_is_better, sentinel).

    The sentinel is the score given to a constituent whose value is missing, and
    it is always the worst possible one, so absent data sorts to the bottom rather
    than to the top of a "cheapest" screen.
    """
    spec = FACTOR_REGISTRY.get(factor)
    if spec is None:
        raise UnsupportedFactorError(factor)
    return (spec.higher_is_better, float("-inf") if spec.higher_is_better else float("inf"))


def missing_requirements(factor: Factor, provided_fields: frozenset[str]) -> tuple[str, ...]:
    """
    Which of a factor's required fields a data source does not populate.

    Empty means the factor is usable with that source. Lets the UI say "not
    available with OpenBB" rather than offering a factor that will silently score
    every constituent the same.
    """
    spec = FACTOR_REGISTRY.get(factor)
    if spec is None:
        raise UnsupportedFactorError(factor)
    return tuple(field for field in spec.requires if field not in provided_fields)

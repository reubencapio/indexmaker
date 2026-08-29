"""
Divisor-based index arithmetic.

An index level is not an average of prices. It is the market value of a notional
portfolio divided by a *divisor*, where the divisor absorbs every change in market
value that did not come from the market:

    level = sum(price_i * shares_i) / divisor

Shares are held fixed between rebalances, which is what makes the level meaningful:
if no price moves, the level does not move. Weights are an *output* of that
arithmetic, not an input -- they drift with prices, exactly as a real portfolio's do.

Whenever composition changes for a non-market reason (a rebalance, an addition, a
deletion, a share-count change), the divisor is reset so the level is continuous
across the event. Without that step the level jumps by an amount no investor
experienced, and the whole series becomes uninterpretable.

This module is deliberately free of database and I/O concerns so the arithmetic can
be tested directly.
"""

from __future__ import annotations

from dataclasses import dataclass

# Below this, a divisor is treated as degenerate rather than merely small: dividing
# by it produces values that are numerically meaningless.
MIN_DIVISOR = 1e-12


class IndexMathError(ValueError):
    """Raised when index arithmetic is asked to do something undefined."""


@dataclass(frozen=True)
class Holding:
    """A constituent's price and the notional share count the index holds."""

    ticker: str
    price: float
    shares: float

    @property
    def value(self) -> float:
        return self.price * self.shares


def market_value(holdings: list[Holding]) -> float:
    """Total market value of the notional portfolio."""
    return sum(h.value for h in holdings)


def index_level(holdings: list[Holding], divisor: float) -> float:
    """
    Current index level.

    Raises:
        IndexMathError: if the divisor is zero or negative, which would make the
            level meaningless rather than merely wrong.
    """
    if divisor <= MIN_DIVISOR:
        raise IndexMathError(f"Divisor must be positive, got {divisor!r}")
    return market_value(holdings) / divisor


def divisor_for_level(holdings: list[Holding], target_level: float) -> float:
    """
    The divisor that makes `holdings` price out at `target_level`.

    This is the single operation behind both index inception (target is the base
    value) and every later composition change (target is the level immediately
    before the change, which is what keeps the series continuous).

    Raises:
        IndexMathError: if the target level is non-positive, or the holdings have
            no market value to divide.
    """
    if target_level <= 0:
        raise IndexMathError(f"Target level must be positive, got {target_level!r}")

    mv = market_value(holdings)
    if mv <= 0:
        raise IndexMathError("Cannot derive a divisor from holdings with no market value")

    return mv / target_level


def weights(holdings: list[Holding]) -> dict[str, float]:
    """
    Current weights, derived from market value.

    These drift between rebalances and are an output of the arithmetic. Nothing
    should ever write them back into the shares.
    """
    mv = market_value(holdings)
    if mv <= 0:
        return {}
    return {h.ticker: h.value / mv for h in holdings}


def shares_for_weights(
    target_weights: dict[str, float],
    prices: dict[str, float],
    notional: float,
) -> dict[str, float]:
    """
    Convert target weights into share counts for a given notional market value.

    Tickers with a missing or non-positive price are skipped: an index cannot hold
    a position it cannot value, and silently assigning it zero shares would quietly
    redistribute its weight to everyone else.

    Raises:
        IndexMathError: if the notional is non-positive.
    """
    if notional <= 0:
        raise IndexMathError(f"Notional must be positive, got {notional!r}")

    result: dict[str, float] = {}
    for ticker, weight in target_weights.items():
        price = prices.get(ticker)
        if price is None or price <= 0:
            continue
        result[ticker] = (weight * notional) / price
    return result


def rebalance(
    current: list[Holding],
    target_weights: dict[str, float],
    prices: dict[str, float],
    divisor: float,
) -> tuple[list[Holding], float]:
    """
    Reallocate the portfolio to `target_weights` without moving the index level.

    Returns the new holdings and the new divisor. The level before and after is
    identical by construction -- a rebalance reallocates, it does not create or
    destroy value.

    Reallocating the *existing* market value leaves the divisor unchanged in the
    common case; it is still recomputed explicitly so that additions, deletions and
    accumulated floating-point drift are all handled by the same code path.

    Raises:
        IndexMathError: if the level cannot be determined before the change, since
            there would then be nothing to hold continuous.
    """
    level_before = index_level(current, divisor)

    notional = market_value(current)
    new_shares = shares_for_weights(target_weights, prices, notional)

    new_holdings = [
        Holding(ticker=ticker, price=prices[ticker], shares=shares)
        for ticker, shares in new_shares.items()
    ]

    if not new_holdings:
        raise IndexMathError("Rebalance produced no priceable holdings")

    return new_holdings, divisor_for_level(new_holdings, level_before)


def inception(
    target_weights: dict[str, float],
    prices: dict[str, float],
    base_value: float,
    notional: float | None = None,
) -> tuple[list[Holding], float]:
    """
    Establish the opening holdings and divisor for a new index.

    The notional is arbitrary -- it cancels out of the level entirely -- so it
    defaults to the base value, which keeps the opening divisor at 1.0 and the
    numbers legible to anyone reading the database by hand.

    Raises:
        IndexMathError: if no target constituent has a usable price.
    """
    if base_value <= 0:
        raise IndexMathError(f"Base value must be positive, got {base_value!r}")

    opening_notional = base_value if notional is None else notional
    shares = shares_for_weights(target_weights, prices, opening_notional)

    holdings = [
        Holding(ticker=ticker, price=prices[ticker], shares=share_count)
        for ticker, share_count in shares.items()
    ]

    if not holdings:
        raise IndexMathError("Cannot start an index with no priceable constituents")

    return holdings, divisor_for_level(holdings, base_value)


def apply_share_change(
    holdings: list[Holding],
    ticker: str,
    ratio: float,
    divisor: float,
    new_price: float | None = None,
) -> tuple[list[Holding], float]:
    """
    Apply a share-count change such as a split or a share-count restatement.

    `holdings` must be the state *before* the event, priced before the event. The
    level is held continuous across the event, which is the whole point: no investor
    experiences a return because a company split its stock or restated its count.

    A 2-for-1 split is ratio=2.0 with new_price set to the post-split price. Share
    count doubles as price halves, market value is unchanged, and the divisor comes
    back unchanged.

    A restatement with no price move (a buyback, a secondary issue) changes market
    value, and there the divisor genuinely does move so that the level does not.

    Note: this assumes the price series is not retroactively back-adjusted by the
    data vendor. A vendor that rewrites history will double-count the event -- see
    the data-provenance caveat in the service layer.

    Raises:
        IndexMathError: if the ratio or price is non-positive, or the ticker is not
            currently held.
    """
    if ratio <= 0:
        raise IndexMathError(f"Share change ratio must be positive, got {ratio!r}")
    if new_price is not None and new_price <= 0:
        raise IndexMathError(f"New price must be positive, got {new_price!r}")
    if not any(h.ticker == ticker for h in holdings):
        raise IndexMathError(f"{ticker} is not a current constituent")

    level_before = index_level(holdings, divisor)

    adjusted = [
        Holding(
            ticker=h.ticker,
            price=h.price if new_price is None else new_price,
            shares=h.shares * ratio,
        )
        if h.ticker == ticker
        else h
        for h in holdings
    ]

    return adjusted, divisor_for_level(adjusted, level_before)

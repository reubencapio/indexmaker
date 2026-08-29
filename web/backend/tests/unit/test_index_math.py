"""
Unit tests for divisor-based index arithmetic.

These pin the properties the previous weighted-average-price calculation violated:
the index starts at its base value, a rebalance does not move the level, and a
split does not move the level.
"""

import pytest

from app.services.index_math import (
    Holding,
    IndexMathError,
    apply_share_change,
    divisor_for_level,
    inception,
    index_level,
    market_value,
    rebalance,
    shares_for_weights,
    weights,
)


class TestLevel:
    """Basic level arithmetic."""

    def test_level_is_market_value_over_divisor(self):
        holdings = [Holding("A", price=10.0, shares=100.0)]
        assert index_level(holdings, divisor=2.0) == 500.0

    def test_zero_divisor_is_rejected(self):
        with pytest.raises(IndexMathError, match="Divisor must be positive"):
            index_level([Holding("A", 10.0, 1.0)], divisor=0.0)

    def test_negative_divisor_is_rejected(self):
        with pytest.raises(IndexMathError):
            index_level([Holding("A", 10.0, 1.0)], divisor=-1.0)


class TestInception:
    """An index must start at the base value it was created with."""

    def test_index_opens_at_its_base_value(self):
        holdings, divisor = inception(
            target_weights={"A": 0.5, "B": 0.5},
            prices={"A": 100.0, "B": 25.0},
            base_value=1000.0,
        )
        assert index_level(holdings, divisor) == pytest.approx(1000.0)

    def test_opening_weights_match_targets(self):
        holdings, _ = inception(
            target_weights={"A": 0.7, "B": 0.3},
            prices={"A": 100.0, "B": 25.0},
            base_value=1000.0,
        )
        result = weights(holdings)
        assert result["A"] == pytest.approx(0.7)
        assert result["B"] == pytest.approx(0.3)

    def test_base_value_is_honoured_for_any_base(self):
        for base in (100.0, 1000.0, 5000.0):
            holdings, divisor = inception({"A": 1.0}, {"A": 33.33}, base_value=base)
            assert index_level(holdings, divisor) == pytest.approx(base)

    def test_notional_choice_does_not_affect_the_level(self):
        """The notional cancels out; only the base value determines the level."""
        a_holdings, a_div = inception({"A": 1.0}, {"A": 50.0}, 1000.0, notional=1000.0)
        b_holdings, b_div = inception({"A": 1.0}, {"A": 50.0}, 1000.0, notional=10_000_000.0)
        assert index_level(a_holdings, a_div) == pytest.approx(index_level(b_holdings, b_div))

    def test_unpriced_constituents_are_excluded(self):
        holdings, _ = inception(
            target_weights={"A": 0.5, "B": 0.5},
            prices={"A": 100.0, "B": 0.0},
            base_value=1000.0,
        )
        assert [h.ticker for h in holdings] == ["A"]

    def test_no_priceable_constituents_is_an_error(self):
        with pytest.raises(IndexMathError, match="no priceable constituents"):
            inception({"A": 1.0}, {"A": 0.0}, base_value=1000.0)

    def test_non_positive_base_value_is_rejected(self):
        with pytest.raises(IndexMathError, match="Base value must be positive"):
            inception({"A": 1.0}, {"A": 10.0}, base_value=0.0)


class TestPriceMoves:
    """Between rebalances, shares are fixed and the level tracks prices."""

    def test_level_tracks_a_price_move(self):
        holdings, divisor = inception({"A": 1.0}, {"A": 100.0}, base_value=1000.0)
        after = [Holding("A", price=110.0, shares=holdings[0].shares)]
        assert index_level(after, divisor) == pytest.approx(1100.0)

    def test_level_does_not_move_when_prices_do_not(self):
        holdings, divisor = inception(
            {"A": 0.5, "B": 0.5}, {"A": 100.0, "B": 40.0}, base_value=1000.0
        )
        assert index_level(holdings, divisor) == pytest.approx(1000.0)

    def test_weights_drift_with_prices(self):
        holdings, _ = inception({"A": 0.5, "B": 0.5}, {"A": 100.0, "B": 100.0}, base_value=1000.0)
        # A doubles, B is flat: A should now be two thirds of the index.
        drifted = [
            Holding("A", 200.0, holdings[0].shares),
            Holding("B", 100.0, holdings[1].shares),
        ]
        assert weights(drifted)["A"] == pytest.approx(2 / 3)


class TestRebalance:
    """A rebalance reallocates; it must not create or destroy index value."""

    def test_rebalance_does_not_move_the_level(self):
        holdings, divisor = inception(
            {"A": 0.5, "B": 0.5}, {"A": 100.0, "B": 100.0}, base_value=1000.0
        )
        drifted = [
            Holding("A", 200.0, holdings[0].shares),
            Holding("B", 100.0, holdings[1].shares),
        ]
        level_before = index_level(drifted, divisor)

        new_holdings, new_divisor = rebalance(
            drifted,
            target_weights={"A": 0.5, "B": 0.5},
            prices={"A": 200.0, "B": 100.0},
            divisor=divisor,
        )

        assert index_level(new_holdings, new_divisor) == pytest.approx(level_before)

    def test_rebalance_applies_the_target_weights(self):
        holdings, divisor = inception(
            {"A": 0.5, "B": 0.5}, {"A": 100.0, "B": 100.0}, base_value=1000.0
        )
        new_holdings, _ = rebalance(
            holdings,
            target_weights={"A": 0.9, "B": 0.1},
            prices={"A": 100.0, "B": 100.0},
            divisor=divisor,
        )
        assert weights(new_holdings)["A"] == pytest.approx(0.9)

    def test_adding_a_constituent_does_not_move_the_level(self):
        """The bug that made the old implementation unusable."""
        holdings, divisor = inception({"A": 1.0}, {"A": 100.0}, base_value=1000.0)
        level_before = index_level(holdings, divisor)

        new_holdings, new_divisor = rebalance(
            holdings,
            target_weights={"A": 0.5, "C": 0.5},
            prices={"A": 100.0, "C": 250.0},
            divisor=divisor,
        )

        assert index_level(new_holdings, new_divisor) == pytest.approx(level_before)
        assert {h.ticker for h in new_holdings} == {"A", "C"}

    def test_removing_a_constituent_does_not_move_the_level(self):
        holdings, divisor = inception(
            {"A": 0.5, "B": 0.5}, {"A": 100.0, "B": 50.0}, base_value=1000.0
        )
        level_before = index_level(holdings, divisor)

        new_holdings, new_divisor = rebalance(
            holdings,
            target_weights={"A": 1.0},
            prices={"A": 100.0, "B": 50.0},
            divisor=divisor,
        )

        assert index_level(new_holdings, new_divisor) == pytest.approx(level_before)
        assert [h.ticker for h in new_holdings] == ["A"]

    def test_repeated_rebalances_do_not_drift(self):
        holdings, divisor = inception(
            {"A": 0.5, "B": 0.5}, {"A": 100.0, "B": 100.0}, base_value=1000.0
        )
        prices = {"A": 100.0, "B": 100.0}
        for _ in range(50):
            holdings, divisor = rebalance(holdings, {"A": 0.5, "B": 0.5}, prices, divisor)

        assert index_level(holdings, divisor) == pytest.approx(1000.0)

    def test_rebalance_with_no_priceable_targets_is_an_error(self):
        holdings, divisor = inception({"A": 1.0}, {"A": 100.0}, base_value=1000.0)
        with pytest.raises(IndexMathError, match="no priceable holdings"):
            rebalance(holdings, {"Z": 1.0}, {"Z": 0.0}, divisor)


class TestShareChanges:
    """Corporate actions must not move the level."""

    def test_two_for_one_split_does_not_move_the_level(self):
        holdings, divisor = inception(
            {"A": 0.5, "B": 0.5}, {"A": 100.0, "B": 100.0}, base_value=1000.0
        )
        level_before = index_level(holdings, divisor)

        # Pre-event holdings in, post-split price supplied with the event.
        adjusted, new_divisor = apply_share_change(
            holdings, ticker="A", ratio=2.0, divisor=divisor, new_price=50.0
        )

        assert index_level(adjusted, new_divisor) == pytest.approx(level_before)

    def test_pure_split_leaves_the_divisor_untouched(self):
        holdings, divisor = inception({"A": 1.0}, {"A": 100.0}, base_value=1000.0)
        _, new_divisor = apply_share_change(
            holdings, "A", ratio=2.0, divisor=divisor, new_price=50.0
        )
        assert new_divisor == pytest.approx(divisor)

    def test_share_issuance_without_a_price_move_shifts_the_divisor(self):
        """The level must not jump because a company issued shares."""
        holdings, divisor = inception({"A": 1.0}, {"A": 100.0}, base_value=1000.0)
        adjusted, new_divisor = apply_share_change(holdings, "A", ratio=1.1, divisor=divisor)

        assert index_level(adjusted, new_divisor) == pytest.approx(1000.0)
        assert new_divisor == pytest.approx(divisor * 1.1)

    def test_split_doubles_the_share_count(self):
        holdings = [Holding("A", 100.0, 10.0), Holding("B", 100.0, 5.0)]
        adjusted, _ = apply_share_change(holdings, "A", 2.0, divisor=1.0, new_price=50.0)
        by_ticker = {h.ticker: h for h in adjusted}
        assert by_ticker["A"].shares == pytest.approx(20.0)
        assert by_ticker["A"].value == pytest.approx(1000.0)

    def test_non_positive_new_price_is_rejected(self):
        with pytest.raises(IndexMathError, match="New price must be positive"):
            apply_share_change([Holding("A", 10.0, 1.0)], "A", 2.0, 1.0, new_price=0.0)

    def test_unknown_ticker_is_rejected(self):
        with pytest.raises(IndexMathError, match="not a current constituent"):
            apply_share_change([Holding("A", 10.0, 1.0)], "ZZZ", 2.0, divisor=1.0)

    def test_non_positive_ratio_is_rejected(self):
        with pytest.raises(IndexMathError, match="ratio must be positive"):
            apply_share_change([Holding("A", 10.0, 1.0)], "A", 0.0, divisor=1.0)


class TestHelpers:
    """Supporting arithmetic."""

    def test_market_value_sums_positions(self):
        assert market_value([Holding("A", 10.0, 2.0), Holding("B", 5.0, 4.0)]) == 40.0

    def test_market_value_of_nothing_is_zero(self):
        assert market_value([]) == 0.0

    def test_weights_of_empty_portfolio(self):
        assert weights([]) == {}

    def test_divisor_for_level_round_trips(self):
        holdings = [Holding("A", 100.0, 10.0)]
        divisor = divisor_for_level(holdings, target_level=500.0)
        assert index_level(holdings, divisor) == pytest.approx(500.0)

    def test_divisor_from_worthless_holdings_is_an_error(self):
        with pytest.raises(IndexMathError, match="no market value"):
            divisor_for_level([Holding("A", 0.0, 0.0)], target_level=1000.0)

    def test_shares_for_weights_scales_with_notional(self):
        shares = shares_for_weights({"A": 1.0}, {"A": 50.0}, notional=1000.0)
        assert shares["A"] == pytest.approx(20.0)

    def test_shares_for_weights_rejects_bad_notional(self):
        with pytest.raises(IndexMathError, match="Notional must be positive"):
            shares_for_weights({"A": 1.0}, {"A": 50.0}, notional=0.0)

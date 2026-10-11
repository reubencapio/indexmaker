"""Tests for the plan catalogue and the gates built on it."""

import pytest
from fastapi import HTTPException

from app.core import plans


def test_unknown_tier_falls_back_to_free():
    assert plans.get_plan("nonsense").id == plans.FREE
    assert plans.get_plan(None).id == plans.FREE


def test_every_plan_feature_has_a_label():
    for plan in plans.PLANS.values():
        assert plan.features <= set(plans.FEATURE_LABELS)


def test_capacity_gate_raises_structured_402():
    plans.require_capacity(plans.FREE, "max_indices", 2, "indices")
    with pytest.raises(HTTPException) as exc:
        plans.require_capacity(plans.FREE, "max_indices", 3, "indices")
    assert exc.value.status_code == 402
    assert exc.value.detail["code"] == "upgrade_required"
    assert exc.value.detail["limit"] == "max_indices"


def test_unlimited_capacity_never_raises():
    plans.require_capacity(plans.PRO, "max_public_shares", 10_000, "shares")


def test_feature_gate():
    plans.require_feature(plans.PRO, plans.FEATURE_DELIVERY)
    with pytest.raises(HTTPException) as exc:
        plans.require_feature(plans.FREE, plans.FEATURE_DELIVERY)
    assert exc.value.detail["feature"] == plans.FEATURE_DELIVERY

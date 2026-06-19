import pytest

from loco.evaluation.fe_accounting import FEBudgetTracker


def test_fe_accounting_sums_categories_and_exports_dict() -> None:
    tracker = FEBudgetTracker(max_fe=10)
    tracker.record("grouping", 2)
    tracker.record("proposal", 3)
    tracker.record("coordination_extra", 1)
    tracker.record("repair", 2)

    data = tracker.to_dict()
    assert data["fe_grouping"] == 2
    assert data["fe_proposal"] == 3
    assert data["fe_coordination_extra"] == 1
    assert data["fe_repair"] == 2
    assert data["fe_total"] == 8
    assert data["remaining_fe"] == 2
    assert data["exhausted"] is False


def test_fe_accounting_rejects_unknown_category_and_budget_overrun() -> None:
    tracker = FEBudgetTracker(max_fe=3)

    with pytest.raises(ValueError, match="Unknown FE category"):
        tracker.record("free_eval", 1)

    tracker.record("proposal", 3)
    assert tracker.exhausted is True
    with pytest.raises(RuntimeError, match="FE budget exhausted"):
        tracker.record("repair", 1)

import math

from loco.conflict.longitudinal_metrics import (
    conflict_oscillation,
    conflict_persistence_over_rounds,
    consensus_instability_over_rounds,
    longitudinal_conflict_reduction_ratio,
    objective_improvement_per_fe,
)


def test_longitudinal_conflict_reduction_uses_next_round_regenerated_conflict() -> None:
    same_round_after = [0.0, 0.0, 0.0]
    next_round_regenerated = [0.6, 0.5, 0.4]
    before = [1.0, 1.0, 1.0]

    ratio = longitudinal_conflict_reduction_ratio(
        conflict_before=before,
        regenerated_conflict_next=next_round_regenerated,
    )

    assert math.isclose(ratio, 0.5)
    assert ratio != 1.0
    assert same_round_after != next_round_regenerated


def test_longitudinal_metrics_are_finite_and_nonnegative() -> None:
    conflict_before = [1.0, 0.8, 0.6, 0.6, 0.4]
    regenerated = [0.9, 0.7, 0.7, 0.5, 0.3]
    objectives = [100.0, 92.0, 90.0, 85.0]
    fe_totals = [10, 20, 30, 40]
    consensus_history = {
        1: [0.0, 0.4, -0.2, 0.1],
        2: [1.0, 0.8, 0.7, 0.65],
    }

    values = [
        longitudinal_conflict_reduction_ratio(conflict_before, regenerated),
        conflict_oscillation(regenerated),
        conflict_persistence_over_rounds(conflict_before, regenerated),
        consensus_instability_over_rounds(consensus_history),
        objective_improvement_per_fe(objectives, fe_totals),
    ]

    for value in values:
        assert math.isfinite(value)
        assert value >= 0.0


def test_objective_improvement_per_fe_handles_zero_or_empty_budget() -> None:
    assert objective_improvement_per_fe([], []) == 0.0
    assert objective_improvement_per_fe([1.0], [0]) == 0.0
    assert objective_improvement_per_fe([10.0, 7.0], [5, 5]) == 0.0

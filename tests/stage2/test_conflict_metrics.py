import math

import numpy as np

from loco.conflict.conflict_metrics import (
    conflict_intensity,
    direction_disagreement,
    metrics_for_state,
    oscillation_score,
    reward_disagreement,
    value_disagreement,
)
from loco.conflict.conflict_state import GroupProposal, SharedVariableConflictState


def _state(proposals=(0.8, -0.6), rewards=(1.0, -0.5), history=(0.2, -0.2, 0.3, -0.1)):
    group_proposals = [
        GroupProposal(
            group_id=i, variable_id=2, proposed_value=value, reward=rewards[i]
        )
        for i, value in enumerate(proposals)
    ]
    return SharedVariableConflictState.from_group_proposals(
        variable_id=2,
        current_value=0.0,
        bounds=(-1.0, 1.0),
        proposals=group_proposals,
        consensus_history=history,
    )


def test_conflict_metrics_are_deterministic_and_finite() -> None:
    state = _state()
    first = metrics_for_state(state)
    second = metrics_for_state(state)

    assert first == second
    assert set(first) == {
        "value_disagreement",
        "direction_disagreement",
        "reward_disagreement",
        "conflict_intensity",
        "oscillation_score",
    }
    assert all(math.isfinite(value) and value >= 0.0 for value in first.values())


def test_single_proposal_has_zero_disagreement() -> None:
    state = _state(proposals=(0.5,), rewards=(1.0,), history=(0.1,))

    assert value_disagreement(state) == 0.0
    assert direction_disagreement(state) == 0.0
    assert reward_disagreement(state) == 0.0
    assert conflict_intensity(state) == 0.0
    assert oscillation_score(state) == 0.0


def test_metric_definitions_capture_conflict() -> None:
    state = _state()

    assert np.isclose(value_disagreement(state), 1.4 / 2.0)
    assert direction_disagreement(state) > 0.0
    assert reward_disagreement(state) > 0.0
    assert conflict_intensity(state) > value_disagreement(state) / 3.0
    assert oscillation_score(state) > 0.0

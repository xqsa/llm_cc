import numpy as np

from loco.coordination.baselines import (
    AverageConsensus,
    BestRewardSelection,
    ConflictDampening,
    NoCoordination,
    WeightedConsensus,
)
from loco.conflict.conflict_state import GroupProposal, SharedVariableConflictState


def _state() -> SharedVariableConflictState:
    return SharedVariableConflictState.from_group_proposals(
        variable_id=5,
        current_value=0.0,
        bounds=(-0.5, 0.5),
        proposals=[
            GroupProposal(group_id=0, variable_id=5, proposed_value=0.8, reward=0.0),
            GroupProposal(group_id=1, variable_id=5, proposed_value=-0.2, reward=2.0),
            GroupProposal(group_id=2, variable_id=5, proposed_value=0.4, reward=1.0),
        ],
        consensus_history=[0.2, -0.2, 0.2],
    )


def test_no_coordination_is_deterministic_and_uses_current_value() -> None:
    result = NoCoordination().coordinate(_state())

    assert result.variable_id == 5
    assert result.coordinated_value == 0.0
    assert result.operator_name == "NoCoordination"
    assert result.extra_fe == 0


def test_average_consensus_respects_bounds() -> None:
    result = AverageConsensus().coordinate(_state())

    assert np.isclose(result.coordinated_value, (0.8 - 0.2 + 0.4) / 3.0)
    assert -0.5 <= result.coordinated_value <= 0.5


def test_best_reward_selection_selects_best_reward_proposal() -> None:
    result = BestRewardSelection().coordinate(_state())

    assert result.coordinated_value == -0.2
    assert result.diagnostics["selected_group_id"] == 1


def test_weighted_consensus_softmax_weights_best_reward_more() -> None:
    result = WeightedConsensus(temperature=1.0).coordinate(_state())

    assert -0.2 < result.coordinated_value < 0.4
    assert result.diagnostics["weights"][1] > result.diagnostics["weights"][2]
    assert result.diagnostics["weights"][2] > result.diagnostics["weights"][0]


def test_conflict_dampening_reduces_update_magnitude_under_high_conflict() -> None:
    state = _state()
    average = AverageConsensus().coordinate(state).coordinated_value
    dampened = ConflictDampening(base_operator=AverageConsensus(), damping_strength=0.75).coordinate(state)

    assert abs(dampened.coordinated_value - state.current_value) < abs(average - state.current_value)
    assert dampened.extra_fe == 0
    assert dampened.diagnostics["conflict_intensity"] > 0.0

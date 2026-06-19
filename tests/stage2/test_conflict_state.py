import numpy as np
import pytest

from loco.conflict.conflict_state import (
    ConflictStateBatch,
    GroupProposal,
    SharedVariableConflictState,
)


def test_conflict_state_records_shared_variable_proposals_without_fe() -> None:
    state = SharedVariableConflictState.from_group_proposals(
        variable_id=3,
        current_value=0.25,
        bounds=(-1.0, 1.0),
        proposals=[
            GroupProposal(group_id=0, variable_id=3, proposed_value=0.5, reward=1.0),
            GroupProposal(group_id=1, variable_id=3, proposed_value=-0.25, reward=-0.2),
        ],
        previous_consensus_value=0.1,
        accepted_value=0.2,
        consensus_history=[0.1, -0.1, 0.15],
        accepted_history=[0.05, 0.2],
    )

    assert state.variable_id == 3
    assert state.related_group_ids == (0, 1)
    assert state.proposals == (0.5, -0.25)
    assert state.proposal_directions == (0.25, -0.5)
    assert state.group_rewards == (1.0, -0.2)
    assert state.clip(2.0) == 1.0
    assert state.clip(-2.0) == -1.0


def test_conflict_state_rejects_mixed_variable_proposals() -> None:
    with pytest.raises(ValueError, match="same shared variable"):
        SharedVariableConflictState.from_group_proposals(
            variable_id=3,
            current_value=0.0,
            bounds=(-1.0, 1.0),
            proposals=[
                GroupProposal(
                    group_id=0, variable_id=3, proposed_value=0.2, reward=1.0
                ),
                GroupProposal(
                    group_id=1, variable_id=4, proposed_value=0.3, reward=1.0
                ),
            ],
        )


def test_conflict_state_batch_constructs_deterministic_states() -> None:
    grouped = {
        2: [
            GroupProposal(group_id=1, variable_id=2, proposed_value=0.2, reward=0.3),
            GroupProposal(group_id=0, variable_id=2, proposed_value=-0.1, reward=0.1),
        ],
        1: [
            GroupProposal(group_id=0, variable_id=1, proposed_value=0.4, reward=0.2),
        ],
    }

    batch = ConflictStateBatch.from_grouped_proposals(
        current_values=np.array([0.0, 0.1, 0.0]),
        lower_bounds=np.array([-1.0, -1.0, -1.0]),
        upper_bounds=np.array([1.0, 1.0, 1.0]),
        grouped_proposals=grouped,
    )

    assert [state.variable_id for state in batch.states] == [1, 2]
    assert batch.by_variable()[2].related_group_ids == (0, 1)
    assert batch.mean_conflict_intensity() >= 0.0

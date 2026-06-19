"""Shared-variable conflict state objects for Stage 2.0."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np


@dataclass(frozen=True)
class GroupProposal:
    """One group's proposal for one shared variable."""

    group_id: int
    variable_id: int
    proposed_value: float
    reward: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SharedVariableConflictState:
    """Conflict state for a single shared variable.

    The object is purely descriptive. It never evaluates or mutates a benchmark.
    """

    variable_id: int
    current_value: float
    bounds: tuple[float, float]
    related_group_ids: tuple[int, ...]
    proposals: tuple[float, ...]
    proposal_directions: tuple[float, ...]
    group_rewards: tuple[float, ...]
    previous_consensus_value: float | None = None
    accepted_value: float | None = None
    consensus_history: tuple[float, ...] = ()
    accepted_history: tuple[float, ...] = ()
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_group_proposals(
        cls,
        variable_id: int,
        current_value: float,
        bounds: tuple[float, float],
        proposals: Iterable[GroupProposal],
        previous_consensus_value: float | None = None,
        accepted_value: float | None = None,
        consensus_history: Iterable[float] = (),
        accepted_history: Iterable[float] = (),
        diagnostics: dict[str, Any] | None = None,
    ) -> "SharedVariableConflictState":
        proposal_list = sorted(list(proposals), key=lambda item: item.group_id)
        if not proposal_list:
            raise ValueError("At least one proposal is required for a conflict state.")
        if any(item.variable_id != variable_id for item in proposal_list):
            raise ValueError("All proposals must belong to the same shared variable.")

        lower, upper = float(bounds[0]), float(bounds[1])
        if not np.isfinite([lower, upper]).all() or lower >= upper:
            raise ValueError("bounds must be finite and lower < upper.")

        current = float(current_value)
        if not np.isfinite(current):
            raise ValueError("current_value must be finite.")

        values = tuple(float(item.proposed_value) for item in proposal_list)
        rewards = tuple(float(item.reward) for item in proposal_list)
        if not np.isfinite(values).all() or not np.isfinite(rewards).all():
            raise ValueError("proposals and rewards must be finite.")

        return cls(
            variable_id=int(variable_id),
            current_value=current,
            bounds=(lower, upper),
            related_group_ids=tuple(int(item.group_id) for item in proposal_list),
            proposals=values,
            proposal_directions=tuple(value - current for value in values),
            group_rewards=rewards,
            previous_consensus_value=(
                None if previous_consensus_value is None else float(previous_consensus_value)
            ),
            accepted_value=None if accepted_value is None else float(accepted_value),
            consensus_history=tuple(float(value) for value in consensus_history),
            accepted_history=tuple(float(value) for value in accepted_history),
            diagnostics=dict(diagnostics or {}),
        )

    @property
    def range_width(self) -> float:
        return self.bounds[1] - self.bounds[0]

    def clip(self, value: float) -> float:
        return float(np.clip(float(value), self.bounds[0], self.bounds[1]))

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable_id": self.variable_id,
            "current_value": self.current_value,
            "bounds": list(self.bounds),
            "related_group_ids": list(self.related_group_ids),
            "proposals": list(self.proposals),
            "proposal_directions": list(self.proposal_directions),
            "group_rewards": list(self.group_rewards),
            "previous_consensus_value": self.previous_consensus_value,
            "accepted_value": self.accepted_value,
            "consensus_history": list(self.consensus_history),
            "accepted_history": list(self.accepted_history),
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True)
class ConflictStateBatch:
    """A deterministic batch of shared-variable conflict states."""

    states: tuple[SharedVariableConflictState, ...]

    @classmethod
    def from_grouped_proposals(
        cls,
        current_values: np.ndarray,
        lower_bounds: np.ndarray,
        upper_bounds: np.ndarray,
        grouped_proposals: dict[int, Iterable[GroupProposal]],
        consensus_history_by_variable: dict[int, Iterable[float]] | None = None,
        accepted_history_by_variable: dict[int, Iterable[float]] | None = None,
    ) -> "ConflictStateBatch":
        current = np.asarray(current_values, dtype=float)
        lower = np.asarray(lower_bounds, dtype=float)
        upper = np.asarray(upper_bounds, dtype=float)
        if current.shape != lower.shape or current.shape != upper.shape:
            raise ValueError("current_values and bounds must have matching shapes.")

        consensus_history_by_variable = consensus_history_by_variable or {}
        accepted_history_by_variable = accepted_history_by_variable or {}
        states = []
        for variable_id in sorted(grouped_proposals):
            states.append(
                SharedVariableConflictState.from_group_proposals(
                    variable_id=variable_id,
                    current_value=float(current[variable_id]),
                    bounds=(float(lower[variable_id]), float(upper[variable_id])),
                    proposals=grouped_proposals[variable_id],
                    consensus_history=consensus_history_by_variable.get(variable_id, ()),
                    accepted_history=accepted_history_by_variable.get(variable_id, ()),
                )
            )
        return cls(states=tuple(states))

    def __iter__(self):
        return iter(self.states)

    def __len__(self) -> int:
        return len(self.states)

    def by_variable(self) -> dict[int, SharedVariableConflictState]:
        return {state.variable_id: state for state in self.states}

    def mean_conflict_intensity(self) -> float:
        if not self.states:
            return 0.0
        from .conflict_metrics import conflict_intensity

        return float(np.mean([conflict_intensity(state) for state in self.states]))

    def to_dict(self) -> dict[str, Any]:
        return {"states": [state.to_dict() for state in self.states]}

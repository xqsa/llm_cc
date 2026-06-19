"""Stage 2.0 baseline coordination operators.

Operators receive only one shared-variable conflict state. They do not access
objective functions, benchmark IDs, schedulers, or non-shared variables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

from loco.conflict.conflict_metrics import conflict_intensity
from loco.conflict.conflict_state import SharedVariableConflictState


@dataclass(frozen=True)
class CoordinationResult:
    variable_id: int
    coordinated_value: float
    operator_name: str
    extra_fe: int = 0
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable_id": self.variable_id,
            "coordinated_value": self.coordinated_value,
            "operator_name": self.operator_name,
            "extra_fe": self.extra_fe,
            "diagnostics": self.diagnostics,
        }


class CoordinationOperator(Protocol):
    name: str

    def coordinate(self, conflict_state: SharedVariableConflictState) -> CoordinationResult:
        ...


class NoCoordination:
    name = "NoCoordination"

    def coordinate(self, conflict_state: SharedVariableConflictState) -> CoordinationResult:
        return CoordinationResult(
            variable_id=conflict_state.variable_id,
            coordinated_value=conflict_state.clip(conflict_state.current_value),
            operator_name=self.name,
            extra_fe=0,
            diagnostics={"policy": "current_value"},
        )


class AverageConsensus:
    name = "AverageConsensus"

    def coordinate(self, conflict_state: SharedVariableConflictState) -> CoordinationResult:
        value = float(np.mean(conflict_state.proposals)) if conflict_state.proposals else conflict_state.current_value
        return CoordinationResult(
            variable_id=conflict_state.variable_id,
            coordinated_value=conflict_state.clip(value),
            operator_name=self.name,
            extra_fe=0,
            diagnostics={"proposal_count": len(conflict_state.proposals)},
        )


class BestRewardSelection:
    name = "BestRewardSelection"

    def coordinate(self, conflict_state: SharedVariableConflictState) -> CoordinationResult:
        rewards = np.asarray(conflict_state.group_rewards, dtype=float)
        best_index = int(np.argmax(rewards))
        return CoordinationResult(
            variable_id=conflict_state.variable_id,
            coordinated_value=conflict_state.clip(conflict_state.proposals[best_index]),
            operator_name=self.name,
            extra_fe=0,
            diagnostics={
                "selected_group_id": conflict_state.related_group_ids[best_index],
                "selected_reward": float(rewards[best_index]),
            },
        )


class WeightedConsensus:
    name = "WeightedConsensus"

    def __init__(self, temperature: float = 1.0):
        if temperature <= 0:
            raise ValueError("temperature must be positive.")
        self.temperature = float(temperature)

    def coordinate(self, conflict_state: SharedVariableConflictState) -> CoordinationResult:
        rewards = np.asarray(conflict_state.group_rewards, dtype=float)
        values = np.asarray(conflict_state.proposals, dtype=float)
        scaled = rewards / self.temperature
        scaled = scaled - float(np.max(scaled))
        weights = np.exp(scaled)
        weights = weights / float(np.sum(weights))
        value = float(np.dot(weights, values))
        return CoordinationResult(
            variable_id=conflict_state.variable_id,
            coordinated_value=conflict_state.clip(value),
            operator_name=self.name,
            extra_fe=0,
            diagnostics={
                "temperature": self.temperature,
                "weights": [float(weight) for weight in weights],
            },
        )


class ConflictDampening:
    name = "ConflictDampening"

    def __init__(
        self,
        base_operator: CoordinationOperator | None = None,
        damping_strength: float = 0.5,
    ):
        if damping_strength < 0:
            raise ValueError("damping_strength must be nonnegative.")
        self.base_operator = base_operator or AverageConsensus()
        self.damping_strength = float(damping_strength)

    def coordinate(self, conflict_state: SharedVariableConflictState) -> CoordinationResult:
        base = self.base_operator.coordinate(conflict_state)
        intensity = conflict_intensity(conflict_state)
        damping = 1.0 / (1.0 + self.damping_strength * intensity)
        value = conflict_state.current_value + damping * (base.coordinated_value - conflict_state.current_value)
        return CoordinationResult(
            variable_id=conflict_state.variable_id,
            coordinated_value=conflict_state.clip(value),
            operator_name=self.name,
            extra_fe=base.extra_fe,
            diagnostics={
                "base_operator": base.operator_name,
                "conflict_intensity": intensity,
                "damping_factor": damping,
                "damping_strength": self.damping_strength,
            },
        )


def default_baseline_operators() -> list[CoordinationOperator]:
    return [
        NoCoordination(),
        AverageConsensus(),
        BestRewardSelection(),
        WeightedConsensus(),
        ConflictDampening(),
    ]

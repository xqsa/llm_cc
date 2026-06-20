"""Runtime shell for frozen typed coordination ASTs.

Stage 2.3 interprets already-validated, frozen ASTs into shared-variable
coordination behavior. It does not call LLMs, run evolution, or evaluate
objectives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from loco.conflict.conflict_metrics import conflict_intensity
from loco.conflict.conflict_state import SharedVariableConflictState
from loco.coordination.baselines import CoordinationResult
from loco.coordination.dsl import (
    CoordinationNodeKind,
    CoordinationOperatorAST,
    DSLNode,
    DSL_SCHEMA_VERSION,
    validate_coordination_ast,
)


@dataclass(frozen=True)
class _NodeValue:
    value: float
    diagnostics: dict[str, Any]


class FrozenASTRuntime:
    """Interpret a frozen typed AST for one shared-variable conflict state."""

    def __init__(self, ast: CoordinationOperatorAST):
        if ast.schema_version != DSL_SCHEMA_VERSION:
            raise ValueError(f"Unsupported DSL schema_version: {ast.schema_version}")
        self.ast = ast

    def coordinate(
        self,
        conflict_state: SharedVariableConflictState,
        shared_variables: set[int] | frozenset[int],
    ) -> CoordinationResult:
        validate_coordination_ast(self.ast, shared_variables=shared_variables)
        node_by_id = {node.id: node for node in self.ast.nodes}
        target_variables = {node.target.variable_id for node in self.ast.nodes}
        if target_variables != {conflict_state.variable_id}:
            raise ValueError(
                "Coordination AST target variable does not match "
                f"conflict_state.variable_id={conflict_state.variable_id}."
            )

        cache: dict[str, _NodeValue] = {}
        trace: list[dict[str, Any]] = []
        output = self._evaluate_node(
            self.ast.output_source,
            node_by_id=node_by_id,
            conflict_state=conflict_state,
            cache=cache,
            trace=trace,
        )

        return CoordinationResult(
            variable_id=conflict_state.variable_id,
            coordinated_value=conflict_state.clip(output.value),
            operator_name=f"DSLRuntime({self.ast.operator_id})",
            extra_fe=0,
            diagnostics={
                "schema_version": self.ast.schema_version,
                "operator_id": self.ast.operator_id,
                "output_node": self.ast.output_source,
                "trace": trace,
            },
        )

    def _evaluate_node(
        self,
        node_id: str,
        *,
        node_by_id: Mapping[str, DSLNode],
        conflict_state: SharedVariableConflictState,
        cache: dict[str, _NodeValue],
        trace: list[dict[str, Any]],
    ) -> _NodeValue:
        cached = cache.get(node_id)
        if cached is not None:
            return cached

        node = node_by_id[node_id]
        source_value = self._source_value(
            node.inputs, node_by_id, conflict_state, cache, trace
        )
        value, diagnostics = self._apply_node(node, conflict_state, source_value)
        result = _NodeValue(value=conflict_state.clip(value), diagnostics=diagnostics)
        cache[node_id] = result
        trace.append(
            {
                "node_id": node.id,
                "kind": node.kind.value,
                "value": result.value,
                "diagnostics": diagnostics,
            }
        )
        return result

    def _source_value(
        self,
        inputs: Mapping[str, Any],
        node_by_id: Mapping[str, DSLNode],
        conflict_state: SharedVariableConflictState,
        cache: dict[str, _NodeValue],
        trace: list[dict[str, Any]],
    ) -> float | None:
        source = inputs.get("source")
        if source is None:
            return None
        return self._evaluate_node(
            str(source),
            node_by_id=node_by_id,
            conflict_state=conflict_state,
            cache=cache,
            trace=trace,
        ).value

    def _apply_node(
        self,
        node: DSLNode,
        conflict_state: SharedVariableConflictState,
        source_value: float | None,
    ) -> tuple[float, dict[str, Any]]:
        if node.kind is CoordinationNodeKind.CONSENSUS:
            return _average_consensus(conflict_state), {
                "proposal_count": len(conflict_state.proposals)
            }
        if node.kind is CoordinationNodeKind.WEIGHTED_CONSENSUS:
            temperature = _positive_float(
                node.inputs.get("temperature", 1.0), "temperature"
            )
            value, weights = _weighted_consensus(conflict_state, temperature)
            return value, {"temperature": temperature, "weights": weights}
        if node.kind is CoordinationNodeKind.BEST_REWARD_SELECT:
            value, group_id, reward = _best_reward_select(conflict_state)
            return value, {"selected_group_id": group_id, "selected_reward": reward}
        if node.kind is CoordinationNodeKind.DAMPENING:
            base = _require_source_value(source_value, node.id)
            strength = _nonnegative_float(
                node.inputs.get("damping_strength", 0.5), "damping_strength"
            )
            intensity = conflict_intensity(conflict_state)
            damping = 1.0 / (1.0 + strength * intensity)
            value = conflict_state.current_value + damping * (
                base - conflict_state.current_value
            )
            return value, {
                "damping_strength": strength,
                "conflict_intensity": intensity,
                "damping_factor": damping,
            }
        if node.kind is CoordinationNodeKind.CLIP:
            base = _require_source_value(source_value, node.id)
            lower = float(node.inputs.get("lower", conflict_state.bounds[0]))
            upper = float(node.inputs.get("upper", conflict_state.bounds[1]))
            if lower > upper:
                raise ValueError("clip lower must be <= upper.")
            value = float(np.clip(base, lower, upper))
            return value, {"lower": lower, "upper": upper}
        if node.kind is CoordinationNodeKind.PROJECTION:
            if source_value is None:
                base = _average_consensus(conflict_state)
                source = "proposal_mean"
            else:
                base = _require_source_value(source_value, node.id)
                source = "input_source"
            return conflict_state.clip(base), {
                "projection": "bounds",
                "source": source,
            }
        if node.kind is CoordinationNodeKind.REWEIGHTING:
            temperature = _positive_float(
                node.inputs.get("temperature", 1.0), "temperature"
            )
            value, weights = _weighted_consensus(conflict_state, temperature)
            return value, {"temperature": temperature, "weights": weights}
        if node.kind is CoordinationNodeKind.REPAIR:
            base = (
                conflict_state.current_value
                if source_value is None
                else _require_source_value(source_value, node.id)
            )
            return conflict_state.clip(base), {"repair": "bounds_clip"}
        raise ValueError(f"Unsupported DSL runtime node kind: {node.kind.value}")


def _average_consensus(conflict_state: SharedVariableConflictState) -> float:
    return float(np.mean(conflict_state.proposals))


def _weighted_consensus(
    conflict_state: SharedVariableConflictState, temperature: float
) -> tuple[float, list[float]]:
    rewards = np.asarray(conflict_state.group_rewards, dtype=float)
    values = np.asarray(conflict_state.proposals, dtype=float)
    scaled = rewards / temperature
    scaled = scaled - float(np.max(scaled))
    weights = np.exp(scaled)
    weights = weights / float(np.sum(weights))
    return float(np.dot(weights, values)), [float(weight) for weight in weights]


def _best_reward_select(
    conflict_state: SharedVariableConflictState,
) -> tuple[float, int, float]:
    rewards = np.asarray(conflict_state.group_rewards, dtype=float)
    best_index = int(np.argmax(rewards))
    return (
        float(conflict_state.proposals[best_index]),
        int(conflict_state.related_group_ids[best_index]),
        float(rewards[best_index]),
    )


def _require_source_value(value: float | None, node_id: str) -> float:
    if value is None:
        raise ValueError(f"DSL node {node_id} requires an input source.")
    return float(value)


def _positive_float(value: Any, name: str) -> float:
    number = float(value)
    if number <= 0:
        raise ValueError(f"{name} must be positive.")
    return number


def _nonnegative_float(value: Any, name: str) -> float:
    number = float(value)
    if number < 0:
        raise ValueError(f"{name} must be nonnegative.")
    return number

"""Deterministic shared-variable conflict metrics."""

from __future__ import annotations

from typing import Any

import numpy as np

from .conflict_state import ConflictStateBatch, SharedVariableConflictState


def _finite_nonnegative(value: float) -> float:
    if not np.isfinite(value) or value < 0.0:
        return 0.0
    return float(value)


def value_disagreement(state: SharedVariableConflictState) -> float:
    if len(state.proposals) <= 1:
        return 0.0
    width = max(state.range_width, 1e-12)
    return _finite_nonnegative((max(state.proposals) - min(state.proposals)) / width)


def direction_disagreement(state: SharedVariableConflictState) -> float:
    directions = np.asarray(state.proposal_directions, dtype=float)
    nonzero = directions[np.abs(directions) > 1e-12]
    if nonzero.size <= 1:
        return 0.0
    has_positive = bool(np.any(nonzero > 0.0))
    has_negative = bool(np.any(nonzero < 0.0))
    if not (has_positive and has_negative):
        return 0.0
    positive = int(np.sum(nonzero > 0.0))
    negative = int(np.sum(nonzero < 0.0))
    total = int(nonzero.size)
    return _finite_nonnegative((2.0 * min(positive, negative)) / total)


def reward_disagreement(state: SharedVariableConflictState) -> float:
    rewards = np.asarray(state.group_rewards, dtype=float)
    if rewards.size <= 1:
        return 0.0
    scale = max(float(np.max(np.abs(rewards))), 1.0)
    return _finite_nonnegative(float(np.max(rewards) - np.min(rewards)) / scale)


def oscillation_score(state: SharedVariableConflictState) -> float:
    history = np.asarray(state.consensus_history, dtype=float)
    if history.size < 3:
        return 0.0
    deltas = np.diff(history)
    signs = np.sign(deltas[np.abs(deltas) > 1e-12])
    if signs.size <= 1:
        return 0.0
    changes = int(np.sum(signs[1:] != signs[:-1]))
    return _finite_nonnegative(changes / (signs.size - 1))


def conflict_intensity(state: SharedVariableConflictState) -> float:
    if len(state.proposals) <= 1:
        return 0.0
    value = value_disagreement(state)
    direction = direction_disagreement(state)
    reward = reward_disagreement(state)
    return _finite_nonnegative((value + direction + reward) / 3.0)


def metrics_for_state(state: SharedVariableConflictState) -> dict[str, float]:
    return {
        "value_disagreement": value_disagreement(state),
        "direction_disagreement": direction_disagreement(state),
        "reward_disagreement": reward_disagreement(state),
        "conflict_intensity": conflict_intensity(state),
        "oscillation_score": oscillation_score(state),
    }


def aggregate_conflict_metrics(
    batch: ConflictStateBatch,
    overlap_ratio: float,
) -> dict[str, Any]:
    rows = [metrics_for_state(state) for state in batch.states]
    if not rows:
        return {
            "mean_value_disagreement": 0.0,
            "mean_direction_disagreement": 0.0,
            "mean_reward_disagreement": 0.0,
            "mean_conflict_intensity": 0.0,
            "mean_oscillation_score": 0.0,
            "number_of_shared_variables": 0,
            "overlap_ratio": float(overlap_ratio),
            "per_variable": {},
        }

    per_variable = {
        str(state.variable_id): metrics_for_state(state) for state in batch.states
    }
    return {
        "mean_value_disagreement": float(
            np.mean([row["value_disagreement"] for row in rows])
        ),
        "mean_direction_disagreement": float(
            np.mean([row["direction_disagreement"] for row in rows])
        ),
        "mean_reward_disagreement": float(
            np.mean([row["reward_disagreement"] for row in rows])
        ),
        "mean_conflict_intensity": float(
            np.mean([row["conflict_intensity"] for row in rows])
        ),
        "mean_oscillation_score": float(
            np.mean([row["oscillation_score"] for row in rows])
        ),
        "number_of_shared_variables": len(batch.states),
        "overlap_ratio": float(overlap_ratio),
        "per_variable": per_variable,
    }

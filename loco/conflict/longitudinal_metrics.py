"""Longitudinal conflict diagnostics for Stage 2.1B."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def _finite_nonnegative(value: float) -> float:
    if not np.isfinite(value) or value < 0.0:
        return 0.0
    return float(value)


def _as_finite_array(values: Sequence[float]) -> np.ndarray:
    array = np.asarray(list(values), dtype=float)
    if array.size == 0:
        return np.asarray([], dtype=float)
    return array[np.isfinite(array)]


def longitudinal_conflict_reduction_ratio(
    conflict_before: Sequence[float],
    regenerated_conflict_next: Sequence[float],
) -> float:
    """Reduction from same-round before-conflict to next-round regenerated conflict."""

    before = _as_finite_array(conflict_before)
    regenerated = _as_finite_array(regenerated_conflict_next)
    if before.size == 0 or regenerated.size == 0:
        return 0.0
    baseline = float(np.mean(before))
    if baseline <= 1e-12:
        return 0.0
    reduction = (baseline - float(np.mean(regenerated))) / baseline
    return _finite_nonnegative(reduction)


def conflict_oscillation(conflict_values: Sequence[float]) -> float:
    values = _as_finite_array(conflict_values)
    if values.size < 3:
        return 0.0
    deltas = np.diff(values)
    signs = np.sign(deltas[np.abs(deltas) > 1e-12])
    if signs.size <= 1:
        return 0.0
    changes = int(np.sum(signs[1:] != signs[:-1]))
    return _finite_nonnegative(changes / (signs.size - 1))


def conflict_persistence_over_rounds(
    conflict_before: Sequence[float],
    regenerated_conflict_next: Sequence[float],
) -> float:
    before = _as_finite_array(conflict_before)
    regenerated = _as_finite_array(regenerated_conflict_next)
    count = min(before.size, regenerated.size)
    if count == 0:
        return 0.0
    ratios = []
    for previous, next_value in zip(before[:count], regenerated[:count]):
        if previous > 1e-12:
            ratios.append(max(0.0, float(next_value) / float(previous)))
    if not ratios:
        return 0.0
    return _finite_nonnegative(float(np.mean(ratios)))


def consensus_instability_over_rounds(
    consensus_history_by_variable: Mapping[int, Sequence[float]],
) -> float:
    per_variable_instability = []
    for history in consensus_history_by_variable.values():
        values = _as_finite_array(history)
        if values.size <= 1:
            continue
        per_variable_instability.append(float(np.std(np.diff(values))))
    if not per_variable_instability:
        return 0.0
    return _finite_nonnegative(float(np.mean(per_variable_instability)))


def objective_improvement_per_fe(
    objective_values: Sequence[float],
    fe_totals: Sequence[int],
) -> float:
    objectives = _as_finite_array(objective_values)
    fe = _as_finite_array(fe_totals)
    count = min(objectives.size, fe.size)
    if count <= 1:
        return 0.0
    fe_delta = float(fe[count - 1] - fe[0])
    if fe_delta <= 0:
        return 0.0
    improvement = float(objectives[0] - objectives[count - 1])
    return _finite_nonnegative(improvement / fe_delta)

"""Unified benchmark interface for LOCO-LSGO.

The interface deliberately hides benchmark metadata from operator-facing views.
Coordination operators must receive only structural overlap information, never
function IDs, benchmark names, hidden test metadata, or future evaluations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class LSGOProblem(ABC):
    """Common interface for MetaBox-backed and LOCO synthetic LSGO problems."""

    @abstractmethod
    def evaluate(self, x: np.ndarray) -> float:
        """Evaluate one candidate solution and return a scalar float."""

    @abstractmethod
    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Return lower and upper bounds as arrays of shape ``(D,)``."""

    @abstractmethod
    def dimension(self) -> int:
        """Return problem dimension D."""

    @abstractmethod
    def optimum_value(self) -> float | None:
        """Return known optimum value, or None when unavailable."""

    @abstractmethod
    def grouping(self) -> list[list[int]] | None:
        """Return groups ``G_k`` or None when grouping is unavailable."""

    @abstractmethod
    def shared_variables(self) -> set[int]:
        """Return shared variable set ``S = {i | m_i >= 2}``."""

    @abstractmethod
    def overlap_degree(self) -> dict[int, int]:
        """Return ``m_i`` for each variable index."""

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Return experiment-log metadata, not operator-facing metadata."""

    def operator_view(self) -> dict[str, Any]:
        """Return the maximum information an operator may see."""

        return {
            "dimension": self.dimension(),
            "grouping": self.grouping(),
            "shared_variables": self.shared_variables(),
            "overlap_degree": self.overlap_degree(),
        }


def assert_problem_contract(problem: LSGOProblem) -> None:
    """Validate the public interface without running optimization."""

    dim = problem.dimension()
    if not isinstance(dim, int) or dim <= 0:
        raise ValueError("dimension() must return a positive integer.")

    lower, upper = problem.bounds()
    lower = np.asarray(lower)
    upper = np.asarray(upper)
    if lower.shape != (dim,) or upper.shape != (dim,):
        raise ValueError("bounds() must return two arrays of shape (D,).")
    if np.any(lower >= upper):
        raise ValueError("Each lower bound must be less than the upper bound.")

    value = problem.evaluate((lower + upper) / 2.0)
    if not isinstance(value, float):
        raise ValueError("evaluate(x) must return float for one candidate.")

    groups = problem.grouping()
    if groups is not None:
        valid = set(range(dim))
        for group in groups:
            if not group:
                raise ValueError("Groups must be non-empty.")
            if not set(group).issubset(valid):
                raise ValueError("Group index out of bounds.")

    operator_view = problem.operator_view()
    forbidden_keys = {"metadata", "function_id", "benchmark_name", "true_optimum_location"}
    if forbidden_keys.intersection(operator_view):
        raise ValueError("Operator view exposes forbidden benchmark metadata.")


"""Adapter from MetaBox-v2 problem objects to the LOCO LSGOProblem interface."""

from __future__ import annotations

import importlib
from typing import Any

import numpy as np

from .overlap_metadata import OverlapMetadata, build_overlap_metadata
from .problem_interface import LSGOProblem


class MetaBoxImportError(ImportError):
    """Raised when MetaBox/metaevobox cannot be imported cleanly."""


def require_metaevobox():
    """Import metaevobox with a clear LOCO-facing error message."""

    try:
        return importlib.import_module("metaevobox")
    except Exception as exc:  # pragma: no cover - depends on external package state
        raise MetaBoxImportError(
            "metaevobox is required for MetaBox-backed benchmarks but is not "
            f"importable in this environment: {exc}"
        ) from exc


def _as_bound_array(value: Any, dimension: int, name: str) -> np.ndarray:
    if value is None:
        raise ValueError(f"MetaBox problem does not expose {name}.")
    array = np.asarray(value, dtype=float)
    if array.ndim == 0:
        return np.full(dimension, float(array))
    if array.shape == (dimension,):
        return array.astype(float, copy=False)
    raise ValueError(f"MetaBox {name} has shape {array.shape}, expected scalar or ({dimension},).")


class MetaBoxProblemAdapter(LSGOProblem):
    """Wrap a MetaBox problem without mutating its objective implementation."""

    def __init__(self, metabox_problem, grouping=None, metadata=None):
        self.metabox_problem = metabox_problem
        self._metadata = dict(metadata or {})
        self.fe_count = int(getattr(metabox_problem, "numevals", 0) or 0)
        self._groups = [list(map(int, group)) for group in grouping] if grouping is not None else None
        self._overlap_metadata: OverlapMetadata | None = None
        if self._groups is not None:
            self._overlap_metadata = build_overlap_metadata(
                self._groups,
                self.dimension(),
                topology=self._metadata.get("topology", "metabox"),
                grouping_source=self._metadata.get("grouping_source", "metabox_adapter"),
                grouping_confidence=self._metadata.get("grouping_confidence", "medium"),
            )

    def evaluate(self, x: np.ndarray) -> float:
        vector = np.asarray(x, dtype=float)
        if vector.shape != (self.dimension(),):
            raise ValueError(f"Expected x shape ({self.dimension()},), got {vector.shape}.")

        before = int(getattr(self.metabox_problem, "numevals", self.fe_count) or self.fe_count)
        if hasattr(self.metabox_problem, "eval"):
            value = self.metabox_problem.eval(vector)
        elif hasattr(self.metabox_problem, "func"):
            value = self.metabox_problem.func(vector.reshape(1, -1))[0]
        else:
            raise ValueError("MetaBox problem exposes neither eval(x) nor func(x).")

        self.fe_count += 1
        after = int(getattr(self.metabox_problem, "numevals", before) or before)
        if after <= before and hasattr(self.metabox_problem, "numevals"):
            setattr(self.metabox_problem, "numevals", before + 1)
        return float(np.asarray(value).reshape(-1)[0])

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return (
            _as_bound_array(getattr(self.metabox_problem, "lb", None), self.dimension(), "lb"),
            _as_bound_array(getattr(self.metabox_problem, "ub", None), self.dimension(), "ub"),
        )

    def dimension(self) -> int:
        return int(
            getattr(
                self.metabox_problem,
                "dimension",
                getattr(self.metabox_problem, "dim", 0),
            )
        )

    def optimum_value(self) -> float | None:
        if hasattr(self.metabox_problem, "get_optimal"):
            value = self.metabox_problem.get_optimal()
            if value is not None:
                return float(value)
        for name in ("opt", "optimum"):
            value = getattr(self.metabox_problem, name, None)
            if value is not None:
                return float(value)
        return None

    def grouping(self) -> list[list[int]] | None:
        return [list(group) for group in self._groups] if self._groups is not None else None

    def shared_variables(self) -> set[int]:
        if self._overlap_metadata is None:
            return set()
        return set(self._overlap_metadata.shared_variables)

    def overlap_degree(self) -> dict[int, int]:
        if self._overlap_metadata is None:
            return {i: 0 for i in range(self.dimension())}
        return dict(self._overlap_metadata.overlap_degree)

    def metadata(self) -> dict[str, Any]:
        data = dict(self._metadata)
        data.setdefault("source", "metabox")
        data.setdefault("adapter", "MetaBoxProblemAdapter")
        data["fe_count"] = self.fe_count
        return data


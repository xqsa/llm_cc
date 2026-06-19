"""MetaBox-backed CEC2013LSGO loaders for LOCO-LSGO."""

from __future__ import annotations

import importlib

import numpy as np

from .metabox_adapter import MetaBoxImportError, MetaBoxProblemAdapter
from .problem_interface import LSGOProblem


OVERLAP_FUNCTION_IDS = [12, 13, 14]


def _import_cec2013lsgo_module():
    try:
        return importlib.import_module("metaevobox.environment.problem.SOO.CEC2013LSGO")
    except Exception as exc:  # pragma: no cover - depends on external package state
        raise MetaBoxImportError(
            "Cannot import MetaBox CEC2013LSGO from metaevobox. Install a working "
            f"metaevobox package and its runtime dependencies. Original error: {exc}"
        ) from exc


def reconstruct_cec2013lsgo_grouping(problem) -> tuple[list[list[int]] | None, str, str]:
    """Reconstruct groups from CEC2013LSGO Pvector/s/overlap metadata."""

    pvector = getattr(problem, "Pvector", None)
    sizes = getattr(problem, "s", None)
    if pvector is None or sizes is None:
        return None, "unknown", "low"

    pvector = np.asarray(pvector, dtype=int)
    sizes = np.asarray(sizes, dtype=int)
    overlap = int(getattr(problem, "overlap", 0) or 0)
    groups: list[list[int]] = []
    cursor = 0
    for i, size in enumerate(sizes):
        start = cursor - i * overlap
        end = cursor + int(size) - i * overlap
        if start < 0 or end > len(pvector) or end <= start:
            return None, "unknown", "low"
        groups.append([int(index) for index in pvector[start:end]])
        cursor += int(size)

    source = "cec2013lsgo_pvector_overlap" if overlap > 0 else "cec2013lsgo_pvector"
    return groups, source, "high"


def load_cec2013lsgo_problem(function_id: int, version: str = "numpy") -> LSGOProblem:
    """Load a CEC2013LSGO problem through MetaBox and wrap it as LSGOProblem."""

    if function_id < 1 or function_id > 15:
        raise ValueError("CEC2013LSGO function_id must be in [1, 15].")
    module = _import_cec2013lsgo_module()
    suffix = "" if version == "numpy" else "_Torch"
    class_name = f"F{function_id}{suffix}"
    try:
        cls = getattr(module, class_name)
    except AttributeError as exc:
        raise MetaBoxImportError(f"MetaBox CEC2013LSGO class {class_name} is unavailable.") from exc

    raw_problem = cls()
    groups, grouping_source, grouping_confidence = reconstruct_cec2013lsgo_grouping(raw_problem)
    metadata = {
        "name": f"cec2013lsgo_f{function_id}",
        "source": "metabox_cec2013lsgo",
        "function_id": function_id,
        "version": version,
        "license": "MetaBox BSD-3-Clause; CEC2013LSGO implementation noted as GPL-3.0 in MetaBox docs",
        "grouping_source": grouping_source,
        "grouping_confidence": grouping_confidence,
        "topology": "cec2013lsgo_overlap" if function_id in OVERLAP_FUNCTION_IDS else "cec2013lsgo",
    }
    return MetaBoxProblemAdapter(raw_problem, grouping=groups, metadata=metadata)


def load_cec2013lsgo_suite(function_ids: list[int], version: str = "numpy") -> list[LSGOProblem]:
    return [load_cec2013lsgo_problem(function_id, version=version) for function_id in function_ids]


def load_cec2013lsgo_overlap_suite() -> list[LSGOProblem]:
    return load_cec2013lsgo_suite(OVERLAP_FUNCTION_IDS, version="numpy")


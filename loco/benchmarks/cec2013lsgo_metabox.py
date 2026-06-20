"""MetaBox-backed CEC2013LSGO loaders for LOCO-LSGO."""

from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path
from contextlib import contextmanager

import numpy as np

from .overlap_metadata import build_overlap_metadata
from .metabox_adapter import MetaBoxImportError, MetaBoxProblemAdapter
from .problem_interface import LSGOProblem


OVERLAP_FUNCTION_IDS = [12, 13, 14]
PVECTOR_GROUPING_FUNCTION_IDS = {13, 14}

FUNCTION_SEMANTICS = {
    12: {
        "D_formula": 1000,
        "overlap_semantics": "rosenbrock_chain_overlap",
        "official_definition": "shifted_rosenbrock_chain",
        "grouping_status": "unavailable",
        "grouping_source": "unavailable",
        "grouping_confidence": "none",
    },
    13: {
        "D_formula": 905,
        "overlap_semantics": "conforming_overlap",
        "official_definition": "shifted_schwefel_conforming_overlapping_subcomponents",
    },
    14: {
        "D_formula": 905,
        "overlap_semantics": "conflicting_overlap",
        "official_definition": "shifted_schwefel_conflicting_overlapping_subcomponents",
    },
}


def _import_cec2013lsgo_module():
    benchmark_only_error = None
    try:
        return _import_cec2013lsgo_numpy_benchmark_only()
    except Exception as exc:  # pragma: no cover - environment dependent
        benchmark_only_error = exc

    try:
        return importlib.import_module("metaevobox.environment.problem.SOO.CEC2013LSGO")
    except Exception as exc:  # pragma: no cover - depends on external package state
        raise MetaBoxImportError(
            "Cannot import MetaBox CEC2013LSGO from metaevobox. Install a working "
            "metaevobox package and its runtime dependencies. "
            f"Benchmark-only import error: {benchmark_only_error}. "
            f"Normal import error: {exc}"
        ) from exc


def _ensure_alias_package(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module


def _load_module_from_file(name: str, path: Path):
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise MetaBoxImportError(f"Cannot create module spec for {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _import_cec2013lsgo_numpy_benchmark_only():
    """Load MetaBox CEC2013LSGO numpy classes without executing metaevobox.__init__."""

    package_spec = importlib.util.find_spec("metaevobox")
    if package_spec is None or not package_spec.submodule_search_locations:
        raise MetaBoxImportError("metaevobox package is not installed.")

    root = Path(next(iter(package_spec.submodule_search_locations)))
    problem_root = root / "environment" / "problem"
    cec_root = problem_root / "SOO" / "CEC2013LSGO"
    basic_problem = problem_root / "basic_problem.py"
    cec_numpy = cec_root / "cec2013lsgo_numpy.py"
    if not basic_problem.is_file() or not cec_numpy.is_file():
        raise MetaBoxImportError(
            "Installed metaevobox does not contain CEC2013LSGO numpy files."
        )

    alias_root = Path(str(root))
    _ensure_alias_package("loco_external_metaevobox", alias_root)
    _ensure_alias_package(
        "loco_external_metaevobox.environment", alias_root / "environment"
    )
    _ensure_alias_package("loco_external_metaevobox.environment.problem", problem_root)
    _ensure_alias_package(
        "loco_external_metaevobox.environment.problem.SOO", problem_root / "SOO"
    )
    _ensure_alias_package(
        "loco_external_metaevobox.environment.problem.SOO.CEC2013LSGO",
        cec_root,
    )

    _load_module_from_file(
        "loco_external_metaevobox.environment.problem.basic_problem",
        basic_problem,
    )
    return _load_module_from_file(
        "loco_external_metaevobox.environment.problem.SOO.CEC2013LSGO.cec2013lsgo_numpy",
        cec_numpy,
    )


@contextmanager
def _force_local_cec_datafiles():
    original_find_spec = importlib.util.find_spec

    def guarded_find_spec(name, *args, **kwargs):
        if name == "metaevobox.environment.problem.SOO.CEC2013LSGO.datafile":
            return None
        return original_find_spec(name, *args, **kwargs)

    importlib.util.find_spec = guarded_find_spec
    try:
        yield
    finally:
        importlib.util.find_spec = original_find_spec


def reconstruct_cec2013lsgo_grouping(
    problem,
) -> tuple[list[list[int]] | None, str, str]:
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


def _dimension_metadata(problem, function_id: int) -> dict[str, int]:
    semantics = FUNCTION_SEMANTICS.get(function_id, {})
    formula = int(
        semantics.get(
            "D_formula", getattr(problem, "dimension", getattr(problem, "dim", 0))
        )
    )
    api = int(getattr(problem, "dim", getattr(problem, "dimension", formula)))
    return {
        "D_formula": formula,
        "D_api": api,
    }


def _runtime_dimension_for_function(
    problem, function_id: int
) -> tuple[int | None, dict[str, object]]:
    if function_id != 13:
        return None, {
            "runtime_dimension": int(
                getattr(problem, "dimension", getattr(problem, "dim", 0))
            ),
            "adapter_mode": "direct_metabox_dimension",
        }

    api_dimension = int(getattr(problem, "dim", 0) or 0)
    formula_dimension = int(
        getattr(problem, "dimension", api_dimension) or api_dimension
    )
    ovector = getattr(problem, "Ovector", None)
    ovector_size = int(np.asarray(ovector).size) if ovector is not None else 0
    if (
        api_dimension
        and ovector_size == api_dimension
        and api_dimension != formula_dimension
    ):
        return api_dimension, {
            "runtime_dimension": api_dimension,
            "adapter_mode": "implementation_api_adapter",
            "adapter_reason": "metabox_f13_ovector_requires_D_api",
            "adapter_preserves_D_formula": True,
        }
    return None, {
        "runtime_dimension": formula_dimension,
        "adapter_mode": "direct_metabox_dimension",
    }


def _shared_count_and_ratio(
    groups: list[list[int]] | None, dimension: int
) -> tuple[int, float]:
    if groups is None:
        return 0, 0.0
    metadata = build_overlap_metadata(
        groups,
        dimension,
        topology="cec2013lsgo_overlap",
        grouping_source="cec2013lsgo_semantics_probe",
        grouping_confidence="high",
    )
    return len(metadata.shared_variables), metadata.overlap_ratio


def _extract_grouping_for_function(
    problem, function_id: int
) -> tuple[list[list[int]] | None, dict[str, object]]:
    semantics = FUNCTION_SEMANTICS.get(function_id, {})
    metadata: dict[str, object] = {
        "overlap_semantics": semantics.get("overlap_semantics", "not_recorded"),
        "official_definition": semantics.get("official_definition", "not_recorded"),
    }
    metadata.update(_dimension_metadata(problem, function_id))

    if function_id not in PVECTOR_GROUPING_FUNCTION_IDS:
        metadata.update(
            {
                "grouping_status": semantics.get("grouping_status", "unavailable"),
                "grouping_source": semantics.get("grouping_source", "unavailable"),
                "grouping_confidence": semantics.get("grouping_confidence", "none"),
                "overlap_size": None,
                "shared_variable_count": 0,
                "overlap_ratio": 0.0,
            }
        )
        return None, metadata

    groups, _source, confidence = reconstruct_cec2013lsgo_grouping(problem)
    if groups is None:
        metadata.update(
            {
                "grouping_status": "unavailable",
                "grouping_source": "unavailable",
                "grouping_confidence": confidence,
                "overlap_size": int(getattr(problem, "overlap", 0) or 0),
                "shared_variable_count": 0,
                "overlap_ratio": 0.0,
            }
        )
        return None, metadata

    shared_count, overlap_ratio = _shared_count_and_ratio(
        groups, int(metadata["D_formula"])
    )
    metadata.update(
        {
            "grouping_status": "available",
            "grouping_source": "cec2013lsgo_f13_f14_pvector_s_overlap",
            "grouping_confidence": confidence,
            "overlap_size": int(getattr(problem, "overlap", 0) or 0),
            "shared_variable_count": shared_count,
            "overlap_ratio": overlap_ratio,
        }
    )
    return groups, metadata


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
        raise MetaBoxImportError(
            f"MetaBox CEC2013LSGO class {class_name} is unavailable."
        ) from exc

    with _force_local_cec_datafiles():
        raw_problem = cls()
    groups, semantics_metadata = _extract_grouping_for_function(
        raw_problem, function_id
    )
    metadata = {
        "name": f"cec2013lsgo_f{function_id}",
        "source": "metabox_cec2013lsgo",
        "function_id": function_id,
        "version": version,
        "license": "MetaBox BSD-3-Clause; CEC2013LSGO implementation noted as GPL-3.0 in MetaBox docs",
        "topology": (
            "cec2013lsgo_overlap"
            if function_id in OVERLAP_FUNCTION_IDS
            else "cec2013lsgo"
        ),
    }
    metadata.update(semantics_metadata)
    runtime_dimension, runtime_metadata = _runtime_dimension_for_function(
        raw_problem, function_id
    )
    metadata.update(runtime_metadata)
    return MetaBoxProblemAdapter(
        raw_problem,
        grouping=groups,
        metadata=metadata,
        runtime_dimension=runtime_dimension,
    )


def load_cec2013lsgo_suite(
    function_ids: list[int], version: str = "numpy"
) -> list[LSGOProblem]:
    return [
        load_cec2013lsgo_problem(function_id, version=version)
        for function_id in function_ids
    ]


def load_cec2013lsgo_overlap_suite() -> list[LSGOProblem]:
    return load_cec2013lsgo_suite(OVERLAP_FUNCTION_IDS, version="numpy")

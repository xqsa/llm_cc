"""Stage 1.8 MetaBox F13/F14 internal dimension probe.

This diagnostic script reads MetaBox CEC2013LSGO numpy internals and evaluates
shape behavior. It does not patch MetaBox, pad inputs, or modify the LOCO
adapter.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loco.benchmarks.cec2013lsgo_metabox import (  # noqa: E402
    _force_local_cec_datafiles,
    _import_cec2013lsgo_numpy_benchmark_only,
)


def _shape(value: Any) -> list[int] | None:
    if value is None:
        return None
    return [int(item) for item in np.asarray(value).shape]


def _finite_float(value: Any) -> bool:
    try:
        return math.isfinite(float(np.asarray(value).reshape(-1)[0]))
    except Exception:
        return False


def _evaluate(problem: Any, dimension: int, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    lower = float(getattr(problem, "lb", -100.0))
    upper = float(getattr(problem, "ub", 100.0))
    x = rng.uniform(lower, upper, size=dimension)
    try:
        value = problem.func(x.reshape(1, -1))[0]
    except Exception as exc:
        return {
            "ok": False,
            "dimension": dimension,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "ok": True,
        "dimension": dimension,
        "value": float(np.asarray(value).reshape(-1)[0]),
        "finite": _finite_float(value),
    }


def _problem_report(cls: type, label: str, seed: int) -> dict[str, Any]:
    report: dict[str, Any] = {
        "label": label,
        "construction_ok": False,
    }
    try:
        with _force_local_cec_datafiles():
            problem = cls()
    except Exception as exc:
        report["construction_error"] = f"{type(exc).__name__}: {exc}"
        return report

    report.update(
        {
            "construction_ok": True,
            "class_name": cls.__name__,
            "dimension": int(getattr(problem, "dimension", 0) or 0),
            "dim": int(getattr(problem, "dim", 0) or 0),
            "overlap": getattr(problem, "overlap", None),
            "s_shape": _shape(getattr(problem, "s", None)),
            "s_sum": (
                int(np.asarray(getattr(problem, "s")).sum())
                if getattr(problem, "s", None) is not None
                else None
            ),
            "pvector_shape": _shape(getattr(problem, "Pvector", None)),
            "ovector_shape": _shape(getattr(problem, "Ovector", None)),
            "ovector_vec_len": (
                len(getattr(problem, "OvectorVec"))
                if getattr(problem, "OvectorVec", None) is not None
                else None
            ),
            "ovector_vec_shapes": [
                _shape(item) for item in getattr(problem, "OvectorVec", []) or []
            ],
        }
    )
    dimensions = {
        int(report["dimension"]),
        int(report["dim"]),
    }
    for dimension in sorted(dimensions):
        report[f"evaluate_{dimension}"] = _evaluate(
            problem, dimension=dimension, seed=seed + dimension
        )
    return report


def run_probe(seed: int = 0) -> dict[str, Any]:
    result: dict[str, Any] = {
        "stage": "1.8",
        "name": "metabox_f13_internal_dimension_probe",
        "status": "FAIL",
        "summary": "",
        "claim_boundary": {
            "adapter_modified": False,
            "objective_reimplemented": False,
            "padding_applied": False,
            "optimizer_implemented": False,
        },
        "functions": {},
    }
    try:
        module = _import_cec2013lsgo_numpy_benchmark_only()
    except Exception as exc:
        result["status"] = "SKIP"
        result["summary"] = f"{type(exc).__name__}: {exc}"
        return result

    result["module"] = module.__name__
    result["functions"] = {
        "F13": _problem_report(module.F13, "F13", seed + 13),
        "F14": _problem_report(module.F14, "F14", seed + 14),
    }

    f13 = result["functions"]["F13"]
    f14 = result["functions"]["F14"]
    f13_mismatch = bool(
        f13.get("dimension") == 905
        and f13.get("dim") == 1000
        and f13.get("ovector_shape") == [1000]
        and f13.get("evaluate_905", {}).get("ok") is False
        and f13.get("evaluate_1000", {}).get("ok") is True
    )
    f14_compatible = bool(
        f14.get("dimension") == 905
        and f14.get("dim") == 1000
        and f14.get("evaluate_905", {}).get("ok") is True
    )
    f14_dual_input_compatible = bool(
        f14_compatible and f14.get("evaluate_1000", {}).get("ok") is True
    )
    result["diagnosis"] = {
        "f13_internal_ovector_dim_mismatch": f13_mismatch,
        "f14_905_eval_compatible": f14_compatible,
        "f14_dual_input_eval_compatible": f14_dual_input_compatible,
        "recommended_next_action": (
            "Treat F13 as a MetaBox internal dimension-semantics probe before "
            "adding any implementation_api_adapter."
        ),
    }
    if f13_mismatch and f14_compatible:
        result["status"] = "PARTIAL"
        result["summary"] = (
            "F13 constructs with dimension=905 and dim=1000, but its Ovector is "
            "1000-long; F14 evaluates at 905 through OvectorVec."
        )
    elif all(item.get("construction_ok") for item in result["functions"].values()):
        result["status"] = "PASS"
        result["summary"] = "F13/F14 internal dimension probe completed."
    else:
        result["summary"] = "F13/F14 construction probe failed."
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    result = run_probe(seed=args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(text + "\n", encoding="utf-8")
    return 0 if result["status"] in {"PASS", "PARTIAL", "SKIP"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

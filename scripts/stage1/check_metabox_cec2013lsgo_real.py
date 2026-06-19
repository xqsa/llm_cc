"""Real MetaBox CEC2013LSGO benchmark-only smoke test.

This script never uses fake modules. It probes the installed MetaBox/metaevobox
package, loads F12/F13/F14 through the LOCO adapter, and reports whether the
real benchmark path can evaluate candidates without NaN/Inf.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loco.benchmarks.cec2013lsgo_metabox import (
    OVERLAP_FUNCTION_IDS,
    _import_cec2013lsgo_numpy_benchmark_only,
    load_cec2013lsgo_problem,
)


def _normal_import_probe() -> dict[str, Any]:
    command = [
        sys.executable,
        "-c",
        "import importlib; importlib.import_module('metaevobox.environment.problem.SOO.CEC2013LSGO'); print('ok')",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=45,
        cwd=str(ROOT),
    )
    if completed.returncode == 0:
        return {
            "ok": True,
            "module": "metaevobox.environment.problem.SOO.CEC2013LSGO",
            "error": None,
            "stdout_tail": completed.stdout[-1000:],
            "stderr_tail": completed.stderr[-1000:],
        }
    return {
        "ok": False,
        "module": "metaevobox.environment.problem.SOO.CEC2013LSGO",
        "error": f"returncode={completed.returncode}",
        "stdout_tail": completed.stdout[-1000:],
        "stderr_tail": completed.stderr[-3000:],
    }

def _benchmark_only_import_probe() -> dict[str, Any]:
    try:
        module = _import_cec2013lsgo_numpy_benchmark_only()
        return {"ok": True, "module": module.__name__, "error": None}
    except Exception as exc:
        return {
            "ok": False,
            "module": "loco benchmark-only loader",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _finite_float(value: float) -> bool:
    return isinstance(value, float) and math.isfinite(value)


def _smoke_one(function_id: int, seed: int) -> dict[str, Any]:
    item: dict[str, Any] = {"function_id": function_id, "ok": False, "checks": {}}
    try:
        problem = load_cec2013lsgo_problem(function_id, version="numpy")
        dimension = problem.dimension()
        metadata = problem.metadata()
        item["checks"]["load"] = True
        item["checks"]["dimension"] = dimension
        item["checks"]["expected_dimension"] = 905 if function_id in (13, 14) else 1000
        item["checks"]["dimension_ok"] = dimension == item["checks"]["expected_dimension"]
        item["checks"]["D_formula"] = metadata.get("D_formula")
        item["checks"]["D_api"] = metadata.get("D_api")
        item["checks"]["dimension_metadata_recorded"] = (
            isinstance(metadata.get("D_formula"), int) and isinstance(metadata.get("D_api"), int)
        )

        lower, upper = problem.bounds()
        item["checks"]["bounds_shape_ok"] = lower.shape == (dimension,) and upper.shape == (dimension,)
        item["checks"]["bounds_finite"] = bool(np.all(np.isfinite(lower)) and np.all(np.isfinite(upper)))

        optimum = problem.optimum_value()
        item["checks"]["optimum_value"] = optimum
        item["checks"]["optimum_readable_or_none"] = optimum is None or isinstance(optimum, float)

        raw = problem.metabox_problem
        item["checks"]["pvector_readable"] = getattr(raw, "Pvector", None) is not None
        item["checks"]["s_readable"] = getattr(raw, "s", None) is not None
        item["checks"]["overlap_readable"] = getattr(raw, "overlap", None) is not None

        groups = problem.grouping()
        item["checks"]["groups_recovered"] = groups is not None
        item["checks"]["shared_variables_nonempty"] = bool(problem.shared_variables())
        item["checks"]["grouping_status"] = metadata.get("grouping_status")
        item["checks"]["grouping_status_valid"] = metadata.get("grouping_status") in {"available", "unavailable"}
        item["checks"]["grouping_required"] = function_id in (13, 14)
        item["checks"]["group_count"] = len(groups) if groups is not None else 0
        item["checks"]["overlap_size"] = metadata.get("overlap_size")
        item["checks"]["shared_variable_count"] = metadata.get("shared_variable_count")
        item["checks"]["overlap_ratio"] = metadata.get("overlap_ratio")
        item["checks"]["official_overlap_metadata_ok"] = bool(
            metadata.get("D_formula") == 905
            and metadata.get("D_api") == 1000
            and item["checks"]["group_count"] == 20
            and metadata.get("overlap_size") == 5
            and metadata.get("shared_variable_count") == 95
            and np.isclose(float(metadata.get("overlap_ratio", -1.0)), 95 / 905)
        )
        if problem._overlap_metadata is not None:
            incidence = problem._overlap_metadata.incidence_matrix
            item["checks"]["incidence_shape"] = list(incidence.shape)
            item["checks"]["incidence_shape_ok"] = incidence.shape[0] == dimension
        else:
            item["checks"]["incidence_shape"] = None
            item["checks"]["incidence_shape_ok"] = function_id == 12

        zero_value = problem.evaluate(np.zeros(dimension))
        rng = np.random.default_rng(seed)
        random_x = rng.uniform(lower, upper)
        random_value_1 = problem.evaluate(random_x)
        random_value_2 = problem.evaluate(random_x.copy())
        item["checks"]["zero_value"] = zero_value
        item["checks"]["random_value_1"] = random_value_1
        item["checks"]["random_value_2"] = random_value_2
        item["checks"]["finite_values"] = all(
            _finite_float(value) for value in (zero_value, random_value_1, random_value_2)
        )
        item["checks"]["deterministic_random_eval"] = random_value_1 == random_value_2

        required = [
            "dimension_ok",
            "dimension_metadata_recorded",
            "bounds_shape_ok",
            "bounds_finite",
            "optimum_readable_or_none",
            "grouping_status_valid",
            "incidence_shape_ok",
            "finite_values",
            "deterministic_random_eval",
        ]
        if function_id in (13, 14):
            required.extend(
                [
                    "groups_recovered",
                    "shared_variables_nonempty",
                    "official_overlap_metadata_ok",
                ]
            )
        item["ok"] = all(bool(item["checks"].get(name)) for name in required)
    except Exception as exc:
        item["error"] = f"{type(exc).__name__}: {exc}"
    return item


def run_smoke(seed: int = 0, include_normal_import: bool = True) -> dict[str, Any]:
    normal_import = _normal_import_probe() if include_normal_import else {
        "ok": None,
        "module": "metaevobox.environment.problem.SOO.CEC2013LSGO",
        "error": "not run",
    }
    benchmark_only_import = _benchmark_only_import_probe()
    result: dict[str, Any] = {
        "stage": "1.5",
        "name": "metabox_cec2013lsgo_real_smoke",
        "normal_import": normal_import,
        "benchmark_only_import": benchmark_only_import,
        "functions": [],
        "status": "FAIL",
        "summary": "",
    }

    if not benchmark_only_import["ok"]:
        result["status"] = "SKIP"
        result["summary"] = benchmark_only_import["error"] or "MetaBox benchmark-only import unavailable."
        return result

    result["functions"] = [_smoke_one(function_id, seed + function_id) for function_id in OVERLAP_FUNCTION_IDS]
    if all(item["ok"] for item in result["functions"]):
        result["status"] = "PASS"
        result["summary"] = "Real MetaBox F12/F13/F14 loaded and evaluated through LOCO adapter."
    else:
        result["status"] = "PARTIAL"
        blockers = [
            f"F{item['function_id']}: {item.get('error', 'failed checks')}"
            for item in result["functions"]
            if not item["ok"]
        ]
        result["summary"] = "; ".join(blockers)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--skip-normal-import-probe", action="store_true")
    args = parser.parse_args()

    result = run_smoke(seed=args.seed, include_normal_import=not args.skip_normal_import_probe)
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(text + "\n", encoding="utf-8")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Run Stage 8.14 CEC2013 single-run smoke and route decision."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.cec2013_single_run_smoke_decision import (  # noqa: E402
    DEFAULT_SMOKE_MAX_FE,
    run_stage8_14_cec2013_single_run_smoke_decision,
)


def main() -> None:
    stage8_13_dir = ROOT / "artifacts" / "objective_eval" / "stage8_13"
    summary = run_stage8_14_cec2013_single_run_smoke_decision(
        stage8_13_design_report_path=stage8_13_dir / "formal_sota_experiment_design.json",
        stage8_13_budget_lock_path=stage8_13_dir / "budget_lock.json",
        stage8_13_function_scope_path=stage8_13_dir / "function_scope_lock.json",
        stage8_13_claim_gate_path=stage8_13_dir / "claim_gate.json",
        stage8_13_runtime_boundary_path=stage8_13_dir / "runtime_boundary.json",
        stage8_13_next_route_path=stage8_13_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_14",
        smoke_max_fe=DEFAULT_SMOKE_MAX_FE,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

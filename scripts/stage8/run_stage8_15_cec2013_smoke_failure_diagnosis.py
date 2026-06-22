"""Run Stage 8.15 failure-honest CEC2013 smoke diagnosis."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.cec2013_smoke_failure_diagnosis import (  # noqa: E402
    run_stage8_15_cec2013_smoke_failure_diagnosis,
)


def main() -> None:
    stage8_14_dir = ROOT / "artifacts" / "objective_eval" / "stage8_14"
    summary = run_stage8_15_cec2013_smoke_failure_diagnosis(
        stage8_14_smoke_report_path=stage8_14_dir / "single_run_smoke_report.json",
        stage8_14_win_loss_path=stage8_14_dir / "win_loss_report.json",
        stage8_14_method_summary_path=stage8_14_dir / "method_summary.json",
        stage8_14_objective_trace_path=stage8_14_dir / "objective_trace.jsonl",
        stage8_14_fe_ledger_path=stage8_14_dir / "fe_ledger.json",
        stage8_14_runtime_boundary_path=stage8_14_dir / "runtime_boundary.json",
        stage8_14_next_route_path=stage8_14_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_15",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

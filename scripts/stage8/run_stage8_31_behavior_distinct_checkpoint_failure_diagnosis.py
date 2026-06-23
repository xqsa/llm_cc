"""Run Stage 8.31 behavior-distinct checkpoint failure diagnosis."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.behavior_distinct_checkpoint_failure_diagnosis import (  # noqa: E402
    run_stage8_31_behavior_distinct_checkpoint_failure_diagnosis,
)


def main() -> None:
    stage8_30_dir = ROOT / "artifacts" / "objective_eval" / "stage8_30"
    report = run_stage8_31_behavior_distinct_checkpoint_failure_diagnosis(
        stage8_30_checkpoint_report_path=stage8_30_dir / "checkpoint_pilot_report.json",
        stage8_30_win_loss_path=stage8_30_dir / "win_loss_report.json",
        stage8_30_method_summary_path=stage8_30_dir / "method_summary.json",
        stage8_30_policy_branch_path=stage8_30_dir / "policy_branch_report.json",
        stage8_30_fe_ledger_path=stage8_30_dir / "fe_ledger.json",
        stage8_30_runtime_boundary_path=stage8_30_dir / "runtime_boundary.json",
        stage8_30_next_route_path=stage8_30_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "analysis" / "stage8_31",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

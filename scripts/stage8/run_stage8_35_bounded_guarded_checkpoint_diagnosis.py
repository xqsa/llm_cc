"""Run Stage 8.35 bounded guarded checkpoint diagnosis."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.bounded_guarded_checkpoint_diagnosis import (  # noqa: E402
    run_stage8_35_bounded_guarded_checkpoint_diagnosis,
)


def main() -> None:
    stage8_34_dir = ROOT / "artifacts" / "objective_eval" / "stage8_34"
    report = run_stage8_35_bounded_guarded_checkpoint_diagnosis(
        stage8_34_checkpoint_report_path=stage8_34_dir
        / "bounded_guarded_checkpoint_report.json",
        stage8_34_case_table_path=stage8_34_dir / "guarded_case_delta_table.jsonl",
        stage8_34_win_loss_path=stage8_34_dir / "win_loss_report.json",
        stage8_34_branch_report_path=stage8_34_dir
        / "guarded_policy_branch_report.json",
        stage8_34_fe_ledger_path=stage8_34_dir / "fe_ledger.json",
        stage8_34_runtime_boundary_path=stage8_34_dir / "runtime_boundary.json",
        stage8_34_next_route_path=stage8_34_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "analysis" / "stage8_35",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

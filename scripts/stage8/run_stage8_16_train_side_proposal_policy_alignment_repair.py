"""Run Stage 8.16 train-side proposal/policy alignment repair."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.train_side_proposal_policy_alignment_repair import (  # noqa: E402
    run_stage8_16_train_side_proposal_policy_alignment_repair,
)


def main() -> None:
    stage8_15_dir = ROOT / "artifacts" / "objective_eval" / "stage8_15"
    summary = run_stage8_16_train_side_proposal_policy_alignment_repair(
        stage8_15_diagnosis_report_path=stage8_15_dir / "diagnosis_report.json",
        stage8_15_method_gap_path=stage8_15_dir / "method_gap_report.json",
        stage8_15_branch_diagnostics_path=stage8_15_dir / "branch_diagnostics.json",
        stage8_15_root_cause_path=stage8_15_dir / "root_cause_hypotheses.json",
        stage8_15_fe_ledger_path=stage8_15_dir / "fe_ledger.json",
        stage8_15_runtime_boundary_path=stage8_15_dir / "runtime_boundary.json",
        stage8_15_next_route_path=stage8_15_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_16",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Run Stage 8.17 bounded repaired-policy objective check."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.bounded_repaired_policy_objective_check import (  # noqa: E402
    run_stage8_17_bounded_repaired_policy_objective_check,
)


def main() -> None:
    stage8_16_dir = ROOT / "artifacts" / "objective_eval" / "stage8_16"
    summary = run_stage8_17_bounded_repaired_policy_objective_check(
        stage8_16_alignment_report_path=stage8_16_dir / "alignment_repair_report.json",
        stage8_16_feature_report_path=stage8_16_dir
        / "reward_reliability_feature_report.json",
        stage8_16_branch_report_path=stage8_16_dir
        / "policy_branch_alignment_report.json",
        stage8_16_fe_ledger_path=stage8_16_dir / "fe_ledger.json",
        stage8_16_runtime_boundary_path=stage8_16_dir / "runtime_boundary.json",
        stage8_16_next_route_path=stage8_16_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_17",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

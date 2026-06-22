"""Run Stage 8.7 conditional proposal-state policy ablation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.conditional_proposal_state_policy import (  # noqa: E402
    run_stage8_7_conditional_policy_ablation,
)


def main() -> None:
    stage8_6_dir = ROOT / "artifacts" / "objective_eval" / "stage8_6"
    summary = run_stage8_7_conditional_policy_ablation(
        stage8_6_case_table_path=stage8_6_dir / "ablation_case_table.jsonl",
        stage8_6_summary_path=stage8_6_dir / "ablation_summary.json",
        stage8_6_operator_report_path=stage8_6_dir
        / "operator_family_ablation_report.json",
        stage8_6_proposal_report_path=stage8_6_dir
        / "proposal_state_ablation_report.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_7",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

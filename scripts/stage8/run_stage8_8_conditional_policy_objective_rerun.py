"""Run Stage 8.8 objective-loop rerun for the conditional policy."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.conditional_policy_objective_rerun import (  # noqa: E402
    run_stage8_8_conditional_policy_objective_rerun,
)


def main() -> None:
    stage8_7_dir = ROOT / "artifacts" / "objective_eval" / "stage8_7"
    summary = run_stage8_8_conditional_policy_objective_rerun(
        protocol_path=ROOT / "configs" / "stage7_0_objective_eval_protocol.yaml",
        stage8_3_selection_decision_path=ROOT
        / "artifacts"
        / "selection_audit"
        / "stage8_3"
        / "objective_utility_selection_decision.json",
        frozen_stage5_operator_path=ROOT
        / "artifacts"
        / "selected"
        / "stage5_1"
        / "selected_operator.json",
        frozen_stage5_ast_path=ROOT
        / "artifacts"
        / "selected"
        / "stage5_1"
        / "selected_operator_ast.json",
        stage8_7_policy_report_path=stage8_7_dir / "conditional_policy_report.json",
        stage8_7_case_policy_path=stage8_7_dir / "case_policy_table.jsonl",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

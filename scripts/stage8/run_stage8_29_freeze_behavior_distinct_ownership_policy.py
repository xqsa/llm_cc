"""Run Stage 8.29 behavior-distinct ownership policy freeze."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.freeze_behavior_distinct_ownership_policy import (  # noqa: E402
    freeze_stage8_29_behavior_distinct_ownership_policy,
)


def main() -> None:
    stage8_27_dir = ROOT / "artifacts" / "selection_audit" / "stage8_27"
    stage8_28_dir = ROOT / "artifacts" / "selection_audit" / "stage8_28"
    report = freeze_stage8_29_behavior_distinct_ownership_policy(
        stage8_27_report_path=stage8_27_dir
        / "llm_reflective_ownership_strategy_search_report.json",
        stage8_27_accepted_strategies_path=stage8_27_dir / "accepted_strategies.jsonl",
        stage8_27_evaluator_path=stage8_27_dir / "strategy_evaluator_report.json",
        stage8_28_report_path=stage8_28_dir
        / "llm_vs_non_llm_ownership_ablation_report.json",
        stage8_28_pool_summary_path=stage8_28_dir / "pool_summary.json",
        stage8_28_candidate_table_path=stage8_28_dir / "pool_candidate_table.jsonl",
        stage8_28_fe_ledger_path=stage8_28_dir / "fe_ledger.json",
        stage8_28_runtime_boundary_path=stage8_28_dir / "runtime_boundary.json",
        stage8_28_next_route_path=stage8_28_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "selected" / "stage8_29",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Run Stage 8.22 LLM-origin policy freeze."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.llm_origin_policy_freeze import (  # noqa: E402
    freeze_stage8_22_llm_origin_policy,
)


def main() -> None:
    stage8_20_dir = ROOT / "artifacts" / "selection_audit" / "stage8_20"
    stage8_21_dir = ROOT / "artifacts" / "selection_audit" / "stage8_21"
    summary = freeze_stage8_22_llm_origin_policy(
        stage8_20_report_path=stage8_20_dir / "llm_reflective_search_report.json",
        stage8_20_accepted_candidates_path=stage8_20_dir / "accepted_candidates.jsonl",
        stage8_20_evaluator_report_path=stage8_20_dir
        / "candidate_evaluator_report.json",
        stage8_20_fe_ledger_path=stage8_20_dir / "fe_ledger.json",
        stage8_20_runtime_boundary_path=stage8_20_dir / "runtime_boundary.json",
        stage8_21_report_path=stage8_21_dir / "llm_contribution_ablation_report.json",
        stage8_21_pool_summary_path=stage8_21_dir / "pool_summary.json",
        stage8_21_candidate_table_path=stage8_21_dir / "pool_candidate_table.jsonl",
        stage8_21_fe_ledger_path=stage8_21_dir / "fe_ledger.json",
        stage8_21_runtime_boundary_path=stage8_21_dir / "runtime_boundary.json",
        stage8_21_next_route_path=stage8_21_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "selected" / "stage8_22",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

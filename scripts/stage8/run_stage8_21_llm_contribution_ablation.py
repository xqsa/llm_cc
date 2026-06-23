"""Run Stage 8.21 LLM vs non-LLM contribution ablation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.llm_contribution_ablation import (  # noqa: E402
    run_stage8_21_llm_contribution_ablation,
)


def main() -> None:
    stage8_20_dir = ROOT / "artifacts" / "selection_audit" / "stage8_20"
    summary = run_stage8_21_llm_contribution_ablation(
        stage8_20_report_path=stage8_20_dir / "llm_reflective_search_report.json",
        stage8_20_accepted_candidates_path=stage8_20_dir / "accepted_candidates.jsonl",
        stage8_20_evaluator_report_path=stage8_20_dir
        / "candidate_evaluator_report.json",
        stage8_20_fe_ledger_path=stage8_20_dir / "fe_ledger.json",
        stage8_20_runtime_boundary_path=stage8_20_dir / "runtime_boundary.json",
        stage8_20_next_route_path=stage8_20_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "selection_audit" / "stage8_21",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

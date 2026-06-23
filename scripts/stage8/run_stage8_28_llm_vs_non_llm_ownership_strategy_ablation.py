"""Run Stage 8.28 LLM vs non-LLM ownership-strategy ablation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.llm_vs_non_llm_ownership_strategy_ablation import (  # noqa: E402
    run_stage8_28_llm_vs_non_llm_ownership_strategy_ablation,
)


def main() -> None:
    stage8_27_dir = ROOT / "artifacts" / "selection_audit" / "stage8_27"
    summary = run_stage8_28_llm_vs_non_llm_ownership_strategy_ablation(
        stage8_27_report_path=stage8_27_dir
        / "llm_reflective_ownership_strategy_search_report.json",
        stage8_27_accepted_strategies_path=stage8_27_dir / "accepted_strategies.jsonl",
        stage8_27_evaluator_path=stage8_27_dir / "strategy_evaluator_report.json",
        stage8_27_fe_ledger_path=stage8_27_dir / "fe_ledger.json",
        stage8_27_runtime_boundary_path=stage8_27_dir / "runtime_boundary.json",
        stage8_27_next_route_path=stage8_27_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "selection_audit" / "stage8_28",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

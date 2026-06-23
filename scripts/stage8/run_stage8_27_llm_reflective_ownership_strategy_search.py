"""Run Stage 8.27 real LLM-reflective ownership-aware strategy search."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.llm_reflective_ownership_strategy_search import (  # noqa: E402
    run_stage8_27_llm_reflective_ownership_strategy_search,
)


def main() -> None:
    stage8_26_dir = ROOT / "artifacts" / "analysis" / "stage8_26"
    summary = run_stage8_27_llm_reflective_ownership_strategy_search(
        stage8_26_report_path=stage8_26_dir / "stage8_26_report.json",
        stage8_26_manifest_path=stage8_26_dir / "strategy_dsl_manifest.json",
        stage8_26_equivalence_path=stage8_26_dir / "behavior_equivalence_report.json",
        stage8_26_fe_ledger_path=stage8_26_dir / "fe_ledger.json",
        stage8_26_runtime_boundary_path=stage8_26_dir / "runtime_boundary.json",
        stage8_26_next_route_path=stage8_26_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "selection_audit" / "stage8_27",
        env_path=ROOT / ".env",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

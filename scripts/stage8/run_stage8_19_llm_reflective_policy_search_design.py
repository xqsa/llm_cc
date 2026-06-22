"""Run Stage 8.19 LLM-reflective policy search design lock."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.llm_reflective_policy_search_design import (  # noqa: E402
    run_stage8_19_llm_reflective_policy_search_design,
)


def main() -> None:
    stage8_18_dir = ROOT / "artifacts" / "objective_eval" / "stage8_18"
    summary = run_stage8_19_llm_reflective_policy_search_design(
        stage8_18_resmoke_report_path=stage8_18_dir
        / "repaired_policy_resmoke_report.json",
        stage8_18_win_loss_path=stage8_18_dir / "win_loss_report.json",
        stage8_18_policy_branch_path=stage8_18_dir / "policy_branch_report.json",
        stage8_18_fe_ledger_path=stage8_18_dir / "fe_ledger.json",
        stage8_18_runtime_boundary_path=stage8_18_dir / "runtime_boundary.json",
        stage8_18_next_route_path=stage8_18_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "selection_audit" / "stage8_19",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

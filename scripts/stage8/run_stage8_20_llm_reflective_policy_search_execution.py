"""Run Stage 8.20 LLM-reflective policy search execution."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.llm_reflective_policy_search_execution import (  # noqa: E402
    run_stage8_20_llm_reflective_policy_search_execution,
)


def main() -> None:
    stage8_19_dir = ROOT / "artifacts" / "selection_audit" / "stage8_19"
    summary = run_stage8_20_llm_reflective_policy_search_execution(
        stage8_19_design_path=stage8_19_dir
        / "llm_reflective_policy_search_design.json",
        stage8_19_prompt_contract_path=stage8_19_dir
        / "reflection_prompt_contract.json",
        stage8_19_dsl_contract_path=stage8_19_dir
        / "coordination_policy_dsl_contract.json",
        stage8_19_ablation_plan_path=stage8_19_dir
        / "llm_contribution_ablation_plan.json",
        stage8_19_gate_path=stage8_19_dir / "beat_best_reward_gate.json",
        stage8_19_fe_ledger_path=stage8_19_dir / "fe_ledger.json",
        stage8_19_runtime_boundary_path=stage8_19_dir / "runtime_boundary.json",
        stage8_19_next_route_path=stage8_19_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "selection_audit" / "stage8_20",
        env_path=ROOT / ".env",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

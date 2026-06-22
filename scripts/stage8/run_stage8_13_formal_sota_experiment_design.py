"""Run Stage 8.13 formal CEC2013 SOTA experiment design lock."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.formal_sota_experiment_design import (  # noqa: E402
    run_stage8_13_formal_sota_experiment_design,
)


def main() -> None:
    stage8_12_dir = ROOT / "artifacts" / "objective_eval" / "stage8_12"
    stage7_4_dir = ROOT / "artifacts" / "objective_eval" / "stage7_4"
    stage7_5_dir = ROOT / "artifacts" / "objective_eval" / "stage7_5"
    stage7_6_dir = ROOT / "artifacts" / "objective_eval" / "stage7_6"
    summary = run_stage8_13_formal_sota_experiment_design(
        stage8_12_panel_report_path=stage8_12_dir / "official_like_panel_report.json",
        stage8_12_sota_gap_path=stage8_12_dir / "sota_gap_report.json",
        stage8_12_same_budget_path=stage8_12_dir / "same_budget_report.json",
        stage8_12_strong_baseline_path=stage8_12_dir / "strong_baseline_report.json",
        stage8_12_fe_ledger_path=stage8_12_dir / "fe_ledger.json",
        stage8_12_runtime_boundary_path=stage8_12_dir / "runtime_boundary.json",
        stage8_12_next_route_path=stage8_12_dir / "next_route_decision.json",
        stage7_4_cec2013_decision_path=stage7_4_dir / "cec2013_panel_decision.json",
        stage7_5_sota_protocol_path=stage7_5_dir / "sota_protocol_report.json",
        stage7_5_claim_contract_path=stage7_5_dir / "benchmark_claim_contract.json",
        stage7_6_comparator_audit_path=stage7_6_dir
        / "reported_results_comparator_audit_report.json",
        stage7_6_comparator_registry_path=stage7_6_dir
        / "reported_results_comparator_registry.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_13",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

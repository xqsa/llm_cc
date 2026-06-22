"""Run Stage 8.10 official-like panel or policy-generalization decision."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.official_like_policy_generalization_decision import (  # noqa: E402
    run_stage8_10_official_like_policy_generalization_decision,
)


def main() -> None:
    stage8_9_dir = ROOT / "artifacts" / "objective_eval" / "stage8_9"
    stage7_5_dir = ROOT / "artifacts" / "objective_eval" / "stage7_5"
    stage7_6_dir = ROOT / "artifacts" / "objective_eval" / "stage7_6"
    summary = run_stage8_10_official_like_policy_generalization_decision(
        stage8_9_interpretation_path=stage8_9_dir / "interpretation_report.json",
        stage8_9_claim_boundary_path=stage8_9_dir / "claim_boundary_report.json",
        stage8_9_readiness_path=stage8_9_dir / "paper_claim_readiness_report.json",
        stage8_9_fe_ledger_path=stage8_9_dir / "fe_ledger.json",
        stage8_9_runtime_boundary_path=stage8_9_dir / "runtime_boundary.json",
        stage7_5_sota_protocol_path=stage7_5_dir / "sota_protocol_report.json",
        stage7_5_claim_contract_path=stage7_5_dir / "benchmark_claim_contract.json",
        stage7_6_comparator_audit_path=stage7_6_dir
        / "reported_results_comparator_audit_report.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_10",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

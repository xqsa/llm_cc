"""Run Stage 8.12 official-like / SOTA-facing evidence gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.official_like_sota_panel import (  # noqa: E402
    run_stage8_12_official_like_sota_panel,
)


def main() -> None:
    stage8_11_dir = ROOT / "artifacts" / "objective_eval" / "stage8_11"
    stage7_5_dir = ROOT / "artifacts" / "objective_eval" / "stage7_5"
    stage7_6_dir = ROOT / "artifacts" / "objective_eval" / "stage7_6"
    summary = run_stage8_12_official_like_sota_panel(
        stage8_11_panel_report_path=stage8_11_dir / "panel_report.json",
        stage8_11_win_loss_path=stage8_11_dir / "win_loss_report.json",
        stage8_11_method_summary_path=stage8_11_dir / "method_summary.json",
        stage8_11_panel_summary_path=stage8_11_dir / "panel_summary.json",
        stage8_11_fe_ledger_path=stage8_11_dir / "fe_ledger.json",
        stage8_11_runtime_boundary_path=stage8_11_dir / "runtime_boundary.json",
        stage8_11_next_route_path=stage8_11_dir / "next_route_decision.json",
        stage7_5_sota_protocol_path=stage7_5_dir / "sota_protocol_report.json",
        stage7_5_claim_contract_path=stage7_5_dir / "benchmark_claim_contract.json",
        stage7_6_comparator_audit_path=stage7_6_dir
        / "reported_results_comparator_audit_report.json",
        stage7_6_comparator_registry_path=stage7_6_dir
        / "reported_results_comparator_registry.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_12",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

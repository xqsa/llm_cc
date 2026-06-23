"""Run Stage 8.33 static guard sanity gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.static_guard_sanity_gate import (  # noqa: E402
    run_stage8_33_static_guard_sanity_gate,
)


def main() -> None:
    stage8_32_dir = ROOT / "artifacts" / "analysis" / "stage8_32"
    report = run_stage8_33_static_guard_sanity_gate(
        stage8_32_repair_design_path=stage8_32_dir / "repair_design_report.json",
        stage8_32_policy_payload_path=stage8_32_dir / "guarded_policy_payload.json",
        stage8_32_guard_spec_path=stage8_32_dir / "overcorrection_guard_spec.json",
        stage8_32_static_coverage_path=stage8_32_dir
        / "static_guard_coverage_report.json",
        stage8_32_fe_ledger_path=stage8_32_dir / "fe_ledger.json",
        stage8_32_runtime_boundary_path=stage8_32_dir / "runtime_boundary.json",
        stage8_32_next_route_path=stage8_32_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "analysis" / "stage8_33",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

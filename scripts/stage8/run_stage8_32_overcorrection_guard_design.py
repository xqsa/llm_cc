"""Run Stage 8.32 overcorrection guard design."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.overcorrection_guard_design import (  # noqa: E402
    run_stage8_32_overcorrection_guard_design,
)


def main() -> None:
    stage8_31_dir = ROOT / "artifacts" / "analysis" / "stage8_31"
    report = run_stage8_32_overcorrection_guard_design(
        stage8_31_failure_diagnosis_path=stage8_31_dir
        / "failure_diagnosis_report.json",
        stage8_31_overcorrection_path=stage8_31_dir
        / "overcorrection_diagnosis.json",
        stage8_31_branch_usage_path=stage8_31_dir / "branch_usage_diagnosis.json",
        stage8_31_fe_ledger_path=stage8_31_dir / "fe_ledger.json",
        stage8_31_runtime_boundary_path=stage8_31_dir / "runtime_boundary.json",
        stage8_31_next_route_path=stage8_31_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "analysis" / "stage8_32",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

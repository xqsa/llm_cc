"""Run Stage 8.18 CEC2013 F13/F14 repaired-policy re-smoke."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.cec2013_repaired_policy_resmoke import (  # noqa: E402
    run_stage8_18_cec2013_repaired_policy_resmoke,
)


def main() -> None:
    stage8_17_dir = ROOT / "artifacts" / "objective_eval" / "stage8_17"
    summary = run_stage8_18_cec2013_repaired_policy_resmoke(
        stage8_17_objective_report_path=stage8_17_dir / "objective_check_report.json",
        stage8_17_win_loss_path=stage8_17_dir / "win_loss_report.json",
        stage8_17_policy_branch_path=stage8_17_dir / "policy_branch_report.json",
        stage8_17_fe_ledger_path=stage8_17_dir / "fe_ledger.json",
        stage8_17_runtime_boundary_path=stage8_17_dir / "runtime_boundary.json",
        stage8_17_next_route_path=stage8_17_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_18",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

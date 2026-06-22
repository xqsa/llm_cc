"""Run Stage 8.9 failure-honest interpretation before official claims."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.failure_honest_interpretation import (  # noqa: E402
    run_stage8_9_failure_honest_interpretation,
)


def main() -> None:
    stage8_8_dir = ROOT / "artifacts" / "objective_eval" / "stage8_8"
    summary = run_stage8_9_failure_honest_interpretation(
        stage8_8_panel_report_path=stage8_8_dir / "panel_report.json",
        stage8_8_win_loss_path=stage8_8_dir / "win_loss_report.json",
        stage8_8_policy_runtime_path=stage8_8_dir
        / "conditional_policy_runtime_report.json",
        stage8_8_fe_ledger_path=stage8_8_dir / "fe_ledger.json",
        stage8_8_runtime_boundary_path=stage8_8_dir / "runtime_boundary.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_9",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

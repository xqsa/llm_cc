"""Run Stage 8.5 failure-honest analysis."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.failure_honest_analysis import (  # noqa: E402
    run_stage8_5_failure_honest_analysis,
)


def main() -> None:
    stage8_4_dir = ROOT / "artifacts" / "objective_eval" / "stage8_4"
    report = run_stage8_5_failure_honest_analysis(
        stage8_4_trace_path=stage8_4_dir / "objective_trace.jsonl",
        stage8_4_win_loss_path=stage8_4_dir / "win_loss_report.json",
        stage8_4_method_summary_path=stage8_4_dir / "method_summary.json",
        stage8_4_panel_report_path=stage8_4_dir / "panel_report.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_5",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Run Stage 6.1 sealed-test baseline ablation analysis."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.baseline_ablation_analysis import (  # noqa: E402
    run_stage6_1_baseline_ablation_analysis,
)


def main() -> None:
    stage6_0_dir = ROOT / "artifacts" / "sealed_test" / "stage6_0"
    report = run_stage6_1_baseline_ablation_analysis(
        sealed_test_trace_path=stage6_0_dir / "sealed_test_trace.jsonl",
        sealed_test_metrics_path=stage6_0_dir / "sealed_test_metrics.json",
        fe_ledger_path=stage6_0_dir / "fe_ledger.json",
        final_reporting_boundary_path=stage6_0_dir / "final_reporting_boundary.json",
        sealed_test_report_path=stage6_0_dir / "sealed_test_report.json",
        output_dir=ROOT / "artifacts" / "sealed_test" / "stage6_1",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

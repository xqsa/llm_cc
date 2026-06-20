"""Run Stage 4.1 train-search audit and promotion-rule hardening."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.train_search_audit import (
    run_stage4_1_train_search_audit,
)  # noqa: E402


def main() -> None:
    stage4_0_dir = ROOT / "artifacts" / "search" / "stage4_0"
    report = run_stage4_1_train_search_audit(
        search_trace_path=stage4_0_dir / "search_trace.jsonl",
        promotion_candidates_path=stage4_0_dir / "promotion_candidates.json",
        fe_ledger_path=stage4_0_dir / "fe_ledger.json",
        search_report_path=stage4_0_dir / "search_report.json",
        output_dir=ROOT / "artifacts" / "search" / "stage4_1",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

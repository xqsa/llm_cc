"""Run Stage 3.6 candidate-pool freeze and protocol preparation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.llm.freeze_candidate_pool import freeze_stage3_6_candidate_pool  # noqa: E402


def main() -> None:
    report = freeze_stage3_6_candidate_pool(
        accepted_log_path=ROOT
        / "artifacts"
        / "candidates"
        / "stage3_5"
        / "accepted_candidates.jsonl",
        quality_report_path=ROOT
        / "artifacts"
        / "candidates"
        / "stage3_5"
        / "quality_filter_report.json",
        diversity_report_path=ROOT
        / "artifacts"
        / "candidates"
        / "stage3_5"
        / "static_diversity_audit.json",
        coverage_report_path=ROOT
        / "artifacts"
        / "candidates"
        / "stage3_5"
        / "coverage_gate_report.json",
        output_dir=ROOT / "artifacts" / "candidates" / "stage3_6",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

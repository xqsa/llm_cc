"""Run Stage 3.4 static candidate quality and diversity audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.llm.static_candidate_audit import run_stage3_4_static_audit  # noqa: E402


def main() -> None:
    report = run_stage3_4_static_audit(
        accepted_log_path=ROOT
        / "artifacts"
        / "candidates"
        / "stage3_3"
        / "accepted_candidates.jsonl",
        output_dir=ROOT / "artifacts" / "candidates" / "stage3_4",
        low_diversity_unique_kind_sequence_threshold=3,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Run Stage 3.3 train-only multi-batch LLM candidate generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.llm.multibatch_candidate_generator import (
    run_stage3_3_multi_batch,
)  # noqa: E402


def main() -> None:
    report = run_stage3_3_multi_batch(
        env_path=ROOT / ".env",
        output_dir=ROOT / "artifacts" / "candidates" / "stage3_3",
        shared_variables={5, 6},
        protocol_report_path=ROOT
        / "artifacts"
        / "readiness"
        / "stage3_0_protocol_lock_report.json",
        batch_count=3,
        candidates_per_batch=3,
        temperature=0.35,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

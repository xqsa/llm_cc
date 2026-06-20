"""Run Stage 5.0 validation-only selection."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.validation_selection import (  # noqa: E402
    run_stage5_0_validation_selection,
)


def main() -> None:
    report = run_stage5_0_validation_selection(
        promotion_decision_path=(
            ROOT / "artifacts" / "search" / "stage4_1" / "promotion_decision.json"
        ),
        frozen_pool_path=(
            ROOT
            / "artifacts"
            / "candidates"
            / "stage3_6"
            / "frozen_candidate_pool.jsonl"
        ),
        output_dir=ROOT / "artifacts" / "validation" / "stage5_0",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

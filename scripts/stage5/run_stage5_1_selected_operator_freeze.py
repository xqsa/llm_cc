"""Run Stage 5.1 selected-operator freeze."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.selected_operator_freeze import (  # noqa: E402
    freeze_stage5_1_selected_operator,
)


def main() -> None:
    report = freeze_stage5_1_selected_operator(
        selection_decision_path=(
            ROOT / "artifacts" / "validation" / "stage5_0" / "selection_decision.json"
        ),
        validation_report_path=(
            ROOT / "artifacts" / "validation" / "stage5_0" / "validation_report.json"
        ),
        frozen_pool_path=(
            ROOT
            / "artifacts"
            / "candidates"
            / "stage3_6"
            / "frozen_candidate_pool.jsonl"
        ),
        output_dir=ROOT / "artifacts" / "selected" / "stage5_1",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

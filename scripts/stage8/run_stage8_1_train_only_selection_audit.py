"""Run Stage 8.1 train-only selection audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.train_only_selection_audit import (  # noqa: E402
    run_stage8_1_train_only_selection_audit,
)


def main() -> None:
    report = run_stage8_1_train_only_selection_audit(
        improvement_trace_path=ROOT
        / "artifacts"
        / "improvement"
        / "stage8_0"
        / "improvement_trace.jsonl",
        improvement_candidates_path=ROOT
        / "artifacts"
        / "improvement"
        / "stage8_0"
        / "improvement_candidates.json",
        output_dir=ROOT / "artifacts" / "selection_audit" / "stage8_1",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

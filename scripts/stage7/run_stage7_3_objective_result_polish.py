"""Run Stage 7.3 objective result polish."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.objective_result_polish import (  # noqa: E402
    run_stage7_3_objective_result_polish,
)


def main() -> None:
    report = run_stage7_3_objective_result_polish(
        source_dir=ROOT / "artifacts" / "objective_eval" / "stage7_2",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage7_3",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

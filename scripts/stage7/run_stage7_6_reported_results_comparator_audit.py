"""Run Stage 7.6 reported-results comparator audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.reported_results_comparator_audit import (  # noqa: E402
    run_stage7_6_reported_results_comparator_audit,
)


def main() -> None:
    report = run_stage7_6_reported_results_comparator_audit(
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage7_6",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

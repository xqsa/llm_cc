"""Run Stage 8.3 objective-level utility evidence selection."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.objective_level_utility_selection import (  # noqa: E402
    run_stage8_3_objective_level_utility_selection,
)


def main() -> None:
    report = run_stage8_3_objective_level_utility_selection(
        stage8_1_selection_decision_path=ROOT
        / "artifacts"
        / "selection_audit"
        / "stage8_1"
        / "selection_decision.json",
        stage8_2_pilot_report_path=ROOT
        / "artifacts"
        / "objective_eval"
        / "stage8_2"
        / "pilot_report.json",
        stage8_2_utility_report_path=ROOT
        / "artifacts"
        / "objective_eval"
        / "stage8_2"
        / "utility_report.json",
        stage8_2_fe_ledger_path=ROOT
        / "artifacts"
        / "objective_eval"
        / "stage8_2"
        / "fe_ledger.json",
        output_dir=ROOT / "artifacts" / "selection_audit" / "stage8_3",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

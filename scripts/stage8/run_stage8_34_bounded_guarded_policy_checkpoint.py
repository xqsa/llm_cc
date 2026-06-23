"""Run Stage 8.34 bounded guarded-policy checkpoint replay."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.bounded_guarded_policy_checkpoint import (  # noqa: E402
    run_stage8_34_bounded_guarded_policy_checkpoint,
)


def main() -> None:
    report = run_stage8_34_bounded_guarded_policy_checkpoint(
        stage8_30_win_loss_path=ROOT
        / "artifacts"
        / "objective_eval"
        / "stage8_30"
        / "win_loss_report.json",
        stage8_31_case_delta_table_path=ROOT
        / "artifacts"
        / "analysis"
        / "stage8_31"
        / "case_delta_table.jsonl",
        stage8_32_policy_payload_path=ROOT
        / "artifacts"
        / "analysis"
        / "stage8_32"
        / "guarded_policy_payload.json",
        stage8_33_sanity_report_path=ROOT
        / "artifacts"
        / "analysis"
        / "stage8_33"
        / "static_guard_sanity_report.json",
        stage8_33_runtime_boundary_path=ROOT
        / "artifacts"
        / "analysis"
        / "stage8_33"
        / "runtime_boundary.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_34",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

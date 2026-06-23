"""Run Stage 8.25 read-only literature-aligned LLM role redesign."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.literature_aligned_llm_role_redesign import (  # noqa: E402
    run_stage8_25_literature_aligned_llm_role_redesign,
)


def main() -> None:
    stage8_24_dir = ROOT / "artifacts" / "objective_eval" / "stage8_24"
    summary = run_stage8_25_literature_aligned_llm_role_redesign(
        stage8_24_checkpoint_report_path=stage8_24_dir
        / "checkpoint_pilot_report.json",
        stage8_24_win_loss_path=stage8_24_dir / "win_loss_report.json",
        stage8_24_policy_branch_path=stage8_24_dir / "policy_branch_report.json",
        stage8_24_fe_ledger_path=stage8_24_dir / "fe_ledger.json",
        stage8_24_runtime_boundary_path=stage8_24_dir / "runtime_boundary.json",
        stage8_24_next_route_path=stage8_24_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "analysis" / "stage8_25",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Run Stage 8.6 proposal-state/operator-family ablation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.proposal_state_operator_family_ablation import (  # noqa: E402
    run_stage8_6_proposal_state_operator_family_ablation,
)


def main() -> None:
    stage8_4_dir = ROOT / "artifacts" / "objective_eval" / "stage8_4"
    stage8_5_dir = ROOT / "artifacts" / "objective_eval" / "stage8_5"
    summary = run_stage8_6_proposal_state_operator_family_ablation(
        stage8_4_trace_path=stage8_4_dir / "objective_trace.jsonl",
        stage8_4_win_loss_path=stage8_4_dir / "win_loss_report.json",
        stage8_5_diagnosis_path=stage8_5_dir / "failure_honest_diagnosis_report.json",
        stage8_5_equivalence_path=stage8_5_dir / "baseline_equivalence_report.json",
        stage8_5_topology_path=stage8_5_dir / "topology_gap_report.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_6",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

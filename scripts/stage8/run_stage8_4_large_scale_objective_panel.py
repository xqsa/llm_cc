"""Run Stage 8.4 large-scale objective panel evaluation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.large_scale_objective_panel import (  # noqa: E402
    run_stage8_4_large_scale_objective_panel,
)


def main() -> None:
    report = run_stage8_4_large_scale_objective_panel(
        protocol_path=ROOT / "configs" / "stage7_0_objective_eval_protocol.yaml",
        stage8_3_selection_decision_path=ROOT
        / "artifacts"
        / "selection_audit"
        / "stage8_3"
        / "objective_utility_selection_decision.json",
        frozen_stage5_operator_path=ROOT
        / "artifacts"
        / "selected"
        / "stage5_1"
        / "selected_operator.json",
        frozen_stage5_ast_path=ROOT
        / "artifacts"
        / "selected"
        / "stage5_1"
        / "selected_operator_ast.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_4",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

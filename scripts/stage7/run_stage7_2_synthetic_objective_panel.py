"""Run Stage 7.2 synthetic large-scale objective panel."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.synthetic_objective_panel import (  # noqa: E402
    run_stage7_2_synthetic_objective_panel,
)


def main() -> None:
    report = run_stage7_2_synthetic_objective_panel(
        protocol_path=ROOT / "configs" / "stage7_0_objective_eval_protocol.yaml",
        selected_operator_path=(
            ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator.json"
        ),
        selected_ast_path=(
            ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator_ast.json"
        ),
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage7_2",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

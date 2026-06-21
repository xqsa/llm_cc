"""Run Stage 7.1 minimal LOCO-CC objective-loop pilot."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.objective_loop_pilot import (  # noqa: E402
    run_stage7_1_objective_loop_pilot,
)


def main() -> None:
    report = run_stage7_1_objective_loop_pilot(
        protocol_path=ROOT / "configs" / "stage7_0_objective_eval_protocol.yaml",
        selected_operator_path=(
            ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator.json"
        ),
        selected_ast_path=(
            ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator_ast.json"
        ),
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage7_1",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

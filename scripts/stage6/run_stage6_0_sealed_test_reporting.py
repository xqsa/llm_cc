"""Run Stage 6.0 sealed-test final reporting diagnostics."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.sealed_test_reporting import (  # noqa: E402
    run_stage6_0_sealed_test_reporting,
)


def main() -> None:
    report = run_stage6_0_sealed_test_reporting(
        readiness_protocol_path=(
            ROOT
            / "artifacts"
            / "selected"
            / "stage5_1"
            / "sealed_test_readiness_protocol.json"
        ),
        selected_operator_path=(
            ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator.json"
        ),
        selected_ast_path=(
            ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator_ast.json"
        ),
        output_dir=ROOT / "artifacts" / "sealed_test" / "stage6_0",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Run Stage 7.5 SOTA-targeted real benchmark protocol lock."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.sota_protocol_lock import (  # noqa: E402
    run_stage7_5_sota_protocol,
)


def main() -> None:
    report = run_stage7_5_sota_protocol(
        stage7_4_decision_path=(
            ROOT
            / "artifacts"
            / "objective_eval"
            / "stage7_4"
            / "cec2013_panel_decision.json"
        ),
        stage7_4_protocol_path=(
            ROOT
            / "artifacts"
            / "objective_eval"
            / "stage7_4"
            / "cec2013_optional_panel_protocol.json"
        ),
        stage7_3_ranking_path=(
            ROOT / "artifacts" / "objective_eval" / "stage7_3" / "method_ranking.json"
        ),
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage7_5",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

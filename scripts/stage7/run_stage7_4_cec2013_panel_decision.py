"""Run Stage 7.4 optional CEC2013 F13/F14 panel decision."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.cec2013_panel_decision import (  # noqa: E402
    run_stage7_4_cec2013_panel_decision,
)


def main() -> None:
    report = run_stage7_4_cec2013_panel_decision(
        stage7_3_report_path=(
            ROOT
            / "artifacts"
            / "objective_eval"
            / "stage7_3"
            / "paper_tables_report.json"
        ),
        stage7_3_ranking_path=(
            ROOT / "artifacts" / "objective_eval" / "stage7_3" / "method_ranking.json"
        ),
        stage7_3_claim_boundary_path=(
            ROOT / "artifacts" / "objective_eval" / "stage7_3" / "claim_boundary.json"
        ),
        metabox_smoke_path=ROOT / "docs" / "stage1" / "metabox_real_smoke_latest.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage7_4",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

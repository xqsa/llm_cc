"""Run Stage 8.26 MVP ownership-aware strategy DSL gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.ownership_aware_strategy_dsl import (  # noqa: E402
    run_stage8_26_mvp_strategy_dsl,
)


def main() -> None:
    stage8_25_dir = ROOT / "artifacts" / "analysis" / "stage8_25"
    summary = run_stage8_26_mvp_strategy_dsl(
        stage8_25_report_path=stage8_25_dir / "stage8_25_report.json",
        stage8_25_dsl_contract_path=stage8_25_dir
        / "ownership_aware_strategy_dsl_contract.json",
        stage8_25_fe_ledger_path=stage8_25_dir / "fe_ledger.json",
        stage8_25_runtime_boundary_path=stage8_25_dir / "runtime_boundary.json",
        stage8_25_next_route_path=stage8_25_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "analysis" / "stage8_26",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

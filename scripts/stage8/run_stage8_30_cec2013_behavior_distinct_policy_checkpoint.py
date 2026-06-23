"""Run Stage 8.30 CEC2013 behavior-distinct policy checkpoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.cec2013_behavior_distinct_policy_checkpoint import (  # noqa: E402
    run_stage8_30_cec2013_behavior_distinct_policy_checkpoint,
)


def main() -> None:
    stage8_29_dir = ROOT / "artifacts" / "selected" / "stage8_29"
    report = run_stage8_30_cec2013_behavior_distinct_policy_checkpoint(
        stage8_29_frozen_policy_path=stage8_29_dir
        / "frozen_behavior_distinct_policy.json",
        stage8_29_frozen_strategy_payload_path=stage8_29_dir
        / "frozen_strategy_payload.json",
        stage8_29_manifest_path=stage8_29_dir / "freeze_manifest.json",
        stage8_29_readiness_protocol_path=stage8_29_dir
        / "cec_checkpoint_readiness_protocol.json",
        stage8_29_fe_ledger_path=stage8_29_dir / "fe_ledger.json",
        stage8_29_runtime_boundary_path=stage8_29_dir / "runtime_boundary.json",
        stage8_29_next_route_path=stage8_29_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_30",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

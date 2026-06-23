"""Run Stage 8.24 CEC2013 F13/F14 frozen-policy checkpoint-budget pilot."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.cec2013_frozen_policy_checkpoint_pilot import (  # noqa: E402
    run_stage8_24_cec2013_f13_f14_checkpoint_budget_pilot,
)


def main() -> None:
    stage8_22_dir = ROOT / "artifacts" / "selected" / "stage8_22"
    summary = run_stage8_24_cec2013_f13_f14_checkpoint_budget_pilot(
        stage8_22_frozen_policy_path=stage8_22_dir / "frozen_policy.json",
        stage8_22_frozen_policy_payload_path=stage8_22_dir
        / "frozen_policy_payload.json",
        stage8_22_manifest_path=stage8_22_dir / "frozen_policy_manifest.json",
        stage8_22_readiness_protocol_path=stage8_22_dir
        / "cec2013_f13_f14_multiseed_readiness_protocol.json",
        stage8_22_fe_ledger_path=stage8_22_dir / "fe_ledger.json",
        stage8_22_runtime_boundary_path=stage8_22_dir / "runtime_boundary.json",
        stage8_22_next_route_path=stage8_22_dir / "next_route_decision.json",
        output_dir=ROOT / "artifacts" / "objective_eval" / "stage8_24",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

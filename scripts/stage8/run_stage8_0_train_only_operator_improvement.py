"""Run Stage 8.0 train-only operator improvement."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.train_only_operator_improvement import (  # noqa: E402
    run_stage8_0_train_only_operator_improvement,
)


def main() -> None:
    report = run_stage8_0_train_only_operator_improvement(
        frozen_pool_path=ROOT
        / "artifacts"
        / "candidates"
        / "stage3_6"
        / "frozen_candidate_pool.jsonl",
        family_space_config_path=ROOT
        / "configs"
        / "stage4_coordination_family_space.yaml",
        output_dir=ROOT / "artifacts" / "improvement" / "stage8_0",
        improvement_top_k=4,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

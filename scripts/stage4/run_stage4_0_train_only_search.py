"""Run Stage 4.0 train-only search over the frozen candidate pool."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.coordination.train_only_search import (
    run_stage4_0_train_only_search,
)  # noqa: E402


def main() -> None:
    report = run_stage4_0_train_only_search(
        frozen_pool_path=ROOT
        / "artifacts"
        / "candidates"
        / "stage3_6"
        / "frozen_candidate_pool.jsonl",
        family_space_config_path=ROOT
        / "configs"
        / "stage4_coordination_family_space.yaml",
        output_dir=ROOT / "artifacts" / "search" / "stage4_0",
        promotion_top_k=3,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

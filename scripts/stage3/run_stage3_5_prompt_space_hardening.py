"""Run Stage 3.5 prompt-space hardening candidate generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from loco.llm.prompt_space_hardening import (  # noqa: E402
    run_stage3_5_prompt_space_hardening,
)


def main() -> None:
    report = run_stage3_5_prompt_space_hardening(
        env_path=ROOT / ".env",
        output_dir=ROOT / "artifacts" / "candidates" / "stage3_5",
        shared_variables={5, 6},
        protocol_report_path=ROOT
        / "artifacts"
        / "readiness"
        / "stage3_0_protocol_lock_report.json",
        batch_count=3,
        candidates_per_batch=4,
        temperature=0.45,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

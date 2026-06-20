"""Pre-Stage-3 readiness gate for Stage 2.10.

This module reads existing Stage 2 artifacts and emits a readiness decision for
entering Stage 3. It does not call LLMs, run evolution, generate candidates,
promote candidates, execute ASTs, or evaluate objectives.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


READINESS_SCHEMA_VERSION = "loco.pre_stage3_readiness.v1"
STAGE = "2.10"
REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_STAGE2_7_AUDIT_REPORT = (
    REPO_ROOT
    / "artifacts"
    / "candidates"
    / "stage2_7"
    / "split_replay_audit_report.json"
)
DEFAULT_STAGE2_8_REGISTRY = (
    REPO_ROOT / "artifacts" / "operators" / "stage2_8_registry.jsonl"
)
DEFAULT_STAGE2_9_AUDIT_REPORT = (
    REPO_ROOT
    / "artifacts"
    / "operators"
    / "stage2_9"
    / "promotion_replay_audit_report.json"
)
DEFAULT_METABOX_SMOKE_REPORT = (
    REPO_ROOT / "docs" / "stage1" / "metabox_real_smoke_latest.json"
)
DEFAULT_DECISION_PATH = (
    REPO_ROOT / "artifacts" / "readiness" / "stage2_10_readiness_decision.json"
)

STAGE3_ALLOWED_SCOPE = "LLM/evolution search over typed coordination operator ASTs only"
STAGE3_FORBIDDEN_SCOPE = [
    "optimizer generation",
    "BaseOpt modification",
    "scheduler/controller generation",
    "optimizer selection",
    "benchmark objective rewrite",
    "test feedback access",
    "test-set tuning",
    "untyped executable code generation",
]
REQUIRED_PASS_GATES = [
    "stage2_7_sealed_split_replay_audit",
    "stage2_8_frozen_candidate_promotion_contract",
    "stage2_9_promotion_replay_and_registry_audit",
]


def evaluate_pre_stage3_readiness(
    *,
    stage2_7_audit_report_path: Path | str = DEFAULT_STAGE2_7_AUDIT_REPORT,
    stage2_8_registry_path: Path | str = DEFAULT_STAGE2_8_REGISTRY,
    stage2_9_audit_report_path: Path | str = DEFAULT_STAGE2_9_AUDIT_REPORT,
    metabox_smoke_report_path: Path | str = DEFAULT_METABOX_SMOKE_REPORT,
    decision_path: Path | str = DEFAULT_DECISION_PATH,
) -> dict[str, Any]:
    stage2_7 = _read_json(Path(stage2_7_audit_report_path))
    stage2_8_registry_rows = _read_jsonl(Path(stage2_8_registry_path))
    stage2_9 = _read_json(Path(stage2_9_audit_report_path))
    metabox_status = _metabox_smoke_status(Path(metabox_smoke_report_path))

    blocking_gates = []
    if stage2_7.get("status") != "PASS":
        blocking_gates.append("stage2_7_sealed_split_replay_audit")
    if not _stage2_8_registry_ready(stage2_8_registry_rows):
        blocking_gates.append("stage2_8_frozen_candidate_promotion_contract")
    if stage2_9.get("status") != "PASS":
        blocking_gates.append("stage2_9_promotion_replay_and_registry_audit")

    ready = not blocking_gates
    decision = {
        "schema_version": READINESS_SCHEMA_VERSION,
        "stage": STAGE,
        "decision": "READY_FOR_STAGE3_BOUNDARY_ONLY" if ready else "BLOCK_STAGE3",
        "stage3_allowed": ready,
        "stage3_allowed_scope": STAGE3_ALLOWED_SCOPE,
        "stage3_forbidden_scope": STAGE3_FORBIDDEN_SCOPE,
        "blocking_gates": blocking_gates,
        "required_pass_gates": REQUIRED_PASS_GATES,
        "evidence": {
            "stage2_7": {
                "path": _display_path(Path(stage2_7_audit_report_path)),
                "status": stage2_7.get("status"),
                "accepted_count": stage2_7.get("accepted_count"),
                "rejected_count": stage2_7.get("rejected_count"),
                "file_fingerprint_mismatch_count": stage2_7.get(
                    "file_fingerprint_mismatch_count"
                ),
                "split_violation_count": stage2_7.get("split_violation_count"),
                "test_feedback_violation_count": stage2_7.get(
                    "test_feedback_violation_count"
                ),
            },
            "stage2_8": {
                "path": _display_path(Path(stage2_8_registry_path)),
                "registry_entry_count": len(stage2_8_registry_rows),
                "frozen_entry_count": sum(
                    1 for row in stage2_8_registry_rows if row.get("frozen") is True
                ),
                "target_scope_values": sorted(
                    {str(row.get("target_scope")) for row in stage2_8_registry_rows}
                ),
                "no_test_feedback": all(
                    row.get("no_test_feedback") is True
                    for row in stage2_8_registry_rows
                ),
                "has_receipt_fingerprint": all(
                    isinstance(row.get("promotion_receipt_fingerprint_sha256"), str)
                    and len(row["promotion_receipt_fingerprint_sha256"]) == 64
                    for row in stage2_8_registry_rows
                ),
            },
            "stage2_9": {
                "path": _display_path(Path(stage2_9_audit_report_path)),
                "status": stage2_9.get("status"),
                "registry_entry_count": stage2_9.get("registry_entry_count"),
                "artifact_fingerprint_mismatch_count": stage2_9.get(
                    "artifact_fingerprint_mismatch_count"
                ),
                "receipt_fingerprint_mismatch_count": stage2_9.get(
                    "receipt_fingerprint_mismatch_count"
                ),
                "promotion_fingerprint_mismatch_count": stage2_9.get(
                    "promotion_fingerprint_mismatch_count"
                ),
                "boundary_violation_count": stage2_9.get("boundary_violation_count"),
            },
        },
        "known_risks": {
            "real_metabox_smoke_status": metabox_status,
            "metabox_top_level_import_status": "not_required_for_stage3_readiness",
            "stage3_still_requires_sealed_train_validation_test_protocol": True,
        },
        "not_performance_claim": True,
        "no_llm": True,
        "no_evolution": True,
        "no_optimizer": True,
        "no_candidate_generation": True,
        "no_test_feedback": True,
        "no_objective_evaluation": True,
    }
    _write_json(Path(decision_path), decision)
    return decision


def _stage2_8_registry_ready(rows: list[Mapping[str, Any]]) -> bool:
    if not rows:
        return False
    for row in rows:
        if row.get("frozen") is not True:
            return False
        if row.get("target_scope") != "shared_variables_only":
            return False
        if row.get("no_test_feedback") is not True:
            return False
        if row.get("no_llm") is not True or row.get("no_evolution") is not True:
            return False
        if row.get("no_optimizer") is not True:
            return False
        receipt_hash = row.get("promotion_receipt_fingerprint_sha256")
        if not isinstance(receipt_hash, str) or len(receipt_hash) != 64:
            return False
    return True


def _metabox_smoke_status(path: Path) -> str:
    resolved = _resolve_path(path)
    if not resolved.is_file():
        return "OPTIONAL_SKIP"
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    status = str(payload.get("status", "OPTIONAL_SKIP"))
    if status == "PASS":
        return "PASS"
    if status in {"PARTIAL", "PASS_WITH_BENCHMARK_ONLY_IMPORT"}:
        return "PARTIAL"
    return "OPTIONAL_SKIP"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(_resolve_path(path).read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _resolve_path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    resolved = _resolve_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _display_path(path: Path) -> str:
    resolved = _resolve_path(path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()

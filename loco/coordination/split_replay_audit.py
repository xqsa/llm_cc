"""Sealed split replay audit for candidate logs.

Stage 2.7 binds Stage 2.6 candidate logs to a sealed split manifest and
rechecks replay/no-test-feedback invariants. It does not call LLMs, run
evolution, generate candidates, execute ASTs, or evaluate objectives.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SEALED_SPLIT_SCHEMA_VERSION = "loco.sealed_split_manifest.v1"
AUDIT_SCHEMA_VERSION = "loco.sealed_split_replay_audit.v1"
STAGE = "2.7"
REPO_ROOT = Path(__file__).resolve().parents[2]


def load_sealed_split_manifest(manifest_path: Path | str) -> dict[str, Any]:
    path = Path(manifest_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    _validate_manifest(manifest)
    return manifest


def audit_sealed_split_replay(
    manifest_path: Path | str,
    report_path: Path | str,
) -> dict[str, Any]:
    manifest = load_sealed_split_manifest(manifest_path)
    accepted_path = _resolve_path(manifest["candidate_logs"]["accepted"]["path"])
    rejected_path = _resolve_path(manifest["candidate_logs"]["rejected"]["path"])
    replay_path = _resolve_path(manifest["candidate_logs"]["replay_report"]["path"])

    accepted_rows = _read_jsonl(accepted_path)
    rejected_rows = _read_jsonl(rejected_path)
    replay_report = json.loads(replay_path.read_text(encoding="utf-8"))
    allowed_splits = set(manifest["allowed_candidate_log_splits"])

    file_fingerprint_mismatch_count = sum(
        [
            _sha256_file(accepted_path)
            != manifest["candidate_logs"]["accepted"]["sha256"],
            _sha256_file(rejected_path)
            != manifest["candidate_logs"]["rejected"]["sha256"],
            _sha256_file(replay_path)
            != manifest["candidate_logs"]["replay_report"]["sha256"],
        ]
    )
    all_rows = accepted_rows + rejected_rows
    split_violations = [
        row["candidate_id"]
        for row in all_rows
        if row.get("split") not in allowed_splits or row.get("split") == "test"
    ]
    test_feedback_violations = [
        row["candidate_id"]
        for row in all_rows
        if row.get("no_test_feedback") is not True
        or row.get("test_feedback_used") is True
        or row.get("tuned_on_test") is True
    ]
    llm_or_evolution_violations = [
        row["candidate_id"]
        for row in all_rows
        if row.get("no_llm") is not True or row.get("no_evolution") is not True
    ]

    replay_status = "PASS" if replay_report.get("status") == "PASS" else "FAIL"
    manifest_status = "PASS" if manifest.get("sealed") is True else "FAIL"
    status = (
        "PASS"
        if manifest_status == "PASS"
        and replay_status == "PASS"
        and file_fingerprint_mismatch_count == 0
        and not split_violations
        and not test_feedback_violations
        and not llm_or_evolution_violations
        else "FAIL"
    )

    result = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": status,
        "sealed_manifest_status": manifest_status,
        "replay_report_status": replay_status,
        "manifest_path": _display_path(Path(manifest_path)),
        "accepted_count": len(accepted_rows),
        "rejected_count": len(rejected_rows),
        "file_fingerprint_mismatch_count": int(file_fingerprint_mismatch_count),
        "split_violation_count": len(split_violations),
        "test_feedback_violation_count": len(test_feedback_violations),
        "llm_or_evolution_violation_count": len(llm_or_evolution_violations),
        "split_violations": split_violations,
        "test_feedback_violations": test_feedback_violations,
        "allowed_candidate_log_splits": sorted(allowed_splits),
        "no_llm": True,
        "no_evolution": True,
        "no_optimizer": True,
        "no_candidate_generation": True,
        "no_test_feedback": True,
        "claim": "sealed split replay audit for candidate logs",
    }
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


def build_sealed_split_manifest(
    accepted_log_path: Path | str,
    rejected_log_path: Path | str,
    replay_report_path: Path | str,
) -> dict[str, Any]:
    accepted = Path(accepted_log_path)
    rejected = Path(rejected_log_path)
    replay = Path(replay_report_path)
    return {
        "schema_version": SEALED_SPLIT_SCHEMA_VERSION,
        "stage": STAGE,
        "sealed": True,
        "created_by": "Codex",
        "created_date": "2026-06-20",
        "split_ids": {
            "train": "stage2_7_train_not_used",
            "validation": "stage2_7_validation_not_used",
            "test": "stage2_7_test_locked",
        },
        "allowed_candidate_log_splits": ["pre_stage3_schema_only"],
        "test_split_locked": True,
        "no_llm": True,
        "no_evolution": True,
        "no_optimizer": True,
        "no_candidate_generation": True,
        "no_test_feedback": True,
        "candidate_logs": {
            "accepted": {
                "path": _display_path(accepted),
                "sha256": _sha256_file(accepted),
            },
            "rejected": {
                "path": _display_path(rejected),
                "sha256": _sha256_file(rejected),
            },
            "replay_report": {
                "path": _display_path(replay),
                "sha256": _sha256_file(replay),
            },
        },
    }


def write_sealed_split_manifest(
    manifest_path: Path | str,
    accepted_log_path: Path | str,
    rejected_log_path: Path | str,
    replay_report_path: Path | str,
) -> dict[str, Any]:
    manifest = build_sealed_split_manifest(
        accepted_log_path=accepted_log_path,
        rejected_log_path=rejected_log_path,
        replay_report_path=replay_report_path,
    )
    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def _validate_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != SEALED_SPLIT_SCHEMA_VERSION:
        raise ValueError("unsupported sealed split manifest schema_version")
    if manifest.get("stage") != STAGE:
        raise ValueError("sealed split manifest stage must be 2.7")
    if manifest.get("sealed") is not True:
        raise ValueError("sealed split manifest must set sealed=true")
    if manifest.get("no_test_feedback") is not True:
        raise ValueError("sealed split manifest must set no_test_feedback=true")
    if manifest.get("test_split_locked") is not True:
        raise ValueError("sealed split manifest must set test_split_locked=true")
    if manifest.get("allowed_candidate_log_splits") != ["pre_stage3_schema_only"]:
        raise ValueError("sealed split manifest has unexpected candidate log splits")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _resolve_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()

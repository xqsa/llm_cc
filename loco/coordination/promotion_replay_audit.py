"""Promotion replay and registry audit for Stage 2.9.

This module cold-start audits Stage 2.8 promoted operator artifacts, promotion
receipts, and registry rows. It does not re-promote candidates, call LLMs, run
evolution, generate candidates, execute ASTs, or evaluate objectives.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from loco.coordination.candidate_promotion import (
    PROMOTION_RECEIPT_SCHEMA_VERSION,
    PROMOTION_REGISTRY_SCHEMA_VERSION,
    load_promotion_receipt,
)
from loco.coordination.operator_artifacts import (
    compute_artifact_fingerprint,
    load_frozen_operator_artifact,
)


AUDIT_SCHEMA_VERSION = "loco.promotion_replay_audit.v1"
STAGE = "2.9"
REPO_ROOT = Path(__file__).resolve().parents[2]


def audit_promotion_registry(
    registry_path: Path | str,
    report_path: Path | str,
) -> dict[str, Any]:
    registry = Path(registry_path)
    rows = _read_jsonl(registry)

    entries = [_audit_registry_row(row) for row in rows]
    totals = _sum_counts(entries)
    status = "PASS" if all(entry["status"] == "PASS" for entry in entries) else "FAIL"
    result = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": status,
        "registry_path": _display_path(registry),
        "registry_entry_count": len(rows),
        "audited_artifact_count": len(entries),
        "artifact_fingerprint_mismatch_count": totals[
            "artifact_fingerprint_mismatch_count"
        ],
        "receipt_fingerprint_mismatch_count": totals[
            "receipt_fingerprint_mismatch_count"
        ],
        "promotion_fingerprint_mismatch_count": totals[
            "promotion_fingerprint_mismatch_count"
        ],
        "source_candidate_fingerprint_mismatch_count": totals[
            "source_candidate_fingerprint_mismatch_count"
        ],
        "sealed_manifest_fingerprint_mismatch_count": totals[
            "sealed_manifest_fingerprint_mismatch_count"
        ],
        "audit_report_fingerprint_mismatch_count": totals[
            "audit_report_fingerprint_mismatch_count"
        ],
        "schema_violation_count": totals["schema_violation_count"],
        "boundary_violation_count": totals["boundary_violation_count"],
        "entries": entries,
        "no_llm": True,
        "no_evolution": True,
        "no_optimizer": True,
        "no_candidate_generation": True,
        "no_test_feedback": True,
        "no_objective_evaluation": True,
        "claim": "promotion replay and registry audit",
    }
    _write_json(Path(report_path), result)
    return result


def _audit_registry_row(row: Mapping[str, Any]) -> dict[str, Any]:
    schema_violations: list[str] = []
    boundary_violations: list[str] = []

    if row.get("registry_schema_version") != PROMOTION_REGISTRY_SCHEMA_VERSION:
        schema_violations.append("registry_schema_version")
    if row.get("stage") != "2.8":
        schema_violations.append("registry_stage")

    artifact_path = _resolve_path(Path(str(row.get("artifact_path", ""))))
    receipt_path = _resolve_path(Path(str(row.get("promotion_receipt_path", ""))))
    artifact_payload = _safe_read_json(artifact_path, schema_violations, "artifact")
    receipt = _safe_read_receipt(receipt_path, schema_violations)

    artifact_fingerprint_mismatch = 1
    receipt_fingerprint_mismatch = 1
    promotion_fingerprint_mismatch = 1
    source_candidate_fingerprint_mismatch = 1
    sealed_manifest_fingerprint_mismatch = 1
    audit_report_fingerprint_mismatch = 1

    if artifact_payload:
        artifact = _safe_load_artifact(artifact_path, schema_violations)
        artifact_fingerprint = compute_artifact_fingerprint(artifact_payload)
        artifact_fingerprint_mismatch = int(
            artifact_fingerprint != row.get("artifact_fingerprint_sha256")
        )
        if artifact and artifact.artifact_id != row.get("artifact_id"):
            schema_violations.append("artifact_id")
        boundary_violations.extend(_artifact_boundary_violations(artifact_payload))
    else:
        artifact_fingerprint = ""

    if receipt:
        receipt_fingerprint = _sha256_file(receipt_path)
        source_candidate_log_path = _resolve_path(
            Path(str(receipt["source_candidate_log_path"]))
        )
        sealed_manifest_path = _resolve_path(
            Path(str(receipt["source_sealed_manifest_path"]))
        )
        source_audit_report_path = _resolve_path(
            Path(str(receipt["source_audit_report_path"]))
        )
        receipt_fingerprint_mismatch = int(
            receipt_fingerprint != row.get("promotion_receipt_fingerprint_sha256")
        )
        source_candidate_fingerprint_mismatch = int(
            _sha256_file(source_candidate_log_path)
            != receipt.get("source_candidate_log_sha256")
            or row.get("source_ast_fingerprint_sha256")
            != receipt.get("source_ast_fingerprint_sha256")
        )
        sealed_manifest_fingerprint_mismatch = int(
            _sha256_file(sealed_manifest_path)
            != receipt.get("sealed_manifest_fingerprint_sha256")
        )
        audit_report_fingerprint_mismatch = int(
            _sha256_file(source_audit_report_path)
            != receipt.get("audit_report_fingerprint_sha256")
        )
        if artifact_payload:
            expected_promotion = _promotion_fingerprint(
                artifact_payload=artifact_payload,
                source_candidate_id=str(receipt["candidate_id"]),
                source_ast_fingerprint_sha256=str(
                    receipt["source_ast_fingerprint_sha256"]
                ),
                sealed_manifest_fingerprint_sha256=str(
                    receipt["sealed_manifest_fingerprint_sha256"]
                ),
                audit_report_fingerprint_sha256=str(
                    receipt["audit_report_fingerprint_sha256"]
                ),
            )
            promotion_fingerprint_mismatch = int(
                expected_promotion != row.get("promotion_fingerprint_sha256")
                or expected_promotion != receipt.get("promotion_fingerprint_sha256")
            )
        boundary_violations.extend(_receipt_boundary_violations(receipt))

    status = (
        "PASS"
        if artifact_fingerprint_mismatch == 0
        and receipt_fingerprint_mismatch == 0
        and promotion_fingerprint_mismatch == 0
        and source_candidate_fingerprint_mismatch == 0
        and sealed_manifest_fingerprint_mismatch == 0
        and audit_report_fingerprint_mismatch == 0
        and not schema_violations
        and not boundary_violations
        else "FAIL"
    )
    return {
        "artifact_id": str(row.get("artifact_id", "")),
        "status": status,
        "artifact_path": _display_path(artifact_path),
        "promotion_receipt_path": _display_path(receipt_path),
        "artifact_fingerprint_mismatch_count": artifact_fingerprint_mismatch,
        "receipt_fingerprint_mismatch_count": receipt_fingerprint_mismatch,
        "promotion_fingerprint_mismatch_count": promotion_fingerprint_mismatch,
        "source_candidate_fingerprint_mismatch_count": source_candidate_fingerprint_mismatch,
        "sealed_manifest_fingerprint_mismatch_count": sealed_manifest_fingerprint_mismatch,
        "audit_report_fingerprint_mismatch_count": audit_report_fingerprint_mismatch,
        "schema_violation_count": len(schema_violations),
        "boundary_violation_count": len(boundary_violations),
        "schema_violations": schema_violations,
        "boundary_violations": boundary_violations,
    }


def _artifact_boundary_violations(payload: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("target_scope") != "shared_variables_only":
        violations.append("target_scope")
    provenance = payload.get("provenance")
    if not isinstance(provenance, Mapping):
        return violations + ["provenance"]
    for key in (
        "frozen",
        "no_llm",
        "no_evolution",
        "no_optimizer",
        "no_candidate_generation",
        "no_objective_evaluation",
        "no_arbitrary_executable_code",
    ):
        if provenance.get(key) is not True:
            violations.append(f"provenance.{key}")
    split_policy = payload.get("split_policy")
    if not isinstance(split_policy, Mapping):
        return violations + ["split_policy"]
    for key in ("no_test_feedback", "no_tuning_on_test", "test_mode_allowed"):
        if split_policy.get(key) is not True:
            violations.append(f"split_policy.{key}")
    return violations


def _receipt_boundary_violations(receipt: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    for key in (
        "no_llm",
        "no_evolution",
        "no_optimizer",
        "no_candidate_generation",
        "no_test_feedback",
        "no_objective_evaluation",
    ):
        if receipt.get(key) is not True:
            violations.append(f"receipt.{key}")
    return violations


def _safe_load_artifact(path: Path, schema_violations: list[str]):
    try:
        return load_frozen_operator_artifact(path)
    except (ValueError, FileNotFoundError, json.JSONDecodeError):
        schema_violations.append("operator_artifact_load")
        return None


def _safe_read_receipt(
    path: Path, schema_violations: list[str]
) -> dict[str, Any] | None:
    try:
        return load_promotion_receipt(path)
    except (ValueError, FileNotFoundError, json.JSONDecodeError):
        schema_violations.append("promotion_receipt_load")
        return _safe_read_json(path, schema_violations, "promotion_receipt_raw")


def _safe_read_json(
    path: Path, schema_violations: list[str], label: str
) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        schema_violations.append(f"{label}_read")
        return None


def _promotion_fingerprint(
    artifact_payload: Mapping[str, Any],
    source_candidate_id: str,
    source_ast_fingerprint_sha256: str,
    sealed_manifest_fingerprint_sha256: str,
    audit_report_fingerprint_sha256: str,
) -> str:
    payload = {
        "artifact": artifact_payload,
        "candidate_id": source_candidate_id,
        "source_ast_fingerprint_sha256": source_ast_fingerprint_sha256,
        "sealed_manifest_fingerprint_sha256": sealed_manifest_fingerprint_sha256,
        "audit_report_fingerprint_sha256": audit_report_fingerprint_sha256,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _sum_counts(entries: list[Mapping[str, Any]]) -> dict[str, int]:
    keys = (
        "artifact_fingerprint_mismatch_count",
        "receipt_fingerprint_mismatch_count",
        "promotion_fingerprint_mismatch_count",
        "source_candidate_fingerprint_mismatch_count",
        "sealed_manifest_fingerprint_mismatch_count",
        "audit_report_fingerprint_mismatch_count",
        "schema_violation_count",
        "boundary_violation_count",
    )
    return {key: sum(int(entry[key]) for entry in entries) for key in keys}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in _resolve_path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
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

"""Frozen candidate promotion contract for Stage 2.8.

This module promotes an already-accepted Stage 2.6 candidate row into a frozen
operator artifact only after the Stage 2.7 sealed split replay audit passes. It
does not call LLMs, run evolution, generate candidates, execute ASTs, or
evaluate objectives.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from loco.coordination.dsl import DSL_SCHEMA_VERSION, stage3_preflight_check
from loco.coordination.operator_artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    compute_artifact_fingerprint,
    load_operator_artifact_payload,
)


PROMOTION_RECEIPT_SCHEMA_VERSION = "loco.candidate_promotion_receipt.v1"
PROMOTION_REGISTRY_SCHEMA_VERSION = "loco.promoted_operator_registry.v1"
STAGE = "2.8"
REPO_ROOT = Path(__file__).resolve().parents[2]


def promote_accepted_candidate(
    candidate_id: str,
    accepted_log_path: Path | str,
    sealed_manifest_path: Path | str,
    audit_report_path: Path | str,
    output_dir: Path | str,
    registry_path: Path | str,
) -> dict[str, Any]:
    accepted_path = Path(accepted_log_path)
    manifest_path = Path(sealed_manifest_path)
    audit_path = Path(audit_report_path)
    output_path = Path(output_dir)
    registry = Path(registry_path)

    manifest = _read_json(manifest_path)
    audit_report = _read_json(audit_path)
    _validate_sealed_audit(manifest, audit_report)
    _validate_manifest_binds_candidate_log(manifest, accepted_path)

    row = _find_candidate_row(accepted_path, candidate_id)
    _validate_accepted_candidate_row(row)

    ast_payload = dict(row["ast_payload"])
    _validate_candidate_ast(row, ast_payload)
    artifact_payload = _build_artifact_payload(row, ast_payload)
    load_operator_artifact_payload(
        artifact_payload, artifact_path=output_path / "probe"
    )

    artifact_filename = f"{_safe_filename(candidate_id)}.json"
    receipt_filename = f"{_safe_filename(candidate_id)}_promotion_receipt.json"
    artifact_path = output_path / artifact_filename
    receipt_path = output_path / receipt_filename
    output_path.mkdir(parents=True, exist_ok=True)

    _write_json(artifact_path, artifact_payload)
    artifact_fingerprint = compute_artifact_fingerprint(artifact_payload)
    manifest_fingerprint = _sha256_file(_resolve_path(manifest_path))
    audit_fingerprint = _sha256_file(_resolve_path(audit_path))
    promotion_fingerprint = _promotion_fingerprint(
        artifact_payload=artifact_payload,
        candidate_row=row,
        sealed_manifest_fingerprint_sha256=manifest_fingerprint,
        audit_report_fingerprint_sha256=audit_fingerprint,
    )

    receipt = _build_receipt(
        row=row,
        artifact_path=artifact_path,
        artifact_fingerprint=artifact_fingerprint,
        sealed_manifest_path=manifest_path,
        sealed_manifest_fingerprint=manifest_fingerprint,
        audit_report_path=audit_path,
        audit_report_fingerprint=audit_fingerprint,
        accepted_log_path=accepted_path,
        promotion_fingerprint=promotion_fingerprint,
    )
    _write_json(receipt_path, receipt)

    registry_row = {
        "registry_schema_version": PROMOTION_REGISTRY_SCHEMA_VERSION,
        "stage": STAGE,
        "artifact_id": artifact_payload["artifact_id"],
        "artifact_path": _display_path(artifact_path),
        "promotion_receipt_path": _display_path(receipt_path),
        "source_candidate_id": candidate_id,
        "source_ast_fingerprint_sha256": row["ast_fingerprint_sha256"],
        "artifact_fingerprint_sha256": artifact_fingerprint,
        "promotion_fingerprint_sha256": promotion_fingerprint,
        "split": row["split"],
        "target_scope": "shared_variables_only",
        "frozen": True,
        "no_llm": True,
        "no_evolution": True,
        "no_optimizer": True,
        "no_candidate_generation": True,
        "no_test_feedback": True,
        "no_objective_evaluation": True,
    }
    _write_jsonl(registry, [registry_row])

    return {
        "schema_version": PROMOTION_RECEIPT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PROMOTED",
        "candidate_id": candidate_id,
        "artifact_id": artifact_payload["artifact_id"],
        "artifact_filename": artifact_filename,
        "artifact_path": _display_path(artifact_path),
        "promotion_receipt_path": _display_path(receipt_path),
        "registry_path": _display_path(registry),
        "artifact_fingerprint_sha256": artifact_fingerprint,
        "promotion_fingerprint_sha256": promotion_fingerprint,
        "no_llm": True,
        "no_evolution": True,
        "no_optimizer": True,
        "no_candidate_generation": True,
        "no_test_feedback": True,
        "no_objective_evaluation": True,
    }


def load_promotion_receipt(receipt_path: Path | str) -> dict[str, Any]:
    receipt = _read_json(Path(receipt_path))
    if receipt.get("schema_version") != PROMOTION_RECEIPT_SCHEMA_VERSION:
        raise ValueError("unsupported candidate promotion receipt schema_version")
    if receipt.get("stage") != STAGE:
        raise ValueError("candidate promotion receipt stage must be 2.8")
    if receipt.get("status") != "PROMOTED":
        raise ValueError("candidate promotion receipt must have status=PROMOTED")
    for key in (
        "no_llm",
        "no_evolution",
        "no_optimizer",
        "no_candidate_generation",
        "no_test_feedback",
        "no_objective_evaluation",
    ):
        if receipt.get(key) is not True:
            raise ValueError(f"candidate promotion receipt must set {key}=true")
    return receipt


def _build_artifact_payload(
    row: Mapping[str, Any],
    ast_payload: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_id = str(row["candidate_id"])
    return {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_id": f"stage2_8.promoted.{candidate_id}",
        "operator_name": "PromotedCandidateWeightedClip",
        "source": "stage2_6_accepted_candidate_promotion",
        "stage_created": STAGE,
        "template_id": f"stage2_8_promoted_{candidate_id}",
        "target_scope": "shared_variables_only",
        "dsl_schema_version": DSL_SCHEMA_VERSION,
        "provenance": {
            "frozen": True,
            "no_llm": True,
            "no_evolution": True,
            "no_optimizer": True,
            "no_objective_evaluation": True,
            "no_arbitrary_executable_code": True,
            "no_candidate_generation": True,
            "source_candidate_id": candidate_id,
            "source_ast_fingerprint_sha256": row["ast_fingerprint_sha256"],
            "source_candidate_log_stage": row["stage"],
        },
        "split_policy": {
            "split_boundary": "promoted_from_pre_stage3_schema_only_after_sealed_audit",
            "source_split": row["split"],
            "train_feedback_allowed": False,
            "validation_feedback_allowed": False,
            "test_mode_allowed": True,
            "no_test_feedback": True,
            "no_tuning_on_test": True,
        },
        "promotion_contract": {
            "schema_version": PROMOTION_RECEIPT_SCHEMA_VERSION,
            "stage": STAGE,
            "source_log_schema_version": row["log_schema_version"],
            "source_stage": row["source_stage"],
            "source_candidate_payload_sha256": row["candidate_payload_sha256"],
        },
        "ast_template": _ast_to_template(candidate_id, ast_payload),
    }


def _ast_to_template(
    candidate_id: str, ast_payload: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "operator_id_template": f"stage2_8_promoted_{candidate_id}_shared_{{variable_id}}",
        "nodes": [_node_to_template(node) for node in ast_payload["nodes"]],
        "output": dict(ast_payload["output"]),
    }


def _node_to_template(node: Mapping[str, Any]) -> dict[str, Any]:
    templated = dict(node)
    templated["target"] = {"variable_id": "$shared_variable"}
    return templated


def _build_receipt(
    row: Mapping[str, Any],
    artifact_path: Path,
    artifact_fingerprint: str,
    sealed_manifest_path: Path,
    sealed_manifest_fingerprint: str,
    audit_report_path: Path,
    audit_report_fingerprint: str,
    accepted_log_path: Path,
    promotion_fingerprint: str,
) -> dict[str, Any]:
    return {
        "schema_version": PROMOTION_RECEIPT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PROMOTED",
        "candidate_id": row["candidate_id"],
        "artifact_id": f"stage2_8.promoted.{row['candidate_id']}",
        "artifact_path": _display_path(artifact_path),
        "artifact_fingerprint_sha256": artifact_fingerprint,
        "source_candidate_log_path": _display_path(accepted_log_path),
        "source_candidate_log_sha256": _sha256_file(_resolve_path(accepted_log_path)),
        "source_ast_fingerprint_sha256": row["ast_fingerprint_sha256"],
        "source_candidate_payload_sha256": row["candidate_payload_sha256"],
        "source_split": row["split"],
        "source_sealed_manifest_path": _display_path(sealed_manifest_path),
        "sealed_manifest_fingerprint_sha256": sealed_manifest_fingerprint,
        "source_audit_report_path": _display_path(audit_report_path),
        "audit_report_fingerprint_sha256": audit_report_fingerprint,
        "promotion_fingerprint_sha256": promotion_fingerprint,
        "no_llm": True,
        "no_evolution": True,
        "no_optimizer": True,
        "no_candidate_generation": True,
        "no_test_feedback": True,
        "no_objective_evaluation": True,
    }


def _validate_sealed_audit(
    manifest: Mapping[str, Any],
    audit_report: Mapping[str, Any],
) -> None:
    if manifest.get("schema_version") != "loco.sealed_split_manifest.v1":
        raise ValueError("sealed manifest schema_version is invalid")
    if manifest.get("stage") != "2.7" or manifest.get("sealed") is not True:
        raise ValueError("sealed manifest must be Stage 2.7 and sealed")
    if manifest.get("no_test_feedback") is not True:
        raise ValueError("sealed manifest must preserve no_test_feedback")
    if audit_report.get("schema_version") != "loco.sealed_split_replay_audit.v1":
        raise ValueError("sealed split audit report schema_version is invalid")
    if audit_report.get("stage") != "2.7" or audit_report.get("status") != "PASS":
        raise ValueError("sealed split replay audit must be PASS before promotion")
    for key in (
        "file_fingerprint_mismatch_count",
        "split_violation_count",
        "test_feedback_violation_count",
        "llm_or_evolution_violation_count",
    ):
        if audit_report.get(key) != 0:
            raise ValueError(f"sealed split replay audit has nonzero {key}")


def _validate_manifest_binds_candidate_log(
    manifest: Mapping[str, Any], accepted_log_path: Path
) -> None:
    expected = _display_path(accepted_log_path)
    actual = str(manifest["candidate_logs"]["accepted"]["path"])
    if actual != expected:
        raise ValueError("sealed manifest does not bind the accepted candidate log")
    expected_sha = str(manifest["candidate_logs"]["accepted"]["sha256"])
    actual_sha = _sha256_file(_resolve_path(accepted_log_path))
    if actual_sha != expected_sha:
        raise ValueError("accepted candidate log fingerprint does not match manifest")


def _find_candidate_row(path: Path, candidate_id: str) -> dict[str, Any]:
    for row in _read_jsonl(path):
        if row.get("candidate_id") == candidate_id:
            return row
    raise ValueError(f"accepted candidate not found: {candidate_id}")


def _validate_accepted_candidate_row(row: Mapping[str, Any]) -> None:
    if row.get("log_schema_version") != "loco.candidate_log.v1":
        raise ValueError("candidate log row has invalid schema")
    if row.get("stage") != "2.6":
        raise ValueError("candidate log row must come from Stage 2.6")
    if row.get("decision") != "accepted":
        raise ValueError("only accepted candidates can be promoted")
    if row.get("split") != "pre_stage3_schema_only":
        raise ValueError("candidate split is not eligible for promotion")
    for key in (
        "no_llm",
        "no_evolution",
        "no_optimizer",
        "no_test_feedback",
        "no_objective_evaluation",
    ):
        if row.get(key) is not True:
            raise ValueError(f"candidate row must set {key}=true")


def _validate_candidate_ast(
    row: Mapping[str, Any], ast_payload: Mapping[str, Any]
) -> None:
    report = stage3_preflight_check(
        [ast_payload],
        shared_variables=_target_variables_from_ast(ast_payload),
    )
    if report.accepted_count != 1:
        raise ValueError("candidate AST no longer passes shared-variable preflight")
    if report.accepted[0].fingerprint_sha256 != row.get("ast_fingerprint_sha256"):
        raise ValueError("candidate AST fingerprint mismatch")


def _target_variables_from_ast(ast_payload: Mapping[str, Any]) -> set[int]:
    nodes = ast_payload.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("candidate AST nodes must be a non-empty list")
    variables: set[int] = set()
    for node in nodes:
        if not isinstance(node, Mapping):
            raise ValueError("candidate AST node must be a mapping")
        target = node.get("target")
        if not isinstance(target, Mapping):
            raise ValueError("candidate AST node target must be a mapping")
        variable_id = target.get("variable_id")
        if not isinstance(variable_id, int):
            raise ValueError("candidate AST target variable_id must be an integer")
        variables.add(variable_id)
    return variables


def _promotion_fingerprint(
    artifact_payload: Mapping[str, Any],
    candidate_row: Mapping[str, Any],
    sealed_manifest_fingerprint_sha256: str,
    audit_report_fingerprint_sha256: str,
) -> str:
    payload = {
        "artifact": artifact_payload,
        "candidate_id": candidate_row["candidate_id"],
        "source_ast_fingerprint_sha256": candidate_row["ast_fingerprint_sha256"],
        "sealed_manifest_fingerprint_sha256": sealed_manifest_fingerprint_sha256,
        "audit_report_fingerprint_sha256": audit_report_fingerprint_sha256,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _safe_filename(text: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in text)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(_resolve_path(path).read_text(encoding="utf-8"))


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


def _write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


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

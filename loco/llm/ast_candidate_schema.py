"""Stage 3.0 LLM candidate wrapper schema and protocol gate.

This module validates the protocol wrapper around the existing typed
coordination-operator AST. It does not call LLMs, run evolution, execute ASTs,
evaluate objective functions, or implement optimizers.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from loco.coordination.dsl import (
    CoordinationOperatorAST,
    load_coordination_ast,
    serialize_coordination_ast,
    validate_coordination_ast,
)


LLM_CANDIDATE_SCHEMA_VERSION = "loco.llm_candidate.v1"
LLM_CANDIDATE_VALIDATION_SCHEMA_VERSION = "loco.llm_candidate_validation.v1"
STAGE3_PROTOCOL_LOCK_SCHEMA_VERSION = "loco.stage3_protocol_lock.v1"
REPO_ROOT = Path(__file__).resolve().parents[2]

ALLOWED_TOP_LEVEL_FIELDS = frozenset(
    {"schema_version", "candidate_id", "generator", "ast", "declared_scope"}
)
ALLOWED_GENERATOR_FIELDS = frozenset(
    {"type", "provider", "model", "prompt_contract_version"}
)
ALLOWED_SCOPE_FIELDS = frozenset(
    {
        "target",
        "not_optimizer",
        "not_controller",
        "not_scheduler",
        "not_optimizer_selection",
        "not_benchmark_specific",
        "no_test_feedback",
    }
)
REQUIRED_TRUE_SCOPE_FLAGS = (
    "not_optimizer",
    "not_controller",
    "not_scheduler",
    "not_optimizer_selection",
    "not_benchmark_specific",
    "no_test_feedback",
)


@dataclass(frozen=True)
class LLMCandidatePayload:
    schema_version: str
    candidate_id: str
    generator: Mapping[str, Any]
    ast: CoordinationOperatorAST
    declared_scope: Mapping[str, Any]


@dataclass(frozen=True)
class LLMCandidateValidationReport:
    schema_version: str
    candidate_id: str
    ast_operator_id: str
    target_scope: str
    no_test_feedback: bool
    ast_fingerprint_sha256: str


def load_llm_candidate_payload(payload: Mapping[str, Any]) -> LLMCandidatePayload:
    """Load the Stage 3.0 candidate wrapper without executing anything."""

    if not isinstance(payload, Mapping):
        raise ValueError("LLM candidate payload must be a mapping.")
    _reject_unknown_fields(payload, ALLOWED_TOP_LEVEL_FIELDS, "top-level")

    schema_version = _require_string(payload, "schema_version")
    if schema_version != LLM_CANDIDATE_SCHEMA_VERSION:
        raise ValueError(f"Unsupported LLM candidate schema_version: {schema_version}")

    candidate_id = _require_string(payload, "candidate_id")
    generator = payload.get("generator")
    if not isinstance(generator, Mapping):
        raise ValueError("LLM candidate generator must be a mapping.")
    _reject_unknown_fields(generator, ALLOWED_GENERATOR_FIELDS, "generator")
    if generator.get("type") != "llm":
        raise ValueError("LLM candidate generator.type must be llm.")

    declared_scope = payload.get("declared_scope")
    if not isinstance(declared_scope, Mapping):
        raise ValueError("LLM candidate declared_scope must be a mapping.")
    _reject_unknown_fields(declared_scope, ALLOWED_SCOPE_FIELDS, "declared_scope")

    ast_payload = payload.get("ast")
    if not isinstance(ast_payload, Mapping):
        raise ValueError("LLM candidate ast must be a mapping.")

    return LLMCandidatePayload(
        schema_version=schema_version,
        candidate_id=candidate_id,
        generator=dict(generator),
        ast=load_coordination_ast(ast_payload),
        declared_scope=dict(declared_scope),
    )


def validate_llm_candidate_payload(
    candidate: LLMCandidatePayload,
    shared_variables: set[int] | frozenset[int],
) -> LLMCandidateValidationReport:
    """Validate candidate wrapper and reuse the Stage 2 typed-AST boundary."""

    target = candidate.declared_scope.get("target")
    if target != "shared_variables_only":
        raise ValueError("declared_scope target must be shared_variables_only.")
    for flag in REQUIRED_TRUE_SCOPE_FLAGS:
        if candidate.declared_scope.get(flag) is not True:
            raise ValueError(f"declared_scope flag must be true: {flag}")

    validate_coordination_ast(candidate.ast, shared_variables=shared_variables)
    serialized_ast = serialize_coordination_ast(candidate.ast)
    return LLMCandidateValidationReport(
        schema_version=LLM_CANDIDATE_VALIDATION_SCHEMA_VERSION,
        candidate_id=candidate.candidate_id,
        ast_operator_id=candidate.ast.operator_id,
        target_scope=str(target),
        no_test_feedback=candidate.declared_scope["no_test_feedback"] is True,
        ast_fingerprint_sha256=hashlib.sha256(
            serialized_ast.encode("utf-8")
        ).hexdigest(),
    )


def evaluate_stage3_protocol_lock(
    *,
    readiness_decision_path: Path | str,
    protocol_config_path: Path | str,
    report_path: Path | str,
) -> dict[str, Any]:
    """Evaluate Stage 3.0 protocol readiness without running search."""

    readiness = _read_json(Path(readiness_decision_path))
    config = _read_yaml_like(Path(protocol_config_path))
    allowed = (
        readiness.get("decision") == "READY_FOR_STAGE3_BOUNDARY_ONLY"
        and readiness.get("stage3_allowed") is True
    )
    status = "PASS" if allowed else "BLOCKED"
    result = {
        "schema_version": STAGE3_PROTOCOL_LOCK_SCHEMA_VERSION,
        "stage": "3.0",
        "status": status,
        "stage3_allowed": allowed,
        "readiness_decision": readiness.get("decision"),
        "protocol_config": _display_path(Path(protocol_config_path)),
        "allowed_search_target": "typed coordination operator AST",
        "target_scope": "shared_variables_only",
        "split_protocol": {
            "train": "candidate generation and evolution selection only",
            "validation": "model/operator selection only",
            "test": "sealed final reporting only",
        },
        "required_before_generation": [
            "READY_FOR_STAGE3_BOUNDARY_ONLY",
            "prompt_contract_locked",
            "candidate_schema_locked",
            "test_feedback_firewall_locked",
        ],
        "config_mentions_test_firewall": "test_feedback_firewall" in config,
        "no_llm_call": True,
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "not_performance_claim": True,
    }
    _write_json(Path(report_path), result)
    return result


def _reject_unknown_fields(
    payload: Mapping[str, Any], allowed_fields: frozenset[str], scope: str
) -> None:
    unknown_fields = set(payload) - allowed_fields
    if unknown_fields:
        raise ValueError(f"Unknown {scope} fields: {sorted(unknown_fields)}")


def _require_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"LLM candidate field must be a non-empty string: {key}")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(_resolve_path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    resolved = _resolve_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_yaml_like(path: Path) -> str:
    return _resolve_path(path).read_text(encoding="utf-8")


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

"""Stage 5.1 selected-operator freeze before sealed-test reporting.

This module freezes the single Stage 5.0 selected coordination operator as the
only candidate eligible for sealed-test reporting. It does not call an LLM,
generate candidates, revise prompts/search/selection rules, access sealed test
data, evaluate objectives, or make a performance claim.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "5.1"
SELECTED_OPERATOR_SCHEMA_VERSION = "loco.stage5_1_selected_operator.v1"
MANIFEST_SCHEMA_VERSION = "loco.stage5_1_selected_operator_manifest.v1"
PROTOCOL_SCHEMA_VERSION = "loco.stage5_1_sealed_test_readiness_protocol.v1"
REPORT_SCHEMA_VERSION = "loco.stage5_1_freeze_report.v1"


def freeze_stage5_1_selected_operator(
    *,
    selection_decision_path: Path | str,
    validation_report_path: Path | str,
    frozen_pool_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Freeze the Stage 5.0 selected operator for sealed-test reporting."""

    selection_decision_path = Path(selection_decision_path)
    validation_report_path = Path(validation_report_path)
    frozen_pool_path = Path(frozen_pool_path)
    selection_decision = _read_json(selection_decision_path)
    validation_report = _read_json(validation_report_path)
    frozen_rows = _read_jsonl(frozen_pool_path)

    _validate_stage5_0_inputs(selection_decision, validation_report)
    selected_candidate_id = str(selection_decision["selected_candidate_id"])
    frozen_row = _selected_frozen_row(frozen_rows, selected_candidate_id)

    selected_operator = _build_selected_operator(selection_decision, frozen_row)
    selected_ast = frozen_row["llm_candidate_payload"]["ast"]
    selected_operator_hash = _fingerprint_payload(selected_operator)
    selected_ast_hash = _fingerprint_payload(selected_ast)
    manifest = _build_manifest(
        selection_decision=selection_decision,
        frozen_row=frozen_row,
        selected_operator=selected_operator,
        selected_operator_hash=selected_operator_hash,
        selected_ast_hash=selected_ast_hash,
        source_selection_decision_hash=_fingerprint_payload(selection_decision),
        source_validation_report_hash=_fingerprint_payload(validation_report),
        source_frozen_candidate_hash=_fingerprint_payload(frozen_row),
    )
    protocol = _build_protocol(manifest)
    report = _build_report(manifest, protocol)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "selected_operator.json", selected_operator)
    _write_json(output_path / "selected_operator_ast.json", selected_ast)
    _write_json(output_path / "selected_operator_manifest.json", manifest)
    _write_json(output_path / "sealed_test_readiness_protocol.json", protocol)
    _write_json(output_path / "freeze_report.json", report)
    return report


def _validate_stage5_0_inputs(
    selection_decision: Mapping[str, Any], validation_report: Mapping[str, Any]
) -> None:
    if selection_decision.get("stage") != "5.0":
        raise ValueError("Stage 5.1 requires Stage 5.0 selection decision.")
    if selection_decision.get("status") != "PASS":
        raise ValueError("Stage 5.1 requires PASS selection decision.")
    if (
        selection_decision.get("selection_status")
        != "SELECTED_FOR_SEALED_TEST_NOT_FINAL"
    ):
        raise ValueError("Stage 5.1 requires selected-for-sealed-test status.")
    if validation_report.get("stage") != "5.0":
        raise ValueError("Stage 5.1 requires Stage 5.0 validation report.")
    if validation_report.get("status") != "PASS":
        raise ValueError("Stage 5.1 requires PASS validation report.")
    if (
        validation_report.get("next_status")
        != "READY_FOR_STAGE5_1_SELECTED_OPERATOR_FREEZE"
    ):
        raise ValueError("Stage 5.1 requires Stage 5.0 readiness.")
    if validation_report.get("selected_candidate_id") != selection_decision.get(
        "selected_candidate_id"
    ):
        raise ValueError("Stage 5.0 report and decision selected different candidates.")

    forbidden_true_fields = [
        "test_feedback_used",
        "sealed_test_access_used",
        "objective_evaluation_used",
        "llm_call_used",
        "new_candidate_generation_used",
        "prompt_revision_used",
        "train_search_revision_used",
        "promotion_rule_revision_used",
        "baseopt_modified",
        "optimizer_generation_used",
        "controller_scheduler_generation_used",
    ]
    for field in forbidden_true_fields:
        if (
            selection_decision.get(field) is True
            or validation_report.get(field) is True
        ):
            raise ValueError(f"Stage 5.1 input violates boundary: {field}")
    if selection_decision.get("not_performance_claim") is not True:
        raise ValueError("Stage 5.1 requires selection claim boundary.")
    if validation_report.get("not_performance_claim") is not True:
        raise ValueError("Stage 5.1 requires validation-report claim boundary.")


def _selected_frozen_row(
    frozen_rows: Sequence[Mapping[str, Any]], selected_candidate_id: str
) -> Mapping[str, Any]:
    matches = [
        row
        for row in frozen_rows
        if str(row.get("candidate_id")) == selected_candidate_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one frozen candidate row for {selected_candidate_id}."
        )
    row = matches[0]
    if row.get("frozen") is not True:
        raise ValueError("Selected candidate must come from the frozen pool.")
    if row.get("target_scope") != "shared_variables_only":
        raise ValueError("Selected operator must target shared variables only.")
    if row.get("no_llm_call") is not True:
        raise ValueError("Frozen row must preserve no-LLM boundary.")
    if row.get("no_test_feedback") is not True:
        raise ValueError("Frozen row must preserve no-test-feedback boundary.")
    if row.get("no_objective_evaluation") is not True:
        raise ValueError("Frozen row must preserve no-objective-evaluation boundary.")
    if row.get("not_performance_claim") is not True:
        raise ValueError("Frozen row must preserve claim boundary.")
    return row


def _build_selected_operator(
    selection_decision: Mapping[str, Any], frozen_row: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": SELECTED_OPERATOR_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "5.0",
        "candidate_id": str(frozen_row["candidate_id"]),
        "freeze_status": "FROZEN_FOR_SEALED_TEST_NOT_FINAL",
        "selection_status": str(selection_decision["selection_status"]),
        "operator_family": str(frozen_row["operator_family"]),
        "kind_sequence": str(frozen_row["kind_sequence"]),
        "node_count": int(frozen_row["node_count"]),
        "target_scope": "shared_variables_only",
        "target_variable_set": list(frozen_row["target_variable_set"]),
        "selected_validation_score": float(
            selection_decision["selected_validation_score"]
        ),
        "ast_fingerprint_sha256": str(frozen_row["ast_fingerprint_sha256"]),
        "candidate_payload_sha256": str(frozen_row["candidate_payload_sha256"]),
        "stage3_6_freeze_fingerprint_sha256": str(
            frozen_row["freeze_fingerprint_sha256"]
        ),
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "sealed_test_access_used": False,
        "objective_evaluation_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "prompt_revision_used": False,
        "train_search_revision_used": False,
        "promotion_rule_revision_used": False,
        "validation_rule_revision_used": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_performance_claim": True,
    }


def _build_manifest(
    *,
    selection_decision: Mapping[str, Any],
    frozen_row: Mapping[str, Any],
    selected_operator: Mapping[str, Any],
    selected_operator_hash: str,
    selected_ast_hash: str,
    source_selection_decision_hash: str,
    source_validation_report_hash: str,
    source_frozen_candidate_hash: str,
) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "5.0",
        "selected_operator_frozen": True,
        "candidate_count": 1,
        "selected_candidate_id": str(selected_operator["candidate_id"]),
        "selected_operator_family": str(selected_operator["operator_family"]),
        "selected_kind_sequence": str(selected_operator["kind_sequence"]),
        "selected_validation_score": float(
            selection_decision["selected_validation_score"]
        ),
        "source_selection_decision_sha256": source_selection_decision_hash,
        "source_validation_report_sha256": source_validation_report_hash,
        "source_frozen_candidate_sha256": source_frozen_candidate_hash,
        "selected_operator_freeze_sha256": selected_operator_hash,
        "selected_operator_ast_sha256": selected_ast_hash,
        "stage3_6_freeze_fingerprint_sha256": str(
            frozen_row["freeze_fingerprint_sha256"]
        ),
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "sealed_test_access_used": False,
        "objective_evaluation_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "prompt_revision_used": False,
        "train_search_revision_used": False,
        "promotion_rule_revision_used": False,
        "validation_rule_revision_used": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_performance_claim": True,
    }


def _build_protocol(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "READY_FOR_STAGE6_SEALED_TEST_REPORTING",
        "selected_candidate_id": str(manifest["selected_candidate_id"]),
        "selected_operator_freeze_sha256": str(
            manifest["selected_operator_freeze_sha256"]
        ),
        "allowed_next_use": "sealed test final reporting only",
        "test_usage": "sealed final reporting only",
        "validation_usage": "already used only for Stage 5.0 selection",
        "base_optimizer_policy": "BaseOpt must remain fixed",
        "fe_accounting_policy": (
            "FE_total = FE_grouping + FE_proposal + "
            "FE_coordination_extra + FE_repair"
        ),
        "oracle_detected_grouping_policy": (
            "oracle grouping and detected grouping must be reported separately"
        ),
        "no_llm_call": True,
        "no_new_candidate_generation": True,
        "no_prompt_revision": True,
        "no_train_search_revision": True,
        "no_promotion_rule_revision": True,
        "no_validation_rule_revision": True,
        "no_test_feedback": True,
        "no_sealed_test_access_in_stage5_1": True,
        "no_objective_evaluation": True,
        "no_baseopt_modification": True,
        "no_optimizer_generation": True,
        "no_controller_scheduler_generation": True,
        "not_performance_claim": True,
    }


def _build_report(
    manifest: Mapping[str, Any], protocol: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "5.0",
        "selected_candidate_id": str(manifest["selected_candidate_id"]),
        "selected_operator_frozen": True,
        "candidate_count": 1,
        "sealed_test_ready": protocol["status"]
        == "READY_FOR_STAGE6_SEALED_TEST_REPORTING",
        "next_status": "READY_FOR_STAGE6_SEALED_TEST_REPORTING",
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "sealed_test_access_used": False,
        "objective_evaluation_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "prompt_revision_used": False,
        "train_search_revision_used": False,
        "promotion_rule_revision_used": False,
        "validation_rule_revision_used": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_performance_claim": True,
    }


def _fingerprint_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

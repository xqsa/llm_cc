"""Stage 7.4 optional CEC2013 F13/F14 panel decision gate.

This stage decides whether a real CEC2013 F13/F14 objective panel is warranted
after the mixed Stage 7.3 synthetic evidence. It prepares a protocol but does
not run the panel or perform any new objective evaluation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


STAGE = "7.4"
DECISION_SCHEMA_VERSION = "loco.stage7_4_cec2013_panel_decision.v1"
PROTOCOL_SCHEMA_VERSION = "loco.stage7_4_cec2013_optional_panel_protocol.v1"
READINESS_SCHEMA_VERSION = "loco.stage7_4_cec2013_readiness_summary.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage7_4_claim_boundary.v1"
REPORT_SCHEMA_VERSION = "loco.stage7_4_decision_report.v1"

LOCKED_METHODS = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "selected_loco_operator",
]


def run_stage7_4_cec2013_panel_decision(
    *,
    stage7_3_report_path: Path | str,
    stage7_3_ranking_path: Path | str,
    stage7_3_claim_boundary_path: Path | str,
    metabox_smoke_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Prepare the optional CEC2013 F13/F14 decision artifacts."""

    stage7_3_report = _read_json(Path(stage7_3_report_path))
    stage7_3_ranking = _read_json(Path(stage7_3_ranking_path))
    stage7_3_boundary = _read_json(Path(stage7_3_claim_boundary_path))
    metabox_smoke = _read_json(Path(metabox_smoke_path))
    _validate_inputs(stage7_3_report, stage7_3_ranking, stage7_3_boundary)

    readiness = _build_readiness_summary(metabox_smoke)
    decision = _build_decision(stage7_3_report, stage7_3_ranking, readiness)
    protocol = _build_protocol(readiness)
    claim_boundary = _build_claim_boundary()
    report = _build_report(decision, protocol, readiness, claim_boundary)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "cec2013_panel_decision.json", decision)
    _write_json(output_path / "cec2013_optional_panel_protocol.json", protocol)
    _write_json(output_path / "cec2013_readiness_summary.json", readiness)
    _write_json(output_path / "claim_boundary.json", claim_boundary)
    _write_json(output_path / "decision_report.json", report)
    return report


def _validate_inputs(
    report: Mapping[str, Any],
    ranking: Mapping[str, Any],
    boundary: Mapping[str, Any],
) -> None:
    if report.get("stage") != "7.3" or report.get("status") != "PASS":
        raise ValueError("Stage 7.4 requires a PASS Stage 7.3 report.")
    if report.get("next_status") != "READY_FOR_OPTIONAL_CEC2013_OR_PAPER_DRAFT":
        raise ValueError("Stage 7.3 report is not ready for Stage 7.4.")
    if ranking.get("selected_loco_operator_rank_overall") == 1:
        raise ValueError("Stage 7.4 decision assumes mixed evidence, not a win claim.")
    if boundary.get("requires_optional_cec2013_decision") is not True:
        raise ValueError(
            "Stage 7.3 boundary does not request optional CEC2013 decision."
        )
    for flag in [
        "new_objective_evaluation_used",
        "test_feedback_tuning_used",
        "llm_call_used",
        "new_candidate_generation_used",
        "selected_operator_revision_used",
    ]:
        if boundary.get(flag) is True:
            raise ValueError(f"Stage 7.3 boundary violates decision input: {flag}")


def _build_readiness_summary(smoke: Mapping[str, Any]) -> dict[str, Any]:
    functions = {item["function_id"]: item for item in smoke.get("functions", [])}
    f13 = functions.get(13, {})
    f14 = functions.get(14, {})
    f13_checks = f13.get("checks", {})
    f14_checks = f14.get("checks", {})
    overlap_ratio = float(
        f14_checks.get("overlap_ratio", f13_checks.get("overlap_ratio", 0.0))
    )
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source": "docs/stage1/metabox_real_smoke_latest.json",
        "metabox_smoke_status": smoke.get("status"),
        "f13_ready": bool(f13.get("ok"))
        and bool(f13_checks.get("official_overlap_metadata_ok")),
        "f14_ready": bool(f14.get("ok"))
        and bool(f14_checks.get("official_overlap_metadata_ok")),
        "f13_adapter_mode": f13_checks.get("adapter_mode"),
        "f14_adapter_mode": f14_checks.get("adapter_mode"),
        "f13_D_formula": int(f13_checks.get("D_formula", 0)),
        "f13_D_api": int(f13_checks.get("D_api", 0)),
        "f14_D_formula": int(f14_checks.get("D_formula", 0)),
        "f14_D_api": int(f14_checks.get("D_api", 0)),
        "f13_shared_variable_count": int(f13_checks.get("shared_variable_count", 0)),
        "f14_shared_variable_count": int(f14_checks.get("shared_variable_count", 0)),
        "overlap_size": int(
            f14_checks.get("overlap_size", f13_checks.get("overlap_size", 0))
        ),
        "overlap_ratio": overlap_ratio,
        "normal_import_required": False,
        "benchmark_only_import_ok": bool(
            smoke.get("benchmark_only_import", {}).get("ok")
        ),
        "not_final_performance_claim": True,
    }


def _build_decision(
    report: Mapping[str, Any],
    ranking: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    can_run = bool(readiness["f13_ready"]) and bool(readiness["f14_ready"])
    decision = (
        "RUN_OPTIONAL_CEC2013_F13_F14_PANEL"
        if can_run
        else "PREPARE_CEC2013_PANEL_BUT_ENVIRONMENT_NOT_READY"
    )
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.3",
        "decision": decision,
        "decision_reason": "stage7_3_mixed_synthetic_evidence_needs_real_overlap_panel",
        "requires_real_overlap_panel": True,
        "paper_draft_without_cec2013_allowed": True,
        "best_overall_method": ranking["best_overall_method"],
        "selected_loco_operator_rank_overall": int(
            ranking["selected_loco_operator_rank_overall"]
        ),
        "selected_loco_operator_best_panel_dimension_count": int(
            ranking["selected_loco_operator_best_panel_dimension_count"]
        ),
        "stage7_3_polish_scope": report["polish_scope"],
        "metabox_smoke_status": readiness["metabox_smoke_status"],
        "f13_ready": bool(readiness["f13_ready"]),
        "f14_ready": bool(readiness["f14_ready"]),
        "cec2013_panel_run": False,
        "new_objective_evaluation_used": False,
        "selected_operator_revision_used": False,
        "test_feedback_tuning_used": False,
        "not_final_performance_claim": True,
        "not_sota_claim": True,
    }


def _build_protocol(readiness: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PREPARED_NOT_EXECUTED",
        "source_stage": "7.4",
        "target_functions": ["F13", "F14"],
        "function_semantics": {
            "F13": {
                "role": "conforming-overlap sanity/stability panel",
                "overlap_semantics": "conforming_overlap",
                "D_formula": int(readiness["f13_D_formula"]),
                "D_api": int(readiness["f13_D_api"]),
                "adapter_mode": readiness["f13_adapter_mode"],
                "shared_variable_count": int(readiness["f13_shared_variable_count"]),
                "overlap_ratio": float(readiness["overlap_ratio"]),
            },
            "F14": {
                "role": "primary real conflicting-overlap panel",
                "overlap_semantics": "conflicting_overlap",
                "D_formula": int(readiness["f14_D_formula"]),
                "D_api": int(readiness["f14_D_api"]),
                "adapter_mode": readiness["f14_adapter_mode"],
                "shared_variable_count": int(readiness["f14_shared_variable_count"]),
                "overlap_ratio": float(readiness["overlap_ratio"]),
            },
        },
        "locked_methods": LOCKED_METHODS,
        "same_budget_across_methods": True,
        "all_extra_fe_counted": True,
        "oracle_and_detected_grouping_reported_separately": True,
        "selected_operator_policy": "frozen_no_revision",
        "base_optimizer_policy": "fixed_baseopt_no_modification",
        "allowed_next_execution": "Stage 7.5 optional CEC2013 protocol or paper draft",
        "execution_status": "NOT_RUN_IN_STAGE7_4",
        "new_objective_evaluation_used": False,
        "not_final_performance_claim": True,
    }


def _build_claim_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "decision gate only; no CEC2013 objective panel run",
        "allowed_claims": [
            "Stage 7.4 decides that an optional CEC2013 F13/F14 panel is warranted before strong empirical claims.",
            "Stage 7.4 prepares a bounded protocol for F13/F14 but does not execute it.",
            "A paper draft may still proceed as a failure-honest prototype if it clearly states the Stage 7.3 mixed evidence.",
        ],
        "forbidden_claims": [
            "official CEC2013 performance claim",
            "F13/F14 objective improvement",
            "final objective-value performance superiority",
            "SOTA improvement",
            "BaseOpt improvement",
            "optimizer generation",
        ],
        "cec2013_panel_run": False,
        "new_objective_evaluation_used": False,
        "selected_operator_revision_used": False,
        "test_feedback_tuning_used": False,
        "not_final_performance_claim": True,
        "not_sota_claim": True,
    }


def _build_report(
    decision: Mapping[str, Any],
    protocol: Mapping[str, Any],
    readiness: Mapping[str, Any],
    claim_boundary: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.3",
        "decision_scope": "optional_cec2013_f13_f14_objective_panel_decision",
        "decision": decision["decision"],
        "decision_reason": decision["decision_reason"],
        "protocol_status": protocol["status"],
        "metabox_smoke_status": readiness["metabox_smoke_status"],
        "f13_ready": readiness["f13_ready"],
        "f14_ready": readiness["f14_ready"],
        "claim_boundary_written": claim_boundary["status"] == "PASS",
        "cec2013_panel_run": False,
        "new_objective_evaluation_used": False,
        "selected_operator_revision_used": False,
        "not_final_performance_claim": True,
        "not_sota_claim": True,
        "next_status": "READY_FOR_STAGE7_5_OPTIONAL_CEC2013_PANEL_PROTOCOL_OR_PAPER_DRAFT",
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

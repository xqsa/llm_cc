"""Stage 8.10 route decision for official-like panel vs policy generalization.

This stage is decision-only. It reads Stage 8.9 failure-honest interpretation
and the Stage 7.5/7.6 SOTA-facing protocol artifacts, then records whether the
next SOTA-targeted step should be an official-like panel or policy
generalization. It performs no objective-loop execution and no new objective
evaluation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


STAGE = "8.10"
ROUTE_SCHEMA_VERSION = "loco.stage8_10_route_decision.v1"
GAP_SCHEMA_VERSION = "loco.stage8_10_sota_gap_report.v1"
REQUIREMENTS_SCHEMA_VERSION = "loco.stage8_10_policy_generalization_requirements.v1"
READINESS_SCHEMA_VERSION = "loco.stage8_10_official_like_panel_readiness.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_10_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_10_runtime_boundary.v1"

DECISION = "PRIORITIZE_POLICY_GENERALIZATION_BEFORE_OFFICIAL_SOTA_CLAIM"
DECISION_REASON = (
    "Stage 8.9 shows bounded synthetic utility but no win over the best "
    "simple baseline, so official-like evaluation is not the best next "
    "SOTA-targeted move."
)
NEXT_STAGE = "Stage 8.11"
NEXT_WORK = "policy_generalization_beyond_best_simple_baseline"


def run_stage8_10_official_like_policy_generalization_decision(
    *,
    stage8_9_interpretation_path: Path | str,
    stage8_9_claim_boundary_path: Path | str,
    stage8_9_readiness_path: Path | str,
    stage8_9_fe_ledger_path: Path | str,
    stage8_9_runtime_boundary_path: Path | str,
    stage7_5_sota_protocol_path: Path | str,
    stage7_5_claim_contract_path: Path | str,
    stage7_6_comparator_audit_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Write Stage 8.10 route-decision artifacts."""

    interpretation = _read_json(Path(stage8_9_interpretation_path))
    claim_boundary = _read_json(Path(stage8_9_claim_boundary_path))
    readiness = _read_json(Path(stage8_9_readiness_path))
    fe_ledger = _read_json(Path(stage8_9_fe_ledger_path))
    runtime_boundary = _read_json(Path(stage8_9_runtime_boundary_path))
    sota_protocol = _read_json(Path(stage7_5_sota_protocol_path))
    claim_contract = _read_json(Path(stage7_5_claim_contract_path))
    comparator_audit = _read_json(Path(stage7_6_comparator_audit_path))
    _validate_inputs(
        interpretation=interpretation,
        claim_boundary=claim_boundary,
        readiness=readiness,
        fe_ledger=fe_ledger,
        runtime_boundary=runtime_boundary,
        sota_protocol=sota_protocol,
        claim_contract=claim_contract,
        comparator_audit=comparator_audit,
    )

    ledger = _build_fe_ledger(fe_ledger)
    gap = _build_sota_gap_report(
        interpretation=interpretation,
        sota_protocol=sota_protocol,
        claim_contract=claim_contract,
        comparator_audit=comparator_audit,
    )
    requirements = _build_policy_requirements()
    official_readiness = _build_official_readiness()
    boundary = _build_runtime_boundary()
    next_route = _build_next_route()
    route = _build_route_decision(
        interpretation=interpretation,
        ledger=ledger,
        gap=gap,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "sota_gap_report.json", gap)
    _write_json(output_path / "route_decision.json", route)
    _write_json(output_path / "policy_generalization_requirements.json", requirements)
    _write_json(output_path / "official_like_panel_readiness.json", official_readiness)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", next_route)
    return route


def _validate_inputs(
    *,
    interpretation: Mapping[str, Any],
    claim_boundary: Mapping[str, Any],
    readiness: Mapping[str, Any],
    fe_ledger: Mapping[str, Any],
    runtime_boundary: Mapping[str, Any],
    sota_protocol: Mapping[str, Any],
    claim_contract: Mapping[str, Any],
    comparator_audit: Mapping[str, Any],
) -> None:
    if interpretation.get("stage") != "8.9" or interpretation.get("status") != "PASS":
        raise ValueError("Stage 8.10 requires a passing Stage 8.9 interpretation.")
    if claim_boundary.get("stage") != "8.9" or claim_boundary.get("status") != "PASS":
        raise ValueError("Stage 8.10 requires a passing Stage 8.9 claim boundary.")
    if readiness.get("stage") != "8.9" or readiness.get("status") != "PASS":
        raise ValueError("Stage 8.10 requires a passing Stage 8.9 readiness report.")
    if fe_ledger.get("stage") != "8.9" or fe_ledger.get("status") != "PASS":
        raise ValueError("Stage 8.10 requires a passing Stage 8.9 FE ledger.")
    if (
        runtime_boundary.get("stage") != "8.9"
        or runtime_boundary.get("status") != "PASS"
    ):
        raise ValueError("Stage 8.10 requires a passing Stage 8.9 runtime boundary.")
    if sota_protocol.get("stage") != "7.5" or sota_protocol.get("status") != "PASS":
        raise ValueError("Stage 8.10 requires the Stage 7.5 SOTA protocol lock.")
    if claim_contract.get("stage") != "7.5" or claim_contract.get("status") != "PASS":
        raise ValueError("Stage 8.10 requires the Stage 7.5 claim contract.")
    if (
        comparator_audit.get("stage") != "7.6"
        or comparator_audit.get("status") != "PASS"
    ):
        raise ValueError("Stage 8.10 requires the Stage 7.6 comparator audit.")
    if interpretation.get("conditional_vs_best_baseline") != {
        "loss": 0,
        "tie": 36,
        "win": 0,
    }:
        raise ValueError("Stage 8.10 expects Stage 8.9 to tie best baseline.")
    if interpretation.get("not_sota_claim") is not True:
        raise ValueError("Stage 8.10 requires no prior SOTA claim.")
    if claim_boundary.get("sota_claim_allowed") is not False:
        raise ValueError("Stage 8.10 refuses a Stage 8.9 SOTA-ready claim boundary.")
    if readiness.get("official_benchmark_claim_ready") is not False:
        raise ValueError("Stage 8.10 expects official benchmark claim to be blocked.")
    if int(fe_ledger["FE_total"]) != 0:
        raise ValueError("Stage 8.10 expects Stage 8.9 to have zero new FE.")
    if (
        runtime_boundary.get("forbidden_behaviors", {}).get("test_feedback")
        is not False
    ):
        raise ValueError("Stage 8.10 refuses test-feedback-contaminated inputs.")
    if (
        sota_protocol.get("reported_results_direct_comparison_requires_same_setting")
        is not True
    ):
        raise ValueError("Stage 8.10 requires same-setting comparator rules.")
    if comparator_audit.get("reported_results_are_audit_only") is not True:
        raise ValueError("Stage 8.10 refuses reported results as runtime feedback.")


def _build_route_decision(
    *,
    interpretation: Mapping[str, Any],
    ledger: Mapping[str, Any],
    gap: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.9",
        "decision_scope": "official_like_panel_or_policy_generalization",
        "decision": DECISION,
        "decision_reason": DECISION_REASON,
        "best_baseline_beaten": False,
        "conditional_vs_best_baseline": dict(
            interpretation["conditional_vs_best_baseline"]
        ),
        "simple_preferred_case_recovery_count": int(
            interpretation["simple_preferred_case_recovery_count"]
        ),
        "official_like_panel_ready": "partial",
        "policy_generalization_required": True,
        "run_official_like_panel_now": False,
        "run_policy_generalization_next": True,
        "next_stage": NEXT_STAGE,
        "allowed_next_work": NEXT_WORK,
        "recommended_next_stage": NEXT_STAGE,
        "recommended_next_work": NEXT_WORK,
        "current_frontier": gap["current_frontier"],
        "sota_gap": gap["sota_gap"],
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "FE_total": int(ledger["FE_total"]),
        "inherited_stage8_9_FE_total": int(ledger["inherited_stage8_9_FE_total"]),
        "sota_claim_ready": False,
        "official_benchmark_claim_ready": False,
        "final_performance_claim_ready": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "selected_operator_revision_used": False,
        "evolution_search_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_sota_gap_report(
    *,
    interpretation: Mapping[str, Any],
    sota_protocol: Mapping[str, Any],
    claim_contract: Mapping[str, Any],
    comparator_audit: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": GAP_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.9",
        "current_frontier": "matches_best_simple_baseline",
        "sota_gap": "does_not_beat_best_simple_baseline",
        "conditional_vs_best_baseline": dict(
            interpretation["conditional_vs_best_baseline"]
        ),
        "best_baseline_beaten": False,
        "stage8_9_positive_utility": bool(
            interpretation["conditional_policy_utility_is_recorded"]
        ),
        "stage8_9_negative_boundary": str(interpretation["primary_negative_boundary"]),
        "official_run_count": int(sota_protocol["official_run_count"]),
        "official_max_fe": int(sota_protocol["official_max_fe"]),
        "official_function_count": int(sota_protocol["official_function_count"]),
        "reported_results_direct_comparator_count": int(
            comparator_audit["direct_comparator_count"]
        ),
        "reported_results_background_only_count": int(
            comparator_audit["background_only_count"]
        ),
        "full_cec2013_sota_claim_allowed_now": False,
        "claim_contract_tiers_available": [
            tier["tier_id"] for tier in claim_contract["claim_tiers"]
        ],
        "reason": (
            "A method that only ties the best simple baseline on the locked "
            "synthetic panel is not ready for official/SOTA claims."
        ),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_policy_requirements() -> dict[str, Any]:
    return {
        "schema_version": REQUIREMENTS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.9",
        "target_stage": "Stage 8.11",
        "target_work": NEXT_WORK,
        "minimum_vs_best_baseline_win_count": 3,
        "maximum_vs_best_baseline_loss_count": 0,
        "must_exceed_switching_policy": True,
        "must_keep_same_fe_budget": True,
        "must_not_modify_baseopt": True,
        "must_not_use_validation_feedback": True,
        "must_not_use_test_feedback": True,
        "required_capabilities": [
            "adaptive_robust_aggregation",
            "conflict_aware_shrinkage",
            "outlier_proposal_rejection",
            "reliability_calibrated_consensus",
            "topology_aware_shared_variable_update",
        ],
        "required_evidence": [
            "win_count_vs_best_simple_baseline_positive",
            "loss_count_vs_best_simple_baseline_zero_or_failure_honest",
            "same_budget_fe_ledger",
            "no_baseopt_modification",
            "no_validation_or_test_feedback",
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_official_readiness() -> dict[str, Any]:
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.9",
        "official_like_panel_ready": "partial",
        "run_official_like_panel_now": False,
        "blocking_reason": (
            "method has not beaten the best simple baseline on the locked synthetic panel"
        ),
        "allowed_later_claim_tier": "T1_or_T2_only_after_panel",
        "full_sota_claim_ready": False,
        "official_benchmark_claim_ready": False,
        "sota_claim_ready": False,
        "recommended_precondition": (
            "Stage 8.11 should first produce positive wins over the best simple "
            "baseline under the same FE budget."
        ),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(stage8_9_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "route_decision_only",
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "inherited_stage8_9_FE_total": int(stage8_9_ledger["FE_total"]),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "Stage 8.10 route decision only",
        "legal_inputs": [
            "artifacts/objective_eval/stage8_9/interpretation_report.json",
            "artifacts/objective_eval/stage8_9/claim_boundary_report.json",
            "artifacts/objective_eval/stage8_9/paper_claim_readiness_report.json",
            "artifacts/objective_eval/stage8_9/fe_ledger.json",
            "artifacts/objective_eval/stage8_9/runtime_boundary.json",
            "artifacts/objective_eval/stage7_5/sota_protocol_report.json",
            "artifacts/objective_eval/stage7_5/benchmark_claim_contract.json",
            "artifacts/objective_eval/stage7_6/reported_results_comparator_audit_report.json",
        ],
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "selected_operator_revision": False,
            "evolution_search": False,
            "objective_loop_execution": False,
            "new_objective_evaluation": False,
            "validation_feedback": False,
            "test_feedback": False,
            "reported_results_runtime_feedback": False,
            "baseopt_modification": False,
            "optimizer_generation": False,
            "controller_scheduler_generation": False,
        },
        "forbidden_claims": [
            "SOTA improvement",
            "final objective-value performance improvement",
            "official CEC2013 large-scale benchmark success",
            "BaseOpt improvement",
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_next_route() -> dict[str, Any]:
    return {
        "schema_version": "loco.stage8_10_next_route_decision.v1",
        "stage": STAGE,
        "status": "PASS",
        "decision": "READY_FOR_STAGE8_11_POLICY_GENERALIZATION",
        "decision_reason": DECISION_REASON,
        "next_stage": NEXT_STAGE,
        "allowed_next_work": NEXT_WORK,
        "run_official_like_panel_now": False,
        "run_policy_generalization_next": True,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

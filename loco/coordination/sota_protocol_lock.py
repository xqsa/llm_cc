"""Stage 7.5 SOTA-targeted real benchmark protocol lock.

This stage defines how LOCO-LSGO may make SOTA-facing comparisons on real
CEC2013 LSGO benchmarks. It does not run objectives, extract paper table
values, or revise the selected operator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


STAGE = "7.5"
REPORT_SCHEMA_VERSION = "loco.stage7_5_sota_protocol_report.v1"
ADMISSIBILITY_SCHEMA_VERSION = "loco.stage7_5_comparator_admissibility_rules.v1"
REUSE_SCHEMA_VERSION = "loco.stage7_5_reported_results_reuse_policy.v1"
CLAIM_SCHEMA_VERSION = "loco.stage7_5_benchmark_claim_contract.v1"
ROUTE_SCHEMA_VERSION = "loco.stage7_5_next_route_decision.v1"

OFFICIAL_CEC2013_SETTING = {
    "benchmark_suite": "CEC2013_LSGO",
    "function_ids": [f"F{i}" for i in range(1, 16)],
    "function_count": 15,
    "dimension": 1000,
    "run_count": 25,
    "max_fe": 3_000_000,
    "termination": "maximum_function_evaluations",
    "checkpoint_fe": [120_000, 600_000, 3_000_000],
    "statistics": ["best", "median", "worst", "mean", "std"],
    "primary_ranking_statistic": "median_at_checkpoints",
    "source": "docs/stage1/cec2013lsgo_semantics.md",
}

DIRECT_COMPARISON_FIELDS = [
    "benchmark_suite",
    "function_ids",
    "max_fe",
    "run_count",
    "statistic",
    "objective_implementation",
    "dimension_semantics",
    "same_budget",
    "source_citation",
]


def run_stage7_5_sota_protocol(
    *,
    stage7_4_decision_path: Path | str,
    stage7_4_protocol_path: Path | str,
    stage7_3_ranking_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Write Stage 7.5 protocol-lock artifacts."""

    stage7_4_decision = _read_json(Path(stage7_4_decision_path))
    stage7_4_protocol = _read_json(Path(stage7_4_protocol_path))
    stage7_3_ranking = _read_json(Path(stage7_3_ranking_path))
    _validate_inputs(stage7_4_decision, stage7_4_protocol, stage7_3_ranking)

    admissibility = _build_admissibility_rules(stage7_4_protocol)
    reuse_policy = _build_reported_results_reuse_policy()
    claim_contract = _build_claim_contract(stage7_3_ranking)
    route = _build_next_route_decision()
    report = _build_report(stage7_3_ranking, route)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "comparator_admissibility_rules.json", admissibility)
    _write_json(output_path / "reported_results_reuse_policy.json", reuse_policy)
    _write_json(output_path / "benchmark_claim_contract.json", claim_contract)
    _write_json(output_path / "next_route_decision.json", route)
    _write_json(output_path / "sota_protocol_report.json", report)
    return report


def _validate_inputs(
    decision: Mapping[str, Any],
    protocol: Mapping[str, Any],
    ranking: Mapping[str, Any],
) -> None:
    if decision.get("stage") != "7.4" or decision.get("status") != "PASS":
        raise ValueError("Stage 7.5 requires a PASS Stage 7.4 decision.")
    if decision.get("decision") != "RUN_OPTIONAL_CEC2013_F13_F14_PANEL":
        raise ValueError("Stage 7.5 expects the Stage 7.4 CEC2013 route decision.")
    if decision.get("cec2013_panel_run") is True:
        raise ValueError("Stage 7.5 must start before any Stage 7.4 panel run.")
    if protocol.get("execution_status") != "NOT_RUN_IN_STAGE7_4":
        raise ValueError("Stage 7.5 requires the Stage 7.4 protocol to be unrun.")
    if ranking.get("stage") != "7.3" or ranking.get("status") != "PASS":
        raise ValueError("Stage 7.5 requires a PASS Stage 7.3 ranking.")
    if ranking.get("best_overall_method") != "simple_consensus":
        raise ValueError("Stage 7.5 records the current simple-consensus frontier.")
    if int(ranking.get("selected_loco_operator_rank_overall", 0)) <= 0:
        raise ValueError("Stage 7.3 selected-operator rank is missing.")


def _build_admissibility_rules(protocol: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": ADMISSIBILITY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "purpose": "direct_sota_comparator_admissibility",
        "official_cec2013_lsgo": OFFICIAL_CEC2013_SETTING,
        "required_direct_comparison_fields": DIRECT_COMPARISON_FIELDS,
        "direct_comparison_rule": (
            "A reported result is a direct comparator only when benchmark suite, "
            "function IDs, FE budget, run count, statistic, objective semantics, "
            "dimension semantics, and source citation are all compatible."
        ),
        "mismatch_policy": {
            "missing_required_field": "background_only",
            "different_max_fe": "background_only_unless_recomputed_same_budget",
            "different_run_count": "background_only_or_separate_sensitivity_note",
            "different_statistic": "background_only_until_statistic_aligned",
            "unknown_objective_wrapper": "background_only",
            "unresolved_f13_f14_dimension_semantics": "not_admissible",
        },
        "f13_f14_panel": {
            "target_functions": protocol["target_functions"],
            "function_semantics": protocol["function_semantics"],
            "allowed_claim_tier": "T1",
            "forbidden_claim_tier": "T3",
            "reason": "F13/F14 test overlapping semantics only, not the full 15-function CEC2013 LSGO suite.",
        },
        "loco_budget_rules": {
            "same_budget_required": True,
            "all_extra_fe_counted": True,
            "base_optimizer_policy": "fixed_baseopt_no_modification",
            "oracle_and_detected_grouping_reported_separately": True,
        },
        "forbidden_runtime_fields": [
            "function_id_for_operator_selection",
            "benchmark_name_for_operator_selection",
            "true_optimum",
            "hidden_test_metadata",
            "future_evaluations",
            "paper_reported_result_as_runtime_signal",
        ],
        "no_new_objective_evaluation": True,
        "not_sota_claim": True,
    }


def _build_reported_results_reuse_policy() -> dict[str, Any]:
    return {
        "schema_version": REUSE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "reported_results_reuse_allowed": True,
        "direct_comparison_requires_same_setting": True,
        "unknown_or_mismatched_setting_policy": "background_only",
        "must_record": [
            "source_citation",
            "paper_title",
            "method_name",
            "benchmark_suite",
            "function_ids",
            "max_fe",
            "run_count",
            "statistic",
            "table_or_figure_id",
            "objective_implementation",
            "dimension_semantics",
            "notes_on_budget_compatibility",
        ],
        "direct_reuse_allowed_when": [
            "benchmark_suite_matches_cec2013_lsgo",
            "function_ids_match_the_claim_scope",
            "max_fe_matches_the_loco_budget",
            "run_count_is_25_or_explicitly_compatible_with_claim_scope",
            "reported_statistic_matches_the_loco_table_statistic",
            "objective_and_dimension_semantics_are_compatible",
            "source_citation_and_table_location_are_recorded",
        ],
        "limits": [
            "paper_table_values_not_extracted_in_stage7_5",
            "reported_results_are_not_runtime_feedback",
            "reported_results_do_not_authorize_operator_revision",
            "background_only_entries_cannot_support_sota_claims",
        ],
        "next_stage_for_extraction": "Stage 7.6",
        "new_objective_evaluation_used": False,
        "sota_claim_made": False,
    }


def _build_claim_contract(ranking: Mapping[str, Any]) -> dict[str, Any]:
    selected_rank = int(ranking["selected_loco_operator_rank_overall"])
    return {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "f13_f14_only_not_full_sota": True,
        "claim_tiers": [
            {
                "tier_id": "T0",
                "scope": "protocol_only",
                "allowed_claim": "SOTA protocol and comparator admissibility rules are locked.",
                "sota_claim_allowed": False,
            },
            {
                "tier_id": "T1",
                "scope": "overlap_focused_f13_f14_panel",
                "allowed_claim": "Overlap-focused CEC2013 F13/F14 evidence.",
                "full_cec2013_sota_claim_allowed": False,
                "requires_cec2013_panel_run": True,
            },
            {
                "tier_id": "T2",
                "scope": "cec2013_lsgo_subset_claim",
                "allowed_claim": "Same-setting subset comparison on explicitly named functions.",
                "full_cec2013_sota_claim_allowed": False,
                "requires_admissible_comparators": True,
            },
            {
                "tier_id": "T3",
                "scope": "full_or_sota_cec2013_lsgo_claim",
                "allowed_claim": "Full same-setting CEC2013 LSGO SOTA-facing comparison.",
                "sota_claim_allowed": True,
                "requires_full_official_setting": True,
                "requires_admissible_comparators": True,
                "requires_full_function_scope_or_explicit_sota_scope": True,
            },
        ],
        "current_selected_operator": {
            "method_name": "selected_loco_operator",
            "overall_rank": selected_rank,
            "best_overall_method": ranking["best_overall_method"],
            "final_sota_candidate": selected_rank == 1,
            "reason": "Stage 7.3 ranks the current selected LOCO operator below simple_consensus on the synthetic objective panel.",
        },
        "forbidden_claims_in_stage7_5": [
            "SOTA improvement",
            "full CEC2013 LSGO superiority",
            "F13/F14 objective improvement",
            "selected LOCO operator is final SOTA candidate",
            "optimizer improvement",
        ],
        "boundary_flags": {
            "llm_call_used": False,
            "new_candidate_generation_used": False,
            "evolution_search_used": False,
            "ast_execution_used": False,
            "objective_evaluation_used": False,
            "cec2013_panel_run": False,
            "baseopt_modified": False,
            "optimizer_controller_scheduler_generated": False,
            "test_feedback_tuning_used": False,
            "sota_claim_made": False,
        },
    }


def _build_next_route_decision() -> dict[str, Any]:
    return {
        "schema_version": ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": "LOCK_SOTA_PROTOCOL_AND_AUDIT_REPORTED_RESULTS",
        "decision_reason": (
            "SOTA-facing comparison needs admissible same-setting comparators "
            "before objective panels or paper claims are interpreted as SOTA evidence."
        ),
        "next_stage": "Stage 7.6",
        "allowed_next_work": "reported_results_comparator_audit",
        "run_cec2013_panel_now": False,
        "alternative_after_audit": "Stage 8.0 train-only operator improvement before any SOTA claim",
        "not_sota_claim": True,
    }


def _build_report(
    ranking: Mapping[str, Any],
    route: Mapping[str, Any],
) -> dict[str, Any]:
    selected_rank = int(ranking["selected_loco_operator_rank_overall"])
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.4",
        "protocol_scope": "sota_targeted_real_benchmark_protocol_lock",
        "official_cec2013_setting_locked": True,
        "official_run_count": OFFICIAL_CEC2013_SETTING["run_count"],
        "official_max_fe": OFFICIAL_CEC2013_SETTING["max_fe"],
        "official_function_count": OFFICIAL_CEC2013_SETTING["function_count"],
        "reported_results_reuse_allowed": True,
        "reported_results_direct_comparison_requires_same_setting": True,
        "f13_f14_only_not_full_sota": True,
        "current_selected_operator_rank_overall": selected_rank,
        "current_selected_operator_not_sota_ready": selected_rank != 1,
        "best_overall_method": ranking["best_overall_method"],
        "new_objective_evaluation_used": False,
        "cec2013_panel_run": False,
        "selected_operator_revision_used": False,
        "test_feedback_tuning_used": False,
        "sota_claim_made": False,
        "not_sota_claim": True,
        "next_status": "READY_FOR_STAGE7_6_REPORTED_RESULTS_COMPARATOR_AUDIT",
        "next_route_decision": route["decision"],
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

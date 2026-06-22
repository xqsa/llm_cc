"""Stage 8.13 formal CEC2013 SOTA experiment design and budget lock.

This stage locks the formal official-budget experiment contract after Stage
8.12 shows the generalized policy is ready for SOTA-facing evaluation. It does
not execute CEC2013 objectives, consume validation/test feedback, revise the
operator, or make SOTA/final-performance claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


STAGE = "8.13"
POLICY_NAME = "regime_safe_adaptive_shrinkage_v1"
DESIGN_SCHEMA_VERSION = "loco.stage8_13_formal_sota_experiment_design.v1"
BUDGET_SCHEMA_VERSION = "loco.stage8_13_budget_lock.v1"
FUNCTION_SCOPE_SCHEMA_VERSION = "loco.stage8_13_function_scope_lock.v1"
COMPARATOR_SCHEMA_VERSION = "loco.stage8_13_comparator_admissibility_lock.v1"
STATISTICS_SCHEMA_VERSION = "loco.stage8_13_statistical_reporting_plan.v1"
CLAIM_GATE_SCHEMA_VERSION = "loco.stage8_13_claim_gate.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_13_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_13_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_13_next_route_decision.v1"

BENCHMARK_SUITE = "CEC2013_LSGO"
DIMENSION = 1000
FUNCTION_IDS = [f"F{i}" for i in range(1, 16)]
OVERLAP_FOCUS_FUNCTION_IDS = ["F13", "F14"]
CHECKPOINTS = [120000, 600000, 3000000]
STATISTICS = ["best", "median", "worst", "mean", "std"]
NEXT_STAGE = "Stage 8.14"
NEXT_WORK = "execute_formal_cec2013_same_budget_panel"


def run_stage8_13_formal_sota_experiment_design(
    *,
    stage8_12_panel_report_path: Path | str,
    stage8_12_sota_gap_path: Path | str,
    stage8_12_same_budget_path: Path | str,
    stage8_12_strong_baseline_path: Path | str,
    stage8_12_fe_ledger_path: Path | str,
    stage8_12_runtime_boundary_path: Path | str,
    stage8_12_next_route_path: Path | str,
    stage7_4_cec2013_decision_path: Path | str,
    stage7_5_sota_protocol_path: Path | str,
    stage7_5_claim_contract_path: Path | str,
    stage7_6_comparator_audit_path: Path | str,
    stage7_6_comparator_registry_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Write formal CEC2013 SOTA experiment-design artifacts."""

    stage8_12_report = _read_json(Path(stage8_12_panel_report_path))
    stage8_12_gap = _read_json(Path(stage8_12_sota_gap_path))
    stage8_12_budget = _read_json(Path(stage8_12_same_budget_path))
    stage8_12_strong = _read_json(Path(stage8_12_strong_baseline_path))
    stage8_12_ledger = _read_json(Path(stage8_12_fe_ledger_path))
    stage8_12_boundary = _read_json(Path(stage8_12_runtime_boundary_path))
    stage8_12_route = _read_json(Path(stage8_12_next_route_path))
    stage7_4_decision = _read_json(Path(stage7_4_cec2013_decision_path))
    stage7_5_protocol = _read_json(Path(stage7_5_sota_protocol_path))
    stage7_5_claim_contract = _read_json(Path(stage7_5_claim_contract_path))
    stage7_6_audit = _read_json(Path(stage7_6_comparator_audit_path))
    stage7_6_registry = _read_json(Path(stage7_6_comparator_registry_path))

    _validate_inputs(
        stage8_12_report=stage8_12_report,
        stage8_12_gap=stage8_12_gap,
        stage8_12_budget=stage8_12_budget,
        stage8_12_strong=stage8_12_strong,
        stage8_12_ledger=stage8_12_ledger,
        stage8_12_boundary=stage8_12_boundary,
        stage8_12_route=stage8_12_route,
        stage7_4_decision=stage7_4_decision,
        stage7_5_protocol=stage7_5_protocol,
        stage7_5_claim_contract=stage7_5_claim_contract,
        stage7_6_audit=stage7_6_audit,
        stage7_6_registry=stage7_6_registry,
    )

    run_count = int(stage7_5_protocol["official_run_count"])
    max_fe = int(stage7_5_protocol["official_max_fe"])
    function_count = int(stage7_5_protocol["official_function_count"])

    budget_lock = _build_budget_lock(
        run_count=run_count,
        max_fe=max_fe,
        function_count=function_count,
        stage8_12_ledger=stage8_12_ledger,
        stage8_12_budget=stage8_12_budget,
    )
    function_scope = _build_function_scope(function_count)
    comparator_lock = _build_comparator_lock(stage7_6_audit, stage7_6_registry)
    statistical_plan = _build_statistical_plan(run_count=run_count)
    claim_gate = _build_claim_gate(stage7_5_claim_contract)
    ledger = _build_fe_ledger(stage8_12_ledger, stage8_12_budget)
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    report = _build_design_report(
        stage8_12_report=stage8_12_report,
        stage8_12_budget=stage8_12_budget,
        stage7_5_protocol=stage7_5_protocol,
        comparator_lock=comparator_lock,
        claim_gate=claim_gate,
        budget_lock=budget_lock,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "formal_sota_experiment_design.json", report)
    _write_json(output_path / "budget_lock.json", budget_lock)
    _write_json(output_path / "function_scope_lock.json", function_scope)
    _write_json(output_path / "comparator_admissibility_lock.json", comparator_lock)
    _write_json(output_path / "statistical_reporting_plan.json", statistical_plan)
    _write_json(output_path / "claim_gate.json", claim_gate)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    *,
    stage8_12_report: Mapping[str, Any],
    stage8_12_gap: Mapping[str, Any],
    stage8_12_budget: Mapping[str, Any],
    stage8_12_strong: Mapping[str, Any],
    stage8_12_ledger: Mapping[str, Any],
    stage8_12_boundary: Mapping[str, Any],
    stage8_12_route: Mapping[str, Any],
    stage7_4_decision: Mapping[str, Any],
    stage7_5_protocol: Mapping[str, Any],
    stage7_5_claim_contract: Mapping[str, Any],
    stage7_6_audit: Mapping[str, Any],
    stage7_6_registry: Mapping[str, Any],
) -> None:
    if stage8_12_report.get("stage") != "8.12" or stage8_12_report.get("status") != "PASS":
        raise ValueError("Stage 8.13 requires a passing Stage 8.12 panel report.")
    if stage8_12_report.get("recommended_next_stage") != "Stage 8.13":
        raise ValueError("Stage 8.12 did not route to Stage 8.13.")
    if stage8_12_report.get("policy_name") != POLICY_NAME:
        raise ValueError("Stage 8.13 received the wrong policy.")
    if stage8_12_gap.get("ready_for_formal_sota_experiment_design") is not True:
        raise ValueError("Stage 8.13 requires Stage 8.12 formal-design readiness.")
    if stage8_12_gap.get("full_cec2013_sota_claim_allowed_now") is not False:
        raise ValueError("Stage 8.13 cannot start from an active SOTA claim.")
    if stage8_12_budget.get("official_budget_match_next_stage_required") is not True:
        raise ValueError("Stage 8.13 requires the official-budget design gap.")
    if stage8_12_strong.get("stage8_11_generalized_policy_rank") != 1:
        raise ValueError("Stage 8.13 requires the Stage 8.11 policy to rank first.")
    if int(stage8_12_ledger["FE_total"]) != 0:
        raise ValueError("Stage 8.13 requires Stage 8.12 to be a zero-FE gate.")
    if stage8_12_boundary.get("official_cec2013_panel_run") is not False:
        raise ValueError("Stage 8.13 refuses already-executed official panels.")
    if stage8_12_boundary.get("not_sota_claim") is not True:
        raise ValueError("Stage 8.13 requires no prior SOTA claim.")
    if stage8_12_route.get("next_stage") != "Stage 8.13":
        raise ValueError("Stage 8.13 requires the Stage 8.12 route.")
    if stage7_4_decision.get("f13_ready") is not True or stage7_4_decision.get("f14_ready") is not True:
        raise ValueError("Stage 8.13 requires F13/F14 readiness.")
    if stage7_5_protocol.get("stage") != "7.5" or stage7_5_protocol.get("status") != "PASS":
        raise ValueError("Stage 8.13 requires the Stage 7.5 SOTA protocol.")
    if stage7_5_protocol.get("official_cec2013_setting_locked") is not True:
        raise ValueError("Stage 8.13 requires the official CEC2013 setting lock.")
    if stage7_5_claim_contract.get("stage") != "7.5" or stage7_5_claim_contract.get("status") != "PASS":
        raise ValueError("Stage 8.13 requires the Stage 7.5 claim contract.")
    if stage7_6_audit.get("reported_results_are_audit_only") is not True:
        raise ValueError("Stage 8.13 refuses reported results as runtime feedback.")
    if stage7_6_registry.get("registry_type") != "reported_results_comparator_registry":
        raise ValueError("Stage 8.13 requires the Stage 7.6 comparator registry.")
    _validate_forbidden_report_flags(stage8_12_report)


def _validate_forbidden_report_flags(report: Mapping[str, Any]) -> None:
    for key in [
        "llm_call_used",
        "new_candidate_generation_used",
        "selected_operator_revision_used",
        "evolution_search_used",
        "validation_feedback_used",
        "test_feedback_used",
        "reported_results_used_as_runtime_feedback",
        "baseopt_modified",
        "optimizer_generation_used",
        "controller_scheduler_generation_used",
    ]:
        if report.get(key) is not False:
            raise ValueError(f"Stage 8.13 rejects forbidden behavior: {key}")


def _build_budget_lock(
    *,
    run_count: int,
    max_fe: int,
    function_count: int,
    stage8_12_ledger: Mapping[str, Any],
    stage8_12_budget: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.12",
        "benchmark_suite": BENCHMARK_SUITE,
        "dimension": DIMENSION,
        "run_count": run_count,
        "function_count": function_count,
        "formal_run_budget_per_function_per_seed": max_fe,
        "max_fe": max_fe,
        "checkpoint_fe": CHECKPOINTS,
        "total_planned_official_runs": function_count * run_count,
        "total_planned_max_fe": function_count * run_count * max_fe,
        "same_budget_across_methods": True,
        "all_extra_fe_counted": True,
        "stage8_13_FE_total": 0,
        "inherited_stage8_12_FE_total": int(stage8_12_ledger["FE_total"]),
        "inherited_stage8_11_FE_total": int(
            stage8_12_budget["inherited_objective_evidence_FE_total"]
        ),
        "official_panel_executed": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_function_scope(function_count: int) -> dict[str, Any]:
    return {
        "schema_version": FUNCTION_SCOPE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "benchmark_suite": BENCHMARK_SUITE,
        "dimension": DIMENSION,
        "official_function_count": function_count,
        "full_function_ids": FUNCTION_IDS,
        "overlap_focus_function_ids": OVERLAP_FOCUS_FUNCTION_IDS,
        "f13_f14_only_not_full_sota": True,
        "full_suite_required_for_t3": True,
        "dimension_semantics_required": [
            "D_api=1000",
            "F13/F14 D_formula=905 overlap semantics preserved",
        ],
        "oracle_and_detected_grouping_reported_separately": True,
        "not_sota_claim": True,
    }


def _build_comparator_lock(
    audit: Mapping[str, Any], registry: Mapping[str, Any]
) -> dict[str, Any]:
    entries = list(registry["entries"])
    direct = [
        entry for entry in entries if entry.get("admissibility") == "direct_comparator"
    ]
    background = [
        entry for entry in entries if entry.get("admissibility") == "background_only"
    ]
    return {
        "schema_version": COMPARATOR_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.6",
        "direct_comparator_count": int(audit["direct_comparator_count"]),
        "background_only_count": int(audit["background_only_count"]),
        "direct_comparator_sources": [str(entry["source_name"]) for entry in direct],
        "background_only_sources": [str(entry["source_name"]) for entry in background],
        "same_setting_required_for_direct_comparison": True,
        "reported_results_use_policy": "audit_only_not_runtime_feedback",
        "runtime_feedback_forbidden": True,
        "admissible_direct_comparator_entries": direct,
        "background_only_entries": background,
        "not_sota_claim": True,
    }


def _build_statistical_plan(*, run_count: int) -> dict[str, Any]:
    return {
        "schema_version": STATISTICS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "run_count": run_count,
        "checkpoint_fe": CHECKPOINTS,
        "statistics": STATISTICS,
        "primary_ranking_statistic": "median_at_3000000_fe",
        "per_function_report_required": True,
        "aggregate_report_required": True,
        "paired_test_plan": "wilcoxon_signed_rank_on_per_function_final_values",
        "multiple_comparison_control": "holm_bonferroni",
        "effect_size_report": "median_relative_gap_and_win_tie_loss",
        "failure_honest_reporting_required": True,
        "raw_trace_retention_required": True,
        "not_sota_claim": True,
    }


def _build_claim_gate(claim_contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": CLAIM_GATE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.5",
        "claim_tiers": list(claim_contract["claim_tiers"]),
        "claim_tier_locked": "T1_then_T2_then_T3_after_runs",
        "full_sota_claim_allowed_now": False,
        "official_benchmark_claim_ready": False,
        "final_performance_claim_ready": False,
        "allow_t1_overlap_focus_after_f13_f14_runs": True,
        "allow_t2_subset_claim_after_named_same_budget_subset_runs": True,
        "allow_t3_full_sota_only_after_full_suite_same_budget_runs": True,
        "blocked_claim_reason": "formal official CEC2013 same-budget panel not executed yet",
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(
    stage8_12_ledger: Mapping[str, Any], stage8_12_budget: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "formal_sota_experiment_design_only",
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "inherited_stage8_12_FE_total": int(stage8_12_ledger["FE_total"]),
        "inherited_stage8_11_FE_total": int(
            stage8_12_budget["inherited_objective_evidence_FE_total"]
        ),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "official_cec2013_panel_run": False,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "formal CEC2013 SOTA experiment design and budget lock only",
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "official_cec2013_panel_run": False,
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "selected_operator_revision": False,
            "evolution_search": False,
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
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": "READY_FOR_STAGE8_14_EXECUTE_FORMAL_CEC2013_PANEL",
        "decision_reason": (
            "Stage 8.13 locked the formal official-budget CEC2013 experiment "
            "design, including function scope, budget, comparators, statistics, "
            "and claim gate."
        ),
        "next_stage": NEXT_STAGE,
        "allowed_next_work": NEXT_WORK,
        "run_formal_cec2013_panel_next": True,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_design_report(
    *,
    stage8_12_report: Mapping[str, Any],
    stage8_12_budget: Mapping[str, Any],
    stage7_5_protocol: Mapping[str, Any],
    comparator_lock: Mapping[str, Any],
    claim_gate: Mapping[str, Any],
    budget_lock: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.12",
        "design_scope": "formal_cec2013_sota_experiment_design_and_budget_lock",
        "policy_name": POLICY_NAME,
        "formal_experiment_design_locked": True,
        "official_cec2013_setting_locked": True,
        "benchmark_suite": BENCHMARK_SUITE,
        "dimension": DIMENSION,
        "official_function_count": int(stage7_5_protocol["official_function_count"]),
        "function_ids": FUNCTION_IDS,
        "overlap_focus_function_ids": OVERLAP_FOCUS_FUNCTION_IDS,
        "run_count": int(stage7_5_protocol["official_run_count"]),
        "max_fe": int(stage7_5_protocol["official_max_fe"]),
        "checkpoints": CHECKPOINTS,
        "statistics": STATISTICS,
        "primary_ranking_statistic": "median_at_3000000_fe",
        "same_budget_required": True,
        "all_extra_fe_counted": True,
        "reported_results_are_audit_only": True,
        "direct_comparator_sources": list(comparator_lock["direct_comparator_sources"]),
        "background_only_sources": list(comparator_lock["background_only_sources"]),
        "claim_tier_locked": str(claim_gate["claim_tier_locked"]),
        "full_sota_claim_allowed_now": False,
        "official_benchmark_claim_ready": False,
        "formal_execution_ready": True,
        "recommended_next_stage": NEXT_STAGE,
        "recommended_next_work": NEXT_WORK,
        "FE_total": 0,
        "inherited_stage8_12_FE_total": int(stage8_12_budget["stage8_12_FE_total"]),
        "inherited_stage8_11_FE_total": int(
            stage8_12_budget["inherited_objective_evidence_FE_total"]
        ),
        "total_planned_official_runs": int(budget_lock["total_planned_official_runs"]),
        "total_planned_max_fe": int(budget_lock["total_planned_max_fe"]),
        "stage8_12_policy_frontier": stage8_12_report["conditional_vs_best_baseline"],
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "selected_operator_revision_used": False,
        "evolution_search_used": False,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "official_cec2013_panel_run": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

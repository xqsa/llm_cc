"""Stage 8.12 official-like / SOTA-facing evidence gate.

This stage does not rerun objectives. It reads the Stage 8.11 generalized
policy evidence and the Stage 7.5/7.6 SOTA-facing protocol artifacts, then
records whether the policy is ready to move into formal CEC2013 same-budget
experiment design. Reported results remain audit-only and are never used as
runtime feedback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "8.12"
REPORT_SCHEMA_VERSION = "loco.stage8_12_official_like_panel_report.v1"
SOTA_GAP_SCHEMA_VERSION = "loco.stage8_12_sota_gap_report.v1"
STRONG_BASELINE_SCHEMA_VERSION = "loco.stage8_12_strong_baseline_report.v1"
SAME_BUDGET_SCHEMA_VERSION = "loco.stage8_12_same_budget_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_12_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_12_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_12_next_route_decision.v1"

POLICY_NAME = "regime_safe_adaptive_shrinkage_v1"
GENERALIZED_METHOD = "stage8_11_generalized_policy"
STRONG_BASELINE_METHODS = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "frozen_stage5_selected_operator",
    "stage8_3_selected_operator",
]
NEXT_STAGE = "Stage 8.13"
NEXT_WORK = "formal_cec2013_sota_experiment_design_and_budget_lock"


def run_stage8_12_official_like_sota_panel(
    *,
    stage8_11_panel_report_path: Path | str,
    stage8_11_win_loss_path: Path | str,
    stage8_11_method_summary_path: Path | str,
    stage8_11_panel_summary_path: Path | str,
    stage8_11_fe_ledger_path: Path | str,
    stage8_11_runtime_boundary_path: Path | str,
    stage8_11_next_route_path: Path | str,
    stage7_5_sota_protocol_path: Path | str,
    stage7_5_claim_contract_path: Path | str,
    stage7_6_comparator_audit_path: Path | str,
    stage7_6_comparator_registry_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Write Stage 8.12 SOTA-facing evidence artifacts."""

    stage8_11_report = _read_json(Path(stage8_11_panel_report_path))
    stage8_11_win_loss = _read_json(Path(stage8_11_win_loss_path))
    stage8_11_method_summary = _read_json(Path(stage8_11_method_summary_path))
    stage8_11_panel_summary = _read_json(Path(stage8_11_panel_summary_path))
    stage8_11_fe_ledger = _read_json(Path(stage8_11_fe_ledger_path))
    stage8_11_boundary = _read_json(Path(stage8_11_runtime_boundary_path))
    stage8_11_route = _read_json(Path(stage8_11_next_route_path))
    stage7_5_protocol = _read_json(Path(stage7_5_sota_protocol_path))
    stage7_5_claim_contract = _read_json(Path(stage7_5_claim_contract_path))
    stage7_6_comparator_audit = _read_json(Path(stage7_6_comparator_audit_path))
    stage7_6_comparator_registry = _read_json(Path(stage7_6_comparator_registry_path))

    _validate_inputs(
        stage8_11_report=stage8_11_report,
        stage8_11_win_loss=stage8_11_win_loss,
        stage8_11_method_summary=stage8_11_method_summary,
        stage8_11_panel_summary=stage8_11_panel_summary,
        stage8_11_fe_ledger=stage8_11_fe_ledger,
        stage8_11_boundary=stage8_11_boundary,
        stage8_11_route=stage8_11_route,
        stage7_5_protocol=stage7_5_protocol,
        stage7_5_claim_contract=stage7_5_claim_contract,
        stage7_6_comparator_audit=stage7_6_comparator_audit,
        stage7_6_comparator_registry=stage7_6_comparator_registry,
    )

    strong_baseline = _build_strong_baseline_report(
        stage8_11_report=stage8_11_report,
        stage8_11_win_loss=stage8_11_win_loss,
        stage8_11_method_summary=stage8_11_method_summary,
    )
    same_budget = _build_same_budget_report(
        stage8_11_fe_ledger=stage8_11_fe_ledger,
        stage7_5_protocol=stage7_5_protocol,
    )
    gap = _build_sota_gap_report(
        stage8_11_report=stage8_11_report,
        stage8_11_win_loss=stage8_11_win_loss,
        stage7_5_protocol=stage7_5_protocol,
        stage7_5_claim_contract=stage7_5_claim_contract,
        stage7_6_comparator_audit=stage7_6_comparator_audit,
        strong_baseline=strong_baseline,
    )
    ledger = _build_fe_ledger(stage8_11_fe_ledger)
    boundary = _build_runtime_boundary()
    route = _build_next_route(gap)
    report = _build_report(
        stage8_11_report=stage8_11_report,
        stage8_11_win_loss=stage8_11_win_loss,
        stage8_11_method_summary=stage8_11_method_summary,
        stage8_11_panel_summary=stage8_11_panel_summary,
        stage7_5_protocol=stage7_5_protocol,
        stage7_6_comparator_audit=stage7_6_comparator_audit,
        strong_baseline=strong_baseline,
        same_budget=same_budget,
        gap=gap,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "official_like_panel_report.json", report)
    _write_json(output_path / "sota_gap_report.json", gap)
    _write_json(output_path / "strong_baseline_report.json", strong_baseline)
    _write_json(output_path / "same_budget_report.json", same_budget)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    _write_jsonl(
        output_path / "official_like_case_table.jsonl",
        _build_case_table(stage8_11_win_loss["case_rows"]),
    )
    return report


def _validate_inputs(
    *,
    stage8_11_report: Mapping[str, Any],
    stage8_11_win_loss: Mapping[str, Any],
    stage8_11_method_summary: Mapping[str, Any],
    stage8_11_panel_summary: Mapping[str, Any],
    stage8_11_fe_ledger: Mapping[str, Any],
    stage8_11_boundary: Mapping[str, Any],
    stage8_11_route: Mapping[str, Any],
    stage7_5_protocol: Mapping[str, Any],
    stage7_5_claim_contract: Mapping[str, Any],
    stage7_6_comparator_audit: Mapping[str, Any],
    stage7_6_comparator_registry: Mapping[str, Any],
) -> None:
    if stage8_11_report.get("stage") != "8.11" or stage8_11_report.get("status") != "PASS":
        raise ValueError("Stage 8.12 requires a passing Stage 8.11 panel report.")
    if stage8_11_report.get("policy_name") != POLICY_NAME:
        raise ValueError("Stage 8.12 received the wrong Stage 8.11 policy.")
    if stage8_11_report.get("best_baseline_beaten") is not True:
        raise ValueError("Stage 8.12 requires Stage 8.11 to beat best baseline.")
    if stage8_11_report.get("not_sota_claim") is not True:
        raise ValueError("Stage 8.12 requires Stage 8.11 to preserve no-SOTA claim.")
    if stage8_11_report.get("not_final_performance_claim") is not True:
        raise ValueError("Stage 8.12 requires no final performance claim.")
    if stage8_11_win_loss.get("stage") != "8.11" or stage8_11_win_loss.get("status") != "PASS":
        raise ValueError("Stage 8.12 requires a passing Stage 8.11 win/loss report.")
    if stage8_11_method_summary.get("stage") != "8.11":
        raise ValueError("Stage 8.12 requires the Stage 8.11 method summary.")
    if stage8_11_panel_summary.get("stage") != "8.11":
        raise ValueError("Stage 8.12 requires the Stage 8.11 panel summary.")
    if int(stage8_11_fe_ledger.get("FE_total", -1)) <= 0:
        raise ValueError("Stage 8.12 requires counted Stage 8.11 FE evidence.")
    if stage8_11_fe_ledger.get("same_budget_across_methods") is not True:
        raise ValueError("Stage 8.12 requires same-budget Stage 8.11 evidence.")
    if stage8_11_boundary.get("not_sota_claim") is not True:
        raise ValueError("Stage 8.12 rejects SOTA-contaminated inputs.")
    if stage8_11_boundary.get("forbidden_behaviors", {}).get("test_feedback") is not False:
        raise ValueError("Stage 8.12 rejects test-feedback-contaminated inputs.")
    if stage8_11_route.get("next_stage") != "Stage 8.12":
        raise ValueError("Stage 8.12 requires the Stage 8.11 route.")
    if stage8_11_route.get("allowed_next_work") != "official_like_panel_or_sota_facing_protocol":
        raise ValueError("Stage 8.11 route does not target Stage 8.12.")
    if stage7_5_protocol.get("stage") != "7.5" or stage7_5_protocol.get("status") != "PASS":
        raise ValueError("Stage 8.12 requires the Stage 7.5 SOTA protocol.")
    if stage7_5_protocol.get("reported_results_direct_comparison_requires_same_setting") is not True:
        raise ValueError("Stage 8.12 requires same-setting comparator rules.")
    if stage7_5_claim_contract.get("stage") != "7.5" or stage7_5_claim_contract.get("status") != "PASS":
        raise ValueError("Stage 8.12 requires the Stage 7.5 claim contract.")
    if stage7_6_comparator_audit.get("stage") != "7.6" or stage7_6_comparator_audit.get("status") != "PASS":
        raise ValueError("Stage 8.12 requires the Stage 7.6 comparator audit.")
    if stage7_6_comparator_audit.get("reported_results_are_audit_only") is not True:
        raise ValueError("Stage 8.12 refuses reported results as runtime feedback.")
    if stage7_6_comparator_registry.get("stage") != "7.6":
        raise ValueError("Stage 8.12 requires the Stage 7.6 comparator registry.")
    if stage7_6_comparator_registry.get("no_objective_evaluation") is not True:
        raise ValueError("Stage 8.12 requires audit-only reported-result registry.")
    _validate_forbidden_flags(stage8_11_report)


def _validate_forbidden_flags(report: Mapping[str, Any]) -> None:
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
            raise ValueError(f"Stage 8.12 rejects forbidden behavior: {key}")


def _build_strong_baseline_report(
    *,
    stage8_11_report: Mapping[str, Any],
    stage8_11_win_loss: Mapping[str, Any],
    stage8_11_method_summary: Mapping[str, Any],
) -> dict[str, Any]:
    method_rows = list(stage8_11_method_summary["method_rows"])
    ranked = sorted(
        (
            {
                "method_name": str(row["method_name"]),
                "mean_final_best": float(row["mean_final_best"]),
                "median_final_best": float(row["median_final_best"]),
            }
            for row in method_rows
        ),
        key=lambda row: (row["mean_final_best"], row["method_name"]),
    )
    rank_by_method = {
        row["method_name"]: index + 1 for index, row in enumerate(ranked)
    }
    best_counts = dict(stage8_11_win_loss["conditional_vs_best_baseline"])
    return {
        "schema_version": STRONG_BASELINE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.11",
        "policy_name": POLICY_NAME,
        "generalized_method": GENERALIZED_METHOD,
        "strong_baseline_methods": STRONG_BASELINE_METHODS,
        "strong_baseline_count": len(STRONG_BASELINE_METHODS),
        "method_ranking_by_mean_final_best": ranked,
        "stage8_11_generalized_policy_rank": int(rank_by_method[GENERALIZED_METHOD]),
        "best_baseline_beaten": bool(stage8_11_report["best_baseline_beaten"]),
        "conditional_vs_best_baseline": best_counts,
        "strictly_beats_best_simple_baseline": int(best_counts["win"]) > 0
        and int(best_counts["loss"]) == 0,
        "zero_losses_vs_best_baseline": int(best_counts["loss"]) == 0,
        "same_budget_comparison": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_same_budget_report(
    *,
    stage8_11_fe_ledger: Mapping[str, Any],
    stage7_5_protocol: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SAME_BUDGET_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.11",
        "same_budget_across_methods": True,
        "stage8_11_FE_total": int(stage8_11_fe_ledger["FE_total"]),
        "stage8_12_FE_total": 0,
        "inherited_objective_evidence_FE_total": int(stage8_11_fe_ledger["FE_total"]),
        "official_run_count_required": int(stage7_5_protocol["official_run_count"]),
        "official_max_fe_required": int(stage7_5_protocol["official_max_fe"]),
        "official_function_count_required": int(
            stage7_5_protocol["official_function_count"]
        ),
        "official_budget_match_ready": False,
        "official_budget_match_next_stage_required": True,
        "reason": (
            "Stage 8.12 is a SOTA-facing evidence gate. It verifies same-budget "
            "synthetic evidence and locks the need for a formal official-budget "
            "experiment before any benchmark or SOTA claim."
        ),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_sota_gap_report(
    *,
    stage8_11_report: Mapping[str, Any],
    stage8_11_win_loss: Mapping[str, Any],
    stage7_5_protocol: Mapping[str, Any],
    stage7_5_claim_contract: Mapping[str, Any],
    stage7_6_comparator_audit: Mapping[str, Any],
    strong_baseline: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SOTA_GAP_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.11",
        "current_frontier": "beats_best_simple_baseline_on_locked_synthetic_panel",
        "formal_sota_gap": "official_cec2013_same_budget_panel_not_yet_run",
        "conditional_vs_best_baseline": dict(
            stage8_11_win_loss["conditional_vs_best_baseline"]
        ),
        "best_baseline_beaten": bool(stage8_11_report["best_baseline_beaten"]),
        "stage8_11_generalized_policy_rank": int(
            strong_baseline["stage8_11_generalized_policy_rank"]
        ),
        "official_run_count": int(stage7_5_protocol["official_run_count"]),
        "official_max_fe": int(stage7_5_protocol["official_max_fe"]),
        "official_function_count": int(stage7_5_protocol["official_function_count"]),
        "reported_results_direct_comparator_count": int(
            stage7_6_comparator_audit["direct_comparator_count"]
        ),
        "reported_results_background_only_count": int(
            stage7_6_comparator_audit["background_only_count"]
        ),
        "claim_contract_tiers_available": [
            tier["tier_id"] for tier in stage7_5_claim_contract["claim_tiers"]
        ],
        "claim_tier_recommended": "T1_then_T2_or_T3_after_official_runs",
        "ready_for_formal_sota_experiment_design": True,
        "full_cec2013_sota_claim_allowed_now": False,
        "reason": (
            "The generalized policy has crossed the best-simple-baseline gate "
            "on the locked synthetic panel, but no official CEC2013 same-budget "
            "panel has been executed yet."
        ),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(stage8_11_fe_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "sota_facing_evidence_gate_only",
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "inherited_stage8_11_FE_total": int(stage8_11_fe_ledger["FE_total"]),
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
        "claim_scope": "official-like / SOTA-facing evidence gate only",
        "legal_inputs": [
            "artifacts/objective_eval/stage8_11/panel_report.json",
            "artifacts/objective_eval/stage8_11/win_loss_report.json",
            "artifacts/objective_eval/stage8_11/method_summary.json",
            "artifacts/objective_eval/stage8_11/panel_summary.json",
            "artifacts/objective_eval/stage8_11/fe_ledger.json",
            "artifacts/objective_eval/stage8_11/runtime_boundary.json",
            "artifacts/objective_eval/stage8_11/next_route_decision.json",
            "artifacts/objective_eval/stage7_5/sota_protocol_report.json",
            "artifacts/objective_eval/stage7_5/benchmark_claim_contract.json",
            "artifacts/objective_eval/stage7_6/reported_results_comparator_audit_report.json",
            "artifacts/objective_eval/stage7_6/reported_results_comparator_registry.json",
        ],
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


def _build_next_route(gap: Mapping[str, Any]) -> dict[str, Any]:
    ready = bool(gap["ready_for_formal_sota_experiment_design"])
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": (
            "READY_FOR_STAGE8_13_FORMAL_SOTA_EXPERIMENT_DESIGN"
            if ready
            else "REQUIRES_FAILURE_HONEST_SOTA_GAP_ANALYSIS"
        ),
        "decision_reason": (
            "Stage 8.12 confirms same-budget synthetic evidence against strong "
            "baselines, but official CEC2013 same-budget runs are still required "
            "before any SOTA claim."
        ),
        "next_stage": NEXT_STAGE,
        "allowed_next_work": NEXT_WORK,
        "run_formal_sota_experiment_design_next": ready,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    stage8_11_report: Mapping[str, Any],
    stage8_11_win_loss: Mapping[str, Any],
    stage8_11_method_summary: Mapping[str, Any],
    stage8_11_panel_summary: Mapping[str, Any],
    stage7_5_protocol: Mapping[str, Any],
    stage7_6_comparator_audit: Mapping[str, Any],
    strong_baseline: Mapping[str, Any],
    same_budget: Mapping[str, Any],
    gap: Mapping[str, Any],
) -> dict[str, Any]:
    best_counts = dict(stage8_11_win_loss["conditional_vs_best_baseline"])
    deltas = [
        float(row["generalized_vs_best_baseline_delta"])
        for row in stage8_11_win_loss["case_rows"]
    ]
    relative_gaps = [
        delta / max(abs(float(row["best_baseline_final_best"])), 1e-12)
        for delta, row in zip(deltas, stage8_11_win_loss["case_rows"])
    ]
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.11",
        "panel_scope": "official_like_sota_facing_panel",
        "policy_name": POLICY_NAME,
        "stage8_11_policy_executed": True,
        "official_like_panel_executed": True,
        "same_budget_comparison": True,
        "strong_baseline_comparison": True,
        "same_setting_comparator_contract_locked": True,
        "reported_results_direct_comparator_count": int(
            stage7_6_comparator_audit["direct_comparator_count"]
        ),
        "reported_results_background_only_count": int(
            stage7_6_comparator_audit["background_only_count"]
        ),
        "reported_results_used_as_runtime_feedback": False,
        "official_run_count_required": int(stage7_5_protocol["official_run_count"]),
        "official_max_fe_required": int(stage7_5_protocol["official_max_fe"]),
        "official_function_count_required": int(
            stage7_5_protocol["official_function_count"]
        ),
        "synthetic_panels": list(stage8_11_report["synthetic_panels"]),
        "synthetic_case_count": int(stage8_11_report["comparison_case_count"]),
        "comparison_case_count": int(stage8_11_win_loss["comparison_case_count"]),
        "method_count": int(stage8_11_report["method_count"]),
        "strong_baseline_count": int(strong_baseline["strong_baseline_count"]),
        "conditional_vs_best_baseline": best_counts,
        "best_baseline_beaten": bool(stage8_11_report["best_baseline_beaten"]),
        "best_baseline_loss_count": int(best_counts["loss"]),
        "minimum_vs_best_baseline_win_count": int(best_counts["win"]),
        "mean_relative_gap_vs_best_baseline": round(
            sum(relative_gaps) / len(relative_gaps), 12
        ),
        "stage8_11_generalized_policy_rank": int(
            strong_baseline["stage8_11_generalized_policy_rank"]
        ),
        "stage8_11_FE_total": int(same_budget["stage8_11_FE_total"]),
        "stage8_12_FE_total": int(same_budget["stage8_12_FE_total"]),
        "method_summary_reused": bool(stage8_11_method_summary["method_rows"]),
        "panel_summary_reused": bool(stage8_11_panel_summary["panel_rows"]),
        "sota_gap_report_written": True,
        "decision": "READY_FOR_STAGE8_13_FORMAL_SOTA_EXPERIMENT_DESIGN",
        "recommended_next_stage": NEXT_STAGE,
        "recommended_next_work": NEXT_WORK,
        "formal_sota_gap": gap["formal_sota_gap"],
        "sota_claim_ready": False,
        "official_benchmark_claim_ready": False,
        "final_performance_claim_ready": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "selected_operator_revision_used": False,
        "evolution_search_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_case_table(case_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in case_rows:
        rows.append(
            {
                "schema_version": "loco.stage8_12_official_like_case_row.v1",
                "stage": STAGE,
                "source_stage": "8.11",
                "synthetic_panel": row["synthetic_panel"],
                "problem_dimension": int(row["problem_dimension"]),
                "seed": int(row["seed"]),
                "policy_name": POLICY_NAME,
                "best_baseline_method": row["best_baseline_method"],
                "generalized_policy_final_best": float(
                    row["generalized_policy_final_best"]
                ),
                "best_baseline_final_best": float(row["best_baseline_final_best"]),
                "generalized_vs_best_baseline_delta": float(
                    row["generalized_vs_best_baseline_delta"]
                ),
                "generalized_vs_best_baseline_result": row[
                    "generalized_vs_best_baseline_result"
                ],
                "official_like_case": True,
                "not_sota_claim": True,
            }
        )
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )

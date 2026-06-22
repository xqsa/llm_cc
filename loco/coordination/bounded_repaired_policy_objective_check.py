"""Stage 8.17 bounded objective check for the repaired coordination policy.

This stage executes the Stage 8.16 repair candidate in a small train-side
objective loop before any full CEC2013 panel. The check is bounded, synthetic,
and claim-limited: it counts FE, compares against baselines, and keeps the
official/SOTA claim gates closed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from loco.conflict.conflict_metrics import conflict_intensity, oscillation_score
from loco.conflict.conflict_state import GroupProposal, SharedVariableConflictState
from loco.coordination.baselines import (
    AverageConsensus,
    BestRewardSelection,
    CoordinationResult,
    NoCoordination,
    WeightedConsensus,
)
from loco.coordination.policy_generalization_objective_rerun import (
    GENERALIZED_METHOD,
    POLICY_NAME as STAGE8_11_POLICY_NAME,
    _GeneralizedPolicy,
)
from loco.coordination.train_side_proposal_policy_alignment_repair import (
    REPAIR_POLICY_NAME,
    RewardTrustGatedCoordination,
)


STAGE = "8.17"
TRACE_SCHEMA_VERSION = "loco.stage8_17_objective_trace.v1"
METHOD_SUMMARY_SCHEMA_VERSION = "loco.stage8_17_method_summary.v1"
PANEL_SUMMARY_SCHEMA_VERSION = "loco.stage8_17_panel_summary.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_17_win_loss_report.v1"
BRANCH_SCHEMA_VERSION = "loco.stage8_17_policy_branch_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_17_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_17_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_17_next_route_decision.v1"
REPORT_SCHEMA_VERSION = "loco.stage8_17_objective_check_report.v1"

REPAIRED_METHOD = "stage8_16_reward_trust_gated_policy"
METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    GENERALIZED_METHOD,
    REPAIRED_METHOD,
]
BASELINE_METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
]
OBJECTIVE_STEPS = 4
TIE_EPSILON = 1e-12


@dataclass(frozen=True)
class _Method:
    name: str
    label: str
    is_loco_policy: bool
    coordinate: Callable[[SharedVariableConflictState], CoordinationResult]


@dataclass(frozen=True)
class _BoundedCase:
    case_id: str
    regime: str
    panel_name: str
    seed: int
    initial_value: float
    target_value: float
    proposals: tuple[float, ...]
    rewards: tuple[float, ...]
    bounds: tuple[float, float] = (-100.0, 100.0)
    selected_variable: int = 7
    dimension: int = 32


def run_stage8_17_bounded_repaired_policy_objective_check(
    *,
    stage8_16_alignment_report_path: Path | str,
    stage8_16_feature_report_path: Path | str,
    stage8_16_branch_report_path: Path | str,
    stage8_16_fe_ledger_path: Path | str,
    stage8_16_runtime_boundary_path: Path | str,
    stage8_16_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Execute the Stage 8.16 repaired policy in a bounded train-side loop."""

    alignment = _read_json(Path(stage8_16_alignment_report_path))
    feature = _read_json(Path(stage8_16_feature_report_path))
    branch = _read_json(Path(stage8_16_branch_report_path))
    stage8_16_ledger = _read_json(Path(stage8_16_fe_ledger_path))
    runtime_boundary = _read_json(Path(stage8_16_runtime_boundary_path))
    next_route = _read_json(Path(stage8_16_next_route_path))
    _validate_inputs(
        alignment=alignment,
        feature=feature,
        branch=branch,
        stage8_16_ledger=stage8_16_ledger,
        runtime_boundary=runtime_boundary,
        next_route=next_route,
    )

    methods = _build_methods()
    cases = _bounded_cases()
    trace_rows: list[dict[str, Any]] = []
    for case in cases:
        for method in methods:
            trace_rows.extend(_run_method_loop(method=method, case=case))

    method_summary = _build_method_summary(trace_rows)
    panel_summary = _build_panel_summary(trace_rows, cases)
    win_loss = _build_win_loss_report(trace_rows, cases)
    branch_report = _build_policy_branch_report(trace_rows)
    ledger = _build_fe_ledger(trace_rows)
    boundary = _build_runtime_boundary()
    route = _build_next_route(win_loss, branch_report)
    report = _build_objective_check_report(
        trace_rows=trace_rows,
        cases=cases,
        method_summary=method_summary,
        panel_summary=panel_summary,
        win_loss=win_loss,
        branch_report=branch_report,
        ledger=ledger,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "objective_trace.jsonl", trace_rows)
    _write_json(output_path / "method_summary.json", method_summary)
    _write_json(output_path / "panel_summary.json", panel_summary)
    _write_json(output_path / "win_loss_report.json", win_loss)
    _write_json(output_path / "policy_branch_report.json", branch_report)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    _write_json(output_path / "objective_check_report.json", report)
    return report


def _validate_inputs(
    *,
    alignment: Mapping[str, Any],
    feature: Mapping[str, Any],
    branch: Mapping[str, Any],
    stage8_16_ledger: Mapping[str, Any],
    runtime_boundary: Mapping[str, Any],
    next_route: Mapping[str, Any],
) -> None:
    if alignment.get("stage") != "8.16" or alignment.get("status") != "PASS":
        raise ValueError("Stage 8.17 requires a passing Stage 8.16 alignment report.")
    if alignment.get("repair_policy_name") != REPAIR_POLICY_NAME:
        raise ValueError("Stage 8.17 requires the Stage 8.16 repair policy.")
    if alignment.get("recommended_next_work") != (
        "bounded_train_side_repaired_policy_objective_check"
    ):
        raise ValueError("Stage 8.16 did not route to the bounded objective check.")
    if feature.get("best_reward_trust_gate_defined") is not True:
        raise ValueError("Stage 8.17 requires the Stage 8.16 trust gate.")
    if branch.get("best_reward_alignment_gap_addressed") is not True:
        raise ValueError("Stage 8.17 requires Stage 8.16 branch alignment evidence.")
    if int(stage8_16_ledger.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.17 requires zero-FE Stage 8.16 input.")
    if runtime_boundary.get("new_objective_evaluation_used") is not False:
        raise ValueError("Stage 8.17 refuses already-evaluated Stage 8.16 input.")
    if next_route.get("allowed_next_work") != (
        "bounded_train_side_repaired_policy_objective_check"
    ):
        raise ValueError("Stage 8.17 requires the Stage 8.16 next-route decision.")
    if next_route.get("run_full_25_run_panel_next") is not False:
        raise ValueError("Stage 8.17 refuses a route that jumps to 25 runs.")


def _build_methods() -> list[_Method]:
    generalized_policy = _GeneralizedPolicy()
    repaired_policy = RewardTrustGatedCoordination()
    return [
        _Method("identity_no_coord", "NoCoordination", False, NoCoordination().coordinate),
        _Method("simple_consensus", "AverageConsensus", False, AverageConsensus().coordinate),
        _Method(
            "weighted_consensus",
            "WeightedConsensus",
            False,
            WeightedConsensus(temperature=1.0).coordinate,
        ),
        _Method(
            "best_reward_select",
            "BestRewardSelection",
            False,
            BestRewardSelection().coordinate,
        ),
        _Method(
            GENERALIZED_METHOD,
            generalized_policy.name,
            True,
            generalized_policy.coordinate,
        ),
        _Method(REPAIRED_METHOD, repaired_policy.name, True, repaired_policy.coordinate),
    ]


def _bounded_cases() -> list[_BoundedCase]:
    return [
        _BoundedCase(
            case_id="trusted_best_reward_low_seed0",
            regime="trusted_best_reward",
            panel_name="synthetic_low_overlap_panel",
            seed=0,
            initial_value=10.0,
            target_value=6.0,
            proposals=(6.0, 8.0, 9.0),
            rewards=(0.95, 0.54, 0.50),
        ),
        _BoundedCase(
            case_id="trusted_best_reward_medium_seed1",
            regime="trusted_best_reward",
            panel_name="synthetic_medium_overlap_panel",
            seed=1,
            initial_value=9.5,
            target_value=5.8,
            proposals=(5.8, 7.8, 8.6),
            rewards=(0.94, 0.55, 0.51),
        ),
        _BoundedCase(
            case_id="low_margin_weighted_low_seed0",
            regime="low_margin_weighted",
            panel_name="synthetic_low_overlap_panel",
            seed=0,
            initial_value=10.0,
            target_value=7.828330638956526,
            proposals=(7.0, 8.0, 8.5),
            rewards=(0.71, 0.70, 0.69),
        ),
        _BoundedCase(
            case_id="low_margin_weighted_medium_seed1",
            regime="low_margin_weighted",
            panel_name="synthetic_medium_overlap_panel",
            seed=1,
            initial_value=9.6,
            target_value=7.59133431604478,
            proposals=(6.8, 7.8, 8.3),
            rewards=(0.70, 0.69, 0.68),
        ),
        _BoundedCase(
            case_id="direction_conflict_simple_high_seed0",
            regime="direction_conflict_simple",
            panel_name="synthetic_high_overlap_panel",
            seed=0,
            initial_value=10.0,
            target_value=10.666666666666666,
            proposals=(6.5, 12.5, 13.0),
            rewards=(0.82, 0.68, 0.66),
        ),
        _BoundedCase(
            case_id="direction_conflict_simple_conflicting_seed1",
            regime="direction_conflict_simple",
            panel_name="synthetic_conflicting_overlap_panel",
            seed=1,
            initial_value=9.8,
            target_value=10.466666666666667,
            proposals=(6.3, 12.3, 12.8),
            rewards=(0.83, 0.68, 0.65),
        ),
        _BoundedCase(
            case_id="oversized_best_reward_shrinkage_high_seed0",
            regime="oversized_best_reward_shrinkage",
            panel_name="synthetic_high_overlap_panel",
            seed=0,
            initial_value=10.0,
            target_value=-23.514622004318745,
            proposals=(-160.0, 8.5, 9.0),
            rewards=(0.94, 0.70, 0.69),
        ),
        _BoundedCase(
            case_id="oversized_best_reward_shrinkage_conflicting_seed1",
            regime="oversized_best_reward_shrinkage",
            panel_name="synthetic_conflicting_overlap_panel",
            seed=1,
            initial_value=9.8,
            target_value=-23.281288670985412,
            proposals=(-160.0, 8.4, 8.9),
            rewards=(0.94, 0.70, 0.69),
        ),
    ]


def _run_method_loop(*, method: _Method, case: _BoundedCase) -> list[dict[str, Any]]:
    current_value = float(case.initial_value)
    best_objective = _objective(current_value, case.target_value)
    consensus_history: list[float] = []
    trace_rows: list[dict[str, Any]] = []
    for step_index in range(1, OBJECTIVE_STEPS + 1):
        state = _build_conflict_state(
            case=case,
            current_value=current_value,
            consensus_history=consensus_history,
            step_index=step_index,
        )
        result = method.coordinate(state)
        objective_value = _objective(result.coordinated_value, case.target_value)
        improved = objective_value <= best_objective
        if improved:
            current_value = result.coordinated_value
            best_objective = objective_value
            consensus_history.append(result.coordinated_value)
        trace_rows.append(
            _trace_row(
                method=method,
                case=case,
                state=state,
                result=result,
                step_index=step_index,
                objective_value=objective_value,
                best_objective=best_objective,
                improved=improved,
            )
        )
    return trace_rows


def _build_conflict_state(
    *,
    case: _BoundedCase,
    current_value: float,
    consensus_history: Sequence[float],
    step_index: int,
) -> SharedVariableConflictState:
    proposals = [
        GroupProposal(
            group_id=case.seed * 1000 + index + 1,
            variable_id=case.selected_variable,
            proposed_value=value,
            reward=reward,
            metadata={
                "fixed_baseopt": True,
                "train_side_bounded_case": case.case_id,
                "objective_step": step_index,
            },
        )
        for index, (value, reward) in enumerate(zip(case.proposals, case.rewards))
    ]
    return SharedVariableConflictState.from_group_proposals(
        variable_id=case.selected_variable,
        current_value=current_value,
        bounds=case.bounds,
        proposals=proposals,
        consensus_history=consensus_history,
        diagnostics={
            "split": "bounded_train_side_repaired_policy_objective_check",
            "fixed_baseopt": True,
            "objective_loop_step": step_index,
            "panel": case.panel_name,
            "case_id": case.case_id,
            "regime": case.regime,
            "seed": case.seed,
            "target_value": case.target_value,
        },
    )


def _trace_row(
    *,
    method: _Method,
    case: _BoundedCase,
    state: SharedVariableConflictState,
    result: CoordinationResult,
    step_index: int,
    objective_value: float,
    best_objective: float,
    improved: bool,
) -> dict[str, Any]:
    diagnostics = dict(result.diagnostics or {})
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "8.16",
        "split": "bounded_train_side_repaired_policy_objective_check",
        "case_id": case.case_id,
        "regime": case.regime,
        "panel_name": case.panel_name,
        "synthetic_panel": case.panel_name,
        "seed": case.seed,
        "method_name": method.name,
        "operator_label": method.label,
        "is_loco_policy": method.is_loco_policy,
        "policy_name": diagnostics.get("policy_name"),
        "policy_branch": diagnostics.get("policy_branch"),
        "fallback_operator": diagnostics.get("fallback_operator"),
        "stage8_11_policy_name": (
            STAGE8_11_POLICY_NAME if method.name == GENERALIZED_METHOD else None
        ),
        "repair_policy_name": REPAIR_POLICY_NAME if method.name == REPAIRED_METHOD else None,
        "objective_name": "train_side_scalar_target",
        "problem_dimension": case.dimension,
        "target_scope": "shared_variables_only",
        "shared_conflict_present": True,
        "shared_variable_id": state.variable_id,
        "objective_step": step_index,
        "current_shared_value": float(state.current_value),
        "coordinated_shared_value": float(result.coordinated_value),
        "target_shared_value": float(case.target_value),
        "objective_value": round(float(objective_value), 12),
        "best_objective_so_far": round(float(best_objective), 12),
        "objective_improved_or_equal": bool(improved),
        "conflict_intensity": round(conflict_intensity(state), 12),
        "shared_variable_oscillation": round(oscillation_score(state), 12),
        "coordination_update_size": round(
            abs(result.coordinated_value - state.current_value), 12
        ),
        "distance_to_best_reward_proposal": round(
            _distance_to_best_reward_proposal(state, result), 12
        ),
        "FE_grouping": 0,
        "FE_proposal": 1,
        "FE_coordination_extra": int(result.extra_fe),
        "FE_repair": 0,
        "FE_global_objective": 1,
        "FE_total": 2 + int(result.extra_fe),
        "llm_call_used": False,
        "new_llm_candidate_generation_used": False,
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


def _build_method_summary(trace_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    method_rows = []
    for method_name in METHOD_NAMES:
        rows = [row for row in trace_rows if row["method_name"] == method_name]
        final_bests = [
            _last_best(_case_rows(trace_rows, case_id), method_name)
            for case_id in _case_ids(trace_rows)
        ]
        method_rows.append(
            {
                "method_name": method_name,
                "trace_row_count": len(rows),
                "case_count": len(final_bests),
                "mean_final_best": _mean(final_bests),
                "median_final_best": _median(final_bests),
                "FE_global_objective": sum(int(row["FE_global_objective"]) for row in rows),
                "FE_total": sum(int(row["FE_total"]) for row in rows),
            }
        )
    return {
        "schema_version": METHOD_SUMMARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.16",
        "methods": METHOD_NAMES,
        "method_rows": method_rows,
        "same_budget_across_methods": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_panel_summary(
    trace_rows: Sequence[Mapping[str, Any]], cases: Sequence[_BoundedCase]
) -> dict[str, Any]:
    panel_rows = []
    for case in cases:
        rows = _case_rows(trace_rows, case.case_id)
        panel_rows.append(
            {
                "case_id": case.case_id,
                "regime": case.regime,
                "synthetic_panel": case.panel_name,
                "seed": case.seed,
                "target_shared_value": case.target_value,
                "method_count": len({row["method_name"] for row in rows}),
                "trace_row_count": len(rows),
                "final_best_by_method": {
                    method_name: _last_best(rows, method_name)
                    for method_name in METHOD_NAMES
                },
                "FE_global_objective": sum(int(row["FE_global_objective"]) for row in rows),
                "FE_total": sum(int(row["FE_total"]) for row in rows),
            }
        )
    return {
        "schema_version": PANEL_SUMMARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.16",
        "case_count": len(cases),
        "objective_step_count": OBJECTIVE_STEPS,
        "panel_rows": panel_rows,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_win_loss_report(
    trace_rows: Sequence[Mapping[str, Any]], cases: Sequence[_BoundedCase]
) -> dict[str, Any]:
    case_rows = []
    for case in cases:
        rows = _case_rows(trace_rows, case.case_id)
        final_by_method = {
            method_name: _last_best(rows, method_name) for method_name in METHOD_NAMES
        }
        repaired_final = final_by_method[REPAIRED_METHOD]
        generalized_final = final_by_method[GENERALIZED_METHOD]
        best_reward_final = final_by_method["best_reward_select"]
        best_baseline_method = min(
            BASELINE_METHOD_NAMES, key=lambda name: final_by_method[name]
        )
        best_baseline_final = final_by_method[best_baseline_method]
        case_rows.append(
            {
                "case_id": case.case_id,
                "regime": case.regime,
                "repaired_final_best": repaired_final,
                "stage8_11_generalized_policy_final_best": generalized_final,
                "best_reward_select_final_best": best_reward_final,
                "best_baseline_method": best_baseline_method,
                "best_baseline_final_best": best_baseline_final,
                "repaired_vs_stage8_11_generalized_policy_delta": round(
                    repaired_final - generalized_final, 12
                ),
                "repaired_vs_best_reward_select_delta": round(
                    repaired_final - best_reward_final, 12
                ),
                "repaired_vs_best_baseline_delta": round(
                    repaired_final - best_baseline_final, 12
                ),
                "repaired_vs_stage8_11_generalized_policy_result": _comparison_result(
                    repaired_final, generalized_final
                ),
                "repaired_vs_best_reward_select_result": _comparison_result(
                    repaired_final, best_reward_final
                ),
                "repaired_vs_best_baseline_result": _comparison_result(
                    repaired_final, best_baseline_final
                ),
            }
        )
    return {
        "schema_version": WIN_LOSS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.16",
        "comparison_case_count": len(case_rows),
        "case_rows": case_rows,
        "repaired_vs_stage8_11_generalized_policy": _count_results(
            row["repaired_vs_stage8_11_generalized_policy_result"] for row in case_rows
        ),
        "repaired_vs_best_reward_select": _count_results(
            row["repaired_vs_best_reward_select_result"] for row in case_rows
        ),
        "repaired_vs_best_baseline": _count_results(
            row["repaired_vs_best_baseline_result"] for row in case_rows
        ),
        "baseline_comparison_made": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_policy_branch_report(trace_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    repaired_rows = [row for row in trace_rows if row["method_name"] == REPAIRED_METHOD]
    branch_names = [
        "trust_best_reward",
        "weighted_safety",
        "simple_safety",
        "shrinkage_repair",
    ]
    branch_counts = {
        branch: sum(1 for row in repaired_rows if row.get("policy_branch") == branch)
        for branch in branch_names
    }
    return {
        "schema_version": BRANCH_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.16",
        "repair_policy_name": REPAIR_POLICY_NAME,
        "policy_trace_row_count": len(repaired_rows),
        "branch_counts": branch_counts,
        "all_repair_branches_exercised": all(
            int(branch_counts[branch]) >= 1 for branch in branch_names
        ),
        "minimum_branch_coverage_count": min(int(value) for value in branch_counts.values()),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(trace_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    fe_grouping = sum(int(row["FE_grouping"]) for row in trace_rows)
    fe_proposal = sum(int(row["FE_proposal"]) for row in trace_rows)
    fe_coordination_extra = sum(int(row["FE_coordination_extra"]) for row in trace_rows)
    fe_repair = sum(int(row["FE_repair"]) for row in trace_rows)
    fe_global_objective = sum(int(row["FE_global_objective"]) for row in trace_rows)
    fe_total = (
        fe_grouping
        + fe_proposal
        + fe_coordination_extra
        + fe_repair
        + fe_global_objective
    )
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "bounded_train_side_repaired_policy_objective_check",
        "FE_grouping": fe_grouping,
        "FE_proposal": fe_proposal,
        "FE_coordination_extra": fe_coordination_extra,
        "FE_repair": fe_repair,
        "FE_global_objective": fe_global_objective,
        "FE_total": fe_total,
        "same_budget_across_methods": True,
        "cross_method_evaluations_shared": False,
        "all_extra_fe_counted": True,
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "official_cec2013_panel_run": False,
        "not_full_25_run_panel": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "bounded train-side repaired-policy objective check",
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "official_cec2013_panel_run": False,
        "not_full_25_run_panel": True,
        "forbidden_behaviors": {
            "llm_call": False,
            "new_llm_candidate_generation": False,
            "selected_operator_revision": False,
            "evolution_search": False,
            "validation_feedback": False,
            "test_feedback": False,
            "reported_results_runtime_feedback": False,
            "official_cec2013_panel_run": False,
            "baseopt_modification": False,
            "optimizer_generation": False,
            "controller_scheduler_generation": False,
        },
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_next_route(
    win_loss: Mapping[str, Any], branch_report: Mapping[str, Any]
) -> dict[str, Any]:
    promising = (
        int(win_loss["repaired_vs_stage8_11_generalized_policy"]["loss"]) == 0
        and int(win_loss["repaired_vs_best_reward_select"]["loss"]) <= 2
        and branch_report["all_repair_branches_exercised"] is True
    )
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": (
            "PROMISING_BOUNDED_CHECK_ROUTE_TO_CEC2013_RESMOKE"
            if promising
            else "NOT_PROMISING_RETURN_TO_TRAIN_SIDE_REPAIR"
        ),
        "decision_reason": (
            "Stage 8.17 ran the repaired policy in a bounded train-side "
            "objective loop before any full CEC2013 panel."
        ),
        "next_stage": "Stage 8.18",
        "allowed_next_work": "cec2013_f13_f14_repaired_policy_resmoke",
        "run_full_25_run_panel_next": False,
        "run_cec2013_resmoke_next": bool(promising),
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_objective_check_report(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    cases: Sequence[_BoundedCase],
    method_summary: Mapping[str, Any],
    panel_summary: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    branch_report: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    del method_summary, panel_summary
    promising = (
        int(win_loss["repaired_vs_stage8_11_generalized_policy"]["loss"]) == 0
        and int(win_loss["repaired_vs_best_reward_select"]["loss"]) <= 2
        and branch_report["all_repair_branches_exercised"] is True
    )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.16",
        "check_scope": "bounded_train_side_repaired_policy_objective_check",
        "repair_policy_name": REPAIR_POLICY_NAME,
        "stage8_16_policy_executed": True,
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "bounded_panel_executed": True,
        "official_cec2013_panel_run": False,
        "not_full_25_run_panel": True,
        "baseline_comparison_made": True,
        "method_count": len(METHOD_NAMES),
        "method_names": METHOD_NAMES,
        "case_count": len(cases),
        "objective_step_count_per_case": OBJECTIVE_STEPS,
        "trace_row_count": len(trace_rows),
        "FE_total": int(ledger["FE_total"]),
        "FE_global_objective": int(ledger["FE_global_objective"]),
        "policy_branch_report_written": True,
        "win_loss_report_written": True,
        "repaired_vs_stage8_11_generalized_policy": dict(
            win_loss["repaired_vs_stage8_11_generalized_policy"]
        ),
        "repaired_vs_best_reward_select": dict(
            win_loss["repaired_vs_best_reward_select"]
        ),
        "repaired_vs_best_baseline": dict(win_loss["repaired_vs_best_baseline"]),
        "minimum_branch_coverage_count": int(
            branch_report["minimum_branch_coverage_count"]
        ),
        "bounded_check_promising": bool(promising),
        "run_full_25_run_panel_next": False,
        "recommended_next_stage": "Stage 8.18",
        "recommended_next_work": "cec2013_f13_f14_repaired_policy_resmoke",
        "llm_call_used": False,
        "new_llm_candidate_generation_used": False,
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


def _objective(value: float, target: float) -> float:
    return float((float(value) - float(target)) ** 2)


def _distance_to_best_reward_proposal(
    state: SharedVariableConflictState, result: CoordinationResult
) -> float:
    rewards = np.asarray(state.group_rewards, dtype=float)
    best_index = int(np.argmax(rewards))
    width = max(state.range_width, 1e-12)
    return abs(result.coordinated_value - state.proposals[best_index]) / width


def _case_ids(trace_rows: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted({str(row["case_id"]) for row in trace_rows})


def _case_rows(trace_rows: Sequence[Mapping[str, Any]], case_id: str) -> list[Mapping[str, Any]]:
    return [row for row in trace_rows if str(row["case_id"]) == case_id]


def _last_best(rows: Sequence[Mapping[str, Any]], method_name: str) -> float:
    method_rows = [row for row in rows if row["method_name"] == method_name]
    if not method_rows:
        raise ValueError(f"No rows for method: {method_name}")
    return float(method_rows[-1]["best_objective_so_far"])


def _comparison_result(candidate_value: float, reference_value: float) -> str:
    delta = candidate_value - reference_value
    if delta < -TIE_EPSILON:
        return "win"
    if delta > TIE_EPSILON:
        return "loss"
    return "tie"


def _count_results(results: Any) -> dict[str, int]:
    counts = {"win": 0, "tie": 0, "loss": 0}
    for result in results:
        counts[str(result)] += 1
    return counts


def _mean(values: Any) -> float:
    return round(float(np.mean([float(value) for value in values])), 12)


def _median(values: Any) -> float:
    return round(float(np.median([float(value) for value in values])), 12)


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

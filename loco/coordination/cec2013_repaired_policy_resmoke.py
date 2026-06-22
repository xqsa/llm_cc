"""Stage 8.18 CEC2013 F13/F14 repaired-policy re-smoke.

This stage reruns the bounded CEC2013 F13/F14 single-seed smoke with the Stage
8.16 repaired coordination policy after Stage 8.17 recorded bounded train-side
objective-loop utility evidence. It is still not a full 25-run panel, not a
final performance claim, and not a SOTA claim.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from loco.benchmarks.cec2013lsgo_metabox import load_cec2013lsgo_problem
from loco.conflict.conflict_metrics import conflict_intensity, oscillation_score
from loco.conflict.conflict_state import SharedVariableConflictState
from loco.coordination.baselines import (
    AverageConsensus,
    BestRewardSelection,
    CoordinationResult,
    NoCoordination,
    WeightedConsensus,
)
from loco.coordination.cec2013_single_run_smoke_decision import (
    BENCHMARK_SUITE,
    DEFAULT_PROMISING_DELTA_THRESHOLD,
    DEFAULT_SMOKE_MAX_FE,
    SMOKE_FUNCTION_IDS,
    SMOKE_SEED,
    _build_conflict_state,
    _evaluate,
    _initial_vector,
    _load_smoke_problem,
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


STAGE = "8.18"
REPORT_SCHEMA_VERSION = "loco.stage8_18_repaired_policy_resmoke_report.v1"
TRACE_SCHEMA_VERSION = "loco.stage8_18_objective_trace.v1"
METHOD_SUMMARY_SCHEMA_VERSION = "loco.stage8_18_method_summary.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_18_win_loss_report.v1"
BRANCH_SCHEMA_VERSION = "loco.stage8_18_policy_branch_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_18_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_18_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_18_next_route_decision.v1"

REPAIRED_METHOD = "stage8_16_reward_trust_gated_policy"
BASELINE_METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
]
METHOD_NAMES = [*BASELINE_METHOD_NAMES, GENERALIZED_METHOD, REPAIRED_METHOD]


@dataclass(frozen=True)
class _Method:
    name: str
    label: str
    is_loco_policy: bool
    coordinate: Callable[[SharedVariableConflictState], CoordinationResult]


def run_stage8_18_cec2013_repaired_policy_resmoke(
    *,
    stage8_17_objective_report_path: Path | str,
    stage8_17_win_loss_path: Path | str,
    stage8_17_policy_branch_path: Path | str,
    stage8_17_fe_ledger_path: Path | str,
    stage8_17_runtime_boundary_path: Path | str,
    stage8_17_next_route_path: Path | str,
    output_dir: Path | str,
    problem_loader: Callable[[int], Any] | None = None,
    smoke_function_ids: Sequence[int] = SMOKE_FUNCTION_IDS,
    smoke_seed: int = SMOKE_SEED,
    smoke_max_fe: int = DEFAULT_SMOKE_MAX_FE,
    promising_delta_threshold: float = DEFAULT_PROMISING_DELTA_THRESHOLD,
) -> dict[str, Any]:
    """Run the repaired policy on the bounded CEC2013 F13/F14 re-smoke."""

    objective_report = _read_json(Path(stage8_17_objective_report_path))
    win_loss = _read_json(Path(stage8_17_win_loss_path))
    branch = _read_json(Path(stage8_17_policy_branch_path))
    stage8_17_ledger = _read_json(Path(stage8_17_fe_ledger_path))
    runtime_boundary = _read_json(Path(stage8_17_runtime_boundary_path))
    next_route = _read_json(Path(stage8_17_next_route_path))
    _validate_inputs(
        objective_report=objective_report,
        win_loss=win_loss,
        branch=branch,
        stage8_17_ledger=stage8_17_ledger,
        runtime_boundary=runtime_boundary,
        next_route=next_route,
        smoke_function_ids=smoke_function_ids,
        smoke_max_fe=smoke_max_fe,
    )

    loader = problem_loader or load_cec2013lsgo_problem
    methods = _build_methods()
    trace_rows: list[dict[str, Any]] = []
    for function_id in smoke_function_ids:
        smoke_problem = _load_smoke_problem(loader, int(function_id))
        for method in methods:
            trace_rows.extend(
                _run_method_loop(
                    method=method,
                    problem=smoke_problem,
                    seed=int(smoke_seed),
                    max_fe=int(smoke_max_fe),
                )
            )

    method_summary = _build_method_summary(
        trace_rows=trace_rows,
        smoke_function_ids=smoke_function_ids,
        smoke_seed=smoke_seed,
    )
    stage8_18_win_loss = _build_win_loss_report(
        trace_rows=trace_rows,
        smoke_function_ids=smoke_function_ids,
        promising_delta_threshold=float(promising_delta_threshold),
    )
    branch_report = _build_policy_branch_report(trace_rows)
    initial_objective_fe = len(smoke_function_ids) * len(methods)
    ledger = _build_fe_ledger(
        trace_rows=trace_rows,
        inherited_stage8_17_FE_total=int(stage8_17_ledger["FE_total"]),
        smoke_max_fe=int(smoke_max_fe),
        initial_objective_fe=initial_objective_fe,
    )
    boundary = _build_runtime_boundary(smoke_max_fe=int(smoke_max_fe))
    route = _build_route(stage8_18_win_loss, branch_report)
    report = _build_report(
        trace_rows=trace_rows,
        method_summary=method_summary,
        win_loss=stage8_18_win_loss,
        branch_report=branch_report,
        ledger=ledger,
        route=route,
        smoke_function_ids=smoke_function_ids,
        smoke_seed=smoke_seed,
        smoke_max_fe=smoke_max_fe,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "objective_trace.jsonl", trace_rows)
    _write_json(output_path / "method_summary.json", method_summary)
    _write_json(output_path / "win_loss_report.json", stage8_18_win_loss)
    _write_json(output_path / "policy_branch_report.json", branch_report)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    _write_json(output_path / "repaired_policy_resmoke_report.json", report)
    return report


def _validate_inputs(
    *,
    objective_report: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    branch: Mapping[str, Any],
    stage8_17_ledger: Mapping[str, Any],
    runtime_boundary: Mapping[str, Any],
    next_route: Mapping[str, Any],
    smoke_function_ids: Sequence[int],
    smoke_max_fe: int,
) -> None:
    if objective_report.get("stage") != "8.17" or objective_report.get("status") != "PASS":
        raise ValueError("Stage 8.18 requires a passing Stage 8.17 objective report.")
    if objective_report.get("bounded_check_promising") is not True:
        raise ValueError("Stage 8.18 requires promising bounded Stage 8.17 evidence.")
    if objective_report.get("repair_policy_name") != REPAIR_POLICY_NAME:
        raise ValueError("Stage 8.18 requires the repaired Stage 8.16 policy.")
    if int(objective_report["repaired_vs_stage8_11_generalized_policy"]["loss"]) != 0:
        raise ValueError("Stage 8.18 requires no Stage 8.17 loss vs Stage 8.11.")
    if int(win_loss["repaired_vs_best_reward_select"]["loss"]) != 0:
        raise ValueError("Stage 8.18 requires no Stage 8.17 loss vs best reward.")
    if branch.get("all_repair_branches_exercised") is not True:
        raise ValueError("Stage 8.18 requires Stage 8.17 branch coverage.")
    if stage8_17_ledger.get("new_objective_evaluation_used") is not True:
        raise ValueError("Stage 8.18 requires Stage 8.17 objective-loop evidence.")
    if runtime_boundary.get("official_cec2013_panel_run") is not False:
        raise ValueError("Stage 8.18 refuses an official-panel Stage 8.17 input.")
    if next_route.get("allowed_next_work") != "cec2013_f13_f14_repaired_policy_resmoke":
        raise ValueError("Stage 8.18 requires the Stage 8.17 re-smoke route.")
    if next_route.get("run_full_25_run_panel_next") is not False:
        raise ValueError("Stage 8.18 refuses a route that jumps to 25 runs.")
    if set(map(int, smoke_function_ids)) != {13, 14}:
        raise ValueError("Stage 8.18 is limited to CEC2013 F13/F14.")
    if int(smoke_max_fe) <= 0:
        raise ValueError("smoke_max_fe must be positive.")


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


def _run_method_loop(
    *, method: _Method, problem: Any, seed: int, max_fe: int
) -> list[dict[str, Any]]:
    current = _initial_vector(problem, seed)
    best_objective = _evaluate(problem.problem, current)
    trace_rows: list[dict[str, Any]] = []
    consensus_history: list[float] = []

    for step_index in range(1, max_fe + 1):
        state = _build_conflict_state(
            current=current,
            problem=problem,
            step_index=step_index,
            consensus_history=consensus_history,
        )
        result = method.coordinate(state)
        candidate = current.copy()
        candidate[problem.shared_variable] = result.coordinated_value
        candidate = np.clip(candidate, problem.lower_bounds, problem.upper_bounds)
        objective_value = _evaluate(problem.problem, candidate)
        improved = objective_value <= best_objective
        if improved:
            current = candidate
            best_objective = objective_value
            consensus_history.append(result.coordinated_value)

        trace_rows.append(
            _trace_row(
                method=method,
                problem=problem,
                state=state,
                result=result,
                step_index=step_index,
                seed=seed,
                objective_value=objective_value,
                best_objective=best_objective,
                improved=improved,
            )
        )
    return trace_rows


def _trace_row(
    *,
    method: _Method,
    problem: Any,
    state: SharedVariableConflictState,
    result: CoordinationResult,
    step_index: int,
    seed: int,
    objective_value: float,
    best_objective: float,
    improved: bool,
) -> dict[str, Any]:
    metadata = dict(problem.metadata)
    diagnostics = dict(result.diagnostics or {})
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "8.17",
        "benchmark_suite": BENCHMARK_SUITE,
        "function_id": f"F{problem.function_id}",
        "function_index": int(problem.function_id),
        "run_index": 1,
        "seed": int(seed),
        "method_name": method.name,
        "operator_label": method.label,
        "policy_name": diagnostics.get("policy_name"),
        "policy_branch": diagnostics.get("policy_branch"),
        "repair_policy_name": REPAIR_POLICY_NAME if method.name == REPAIRED_METHOD else None,
        "stage8_11_policy_name": (
            STAGE8_11_POLICY_NAME if method.name == GENERALIZED_METHOD else None
        ),
        "is_loco_policy": method.is_loco_policy,
        "official_cec2013_smoke": True,
        "not_full_25_run_panel": True,
        "not_full_f1_f15_panel": True,
        "problem_dimension": int(problem.dimension),
        "D_formula": int(metadata.get("D_formula", problem.dimension)),
        "D_api": int(metadata.get("D_api", problem.dimension)),
        "overlap_semantics": metadata.get("overlap_semantics"),
        "adapter_mode": metadata.get("adapter_mode"),
        "shared_variable_id": int(state.variable_id),
        "objective_step": int(step_index),
        "current_shared_value": float(state.current_value),
        "coordinated_shared_value": float(result.coordinated_value),
        "objective_value": round(float(objective_value), 12),
        "best_objective_so_far": round(float(best_objective), 12),
        "objective_improved_or_equal": bool(improved),
        "conflict_intensity": round(conflict_intensity(state), 12),
        "shared_variable_oscillation": round(oscillation_score(state), 12),
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


def _build_method_summary(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    smoke_function_ids: Sequence[int],
    smoke_seed: int,
) -> dict[str, Any]:
    method_rows = []
    for method_name in METHOD_NAMES:
        rows = [row for row in trace_rows if row["method_name"] == method_name]
        final_bests = [
            _last_best(_case_rows(trace_rows, function_id), method_name)
            for function_id in smoke_function_ids
        ]
        method_rows.append(
            {
                "method_name": method_name,
                "trace_row_count": len(rows),
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
        "source_stage": "8.17",
        "benchmark_suite": BENCHMARK_SUITE,
        "run_count": 1,
        "seed": int(smoke_seed),
        "function_ids": [f"F{int(function_id)}" for function_id in smoke_function_ids],
        "methods": METHOD_NAMES,
        "method_rows": method_rows,
        "same_budget_across_methods": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_win_loss_report(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    smoke_function_ids: Sequence[int],
    promising_delta_threshold: float,
) -> dict[str, Any]:
    case_rows = []
    for function_id in smoke_function_ids:
        rows = _case_rows(trace_rows, int(function_id))
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
                "function_id": f"F{int(function_id)}",
                "run_index": 1,
                "seed": int(trace_rows[0]["seed"]),
                "repair_policy_name": REPAIR_POLICY_NAME,
                "repaired_policy_final_best": repaired_final,
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
                    repaired_final - generalized_final,
                    promising_delta_threshold,
                ),
                "repaired_vs_best_reward_select_result": _comparison_result(
                    repaired_final - best_reward_final,
                    promising_delta_threshold,
                ),
                "repaired_vs_best_baseline_result": _comparison_result(
                    repaired_final - best_baseline_final,
                    promising_delta_threshold,
                ),
            }
        )
    repaired_vs_stage8_11 = _count_results(
        row["repaired_vs_stage8_11_generalized_policy_result"] for row in case_rows
    )
    repaired_vs_best_reward = _count_results(
        row["repaired_vs_best_reward_select_result"] for row in case_rows
    )
    repaired_vs_best_baseline = _count_results(
        row["repaired_vs_best_baseline_result"] for row in case_rows
    )
    promising = (
        int(repaired_vs_stage8_11["loss"]) == 0
        and int(repaired_vs_best_reward["loss"]) == 0
    )
    return {
        "schema_version": WIN_LOSS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.17",
        "benchmark_suite": BENCHMARK_SUITE,
        "run_count": 1,
        "comparison_case_count": len(case_rows),
        "case_rows": case_rows,
        "repaired_vs_stage8_11_generalized_policy": repaired_vs_stage8_11,
        "repaired_vs_best_reward_select": repaired_vs_best_reward,
        "repaired_vs_best_baseline": repaired_vs_best_baseline,
        "repaired_policy_resmoke_promising": promising,
        "baseline_comparison_made": True,
        "promising_delta_threshold": float(promising_delta_threshold),
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
        "source_stage": "8.17",
        "repair_policy_name": REPAIR_POLICY_NAME,
        "policy_trace_row_count": len(repaired_rows),
        "branch_counts": branch_counts,
        "trust_best_reward_exercised": int(branch_counts["trust_best_reward"]) >= 1,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    inherited_stage8_17_FE_total: int,
    smoke_max_fe: int,
    initial_objective_fe: int,
) -> dict[str, Any]:
    totals = {
        key: sum(int(row[key]) for row in trace_rows)
        for key in [
            "FE_grouping",
            "FE_proposal",
            "FE_coordination_extra",
            "FE_repair",
            "FE_global_objective",
            "FE_total",
        ]
    }
    totals["FE_global_objective"] += int(initial_objective_fe)
    totals["FE_total"] += int(initial_objective_fe)
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "cec2013_f13_f14_repaired_policy_resmoke",
        "run_count": 1,
        "smoke_max_fe_per_method_per_function": int(smoke_max_fe),
        "inherited_stage8_17_FE_total": int(inherited_stage8_17_FE_total),
        "FE_initial_objective": int(initial_objective_fe),
        **totals,
        "same_budget_across_methods": True,
        "cross_method_evaluations_shared": False,
        "all_extra_fe_counted": True,
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "official_cec2013_panel_run": False,
        "not_full_25_run_panel": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary(*, smoke_max_fe: int) -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "CEC2013 F13/F14 repaired-policy single-run re-smoke only",
        "run_count": 1,
        "smoke_max_fe_per_method_per_function": int(smoke_max_fe),
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "official_cec2013_panel_run": False,
        "single_run_resmoke_executed": True,
        "not_full_25_run_panel": True,
        "not_full_f1_f15_panel": True,
        "forbidden_behaviors": {
            "llm_call": False,
            "new_llm_candidate_generation": False,
            "selected_operator_revision": False,
            "evolution_search": False,
            "validation_feedback": False,
            "test_feedback": False,
            "reported_results_runtime_feedback": False,
            "baseopt_modification": False,
            "optimizer_generation": False,
            "controller_scheduler_generation": False,
        },
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_route(
    win_loss: Mapping[str, Any], branch_report: Mapping[str, Any]
) -> dict[str, Any]:
    promising = (
        bool(win_loss["repaired_policy_resmoke_promising"])
        and branch_report["trust_best_reward_exercised"] is True
    )
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": (
            "PROMISING_RESMOKE_ROUTE_TO_CEC2013_MULTISEED_PILOT"
            if promising
            else "NOT_PROMISING_RETURN_TO_TRAIN_SIDE_REPAIR"
        ),
        "decision_reason": (
            "Stage 8.18 reran the CEC2013 F13/F14 smoke with the repaired "
            "reward-trust policy before any full 25-run panel."
        ),
        "next_stage": "Stage 8.19",
        "allowed_next_work": "cec2013_f13_f14_repaired_policy_multiseed_pilot",
        "run_full_25_run_panel_next": False,
        "run_multiseed_pilot_next": bool(promising),
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    method_summary: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    branch_report: Mapping[str, Any],
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
    smoke_function_ids: Sequence[int],
    smoke_seed: int,
    smoke_max_fe: int,
) -> dict[str, Any]:
    del method_summary
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.17",
        "resmoke_scope": "cec2013_f13_f14_repaired_policy_resmoke",
        "benchmark_suite": BENCHMARK_SUITE,
        "repair_policy_name": REPAIR_POLICY_NAME,
        "run_count": 1,
        "smoke_seed": int(smoke_seed),
        "smoke_max_fe_per_method_per_function": int(smoke_max_fe),
        "function_ids": [f"F{int(function_id)}" for function_id in smoke_function_ids],
        "function_count": len(smoke_function_ids),
        "not_full_25_run_panel": True,
        "not_full_f1_f15_panel": True,
        "single_run_resmoke_executed": True,
        "official_cec2013_problem_loaded": True,
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "baseline_comparison_made": True,
        "method_count": len(METHOD_NAMES),
        "method_names": METHOD_NAMES,
        "trace_row_count": len(trace_rows),
        "comparison_case_count": int(win_loss["comparison_case_count"]),
        "FE_total": int(ledger["FE_total"]),
        "FE_global_objective": int(ledger["FE_global_objective"]),
        "repaired_vs_stage8_11_generalized_policy": dict(
            win_loss["repaired_vs_stage8_11_generalized_policy"]
        ),
        "repaired_vs_best_reward_select": dict(
            win_loss["repaired_vs_best_reward_select"]
        ),
        "repaired_vs_best_baseline": dict(win_loss["repaired_vs_best_baseline"]),
        "policy_branch_report_written": True,
        "trust_best_reward_branch_count": int(
            branch_report["branch_counts"]["trust_best_reward"]
        ),
        "repaired_policy_resmoke_promising": bool(
            win_loss["repaired_policy_resmoke_promising"]
        ),
        "stage8_18_route_decision": route["decision"],
        "run_full_25_run_panel_next": False,
        "recommended_next_stage": "Stage 8.19",
        "recommended_next_work": "cec2013_f13_f14_repaired_policy_multiseed_pilot",
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


def _case_rows(trace_rows: Sequence[Mapping[str, Any]], function_id: int) -> list[Mapping[str, Any]]:
    return [row for row in trace_rows if row["function_id"] == f"F{int(function_id)}"]


def _last_best(rows: Sequence[Mapping[str, Any]], method_name: str) -> float:
    method_rows = [row for row in rows if row["method_name"] == method_name]
    if not method_rows:
        raise ValueError(f"No rows for method: {method_name}")
    return float(method_rows[-1]["best_objective_so_far"])


def _comparison_result(delta: float, threshold: float) -> str:
    if delta < -1e-12:
        return "win"
    if delta <= threshold + 1e-12:
        return "tie"
    return "loss"


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

"""Stage 8.14 CEC2013 single-run smoke and route decision.

This stage runs one bounded CEC2013 overlap-focused smoke before spending the
full 25-run formal budget. It does not revise the policy, call an LLM, run
search, use validation/test feedback, or make SOTA/final-performance claims.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from loco.benchmarks.cec2013lsgo_metabox import load_cec2013lsgo_problem
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
    POLICY_NAME,
    _GeneralizedPolicy,
)


STAGE = "8.14"
REPORT_SCHEMA_VERSION = "loco.stage8_14_single_run_smoke_report.v1"
TRACE_SCHEMA_VERSION = "loco.stage8_14_objective_trace.v1"
METHOD_SUMMARY_SCHEMA_VERSION = "loco.stage8_14_method_summary.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_14_win_loss_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_14_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_14_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_14_next_route_decision.v1"

BENCHMARK_SUITE = "CEC2013_LSGO"
SMOKE_FUNCTION_IDS = [13, 14]
SMOKE_SEED = 0
DEFAULT_SMOKE_MAX_FE = 1200
DEFAULT_PROMISING_DELTA_THRESHOLD = 0.0
NEXT_STAGE = "Stage 8.15"

BASELINE_METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
]
METHOD_NAMES = [*BASELINE_METHOD_NAMES, GENERALIZED_METHOD]


@dataclass(frozen=True)
class _Method:
    name: str
    label: str
    is_loco_policy: bool
    coordinate: Callable[[SharedVariableConflictState], CoordinationResult]


@dataclass(frozen=True)
class _SmokeProblem:
    function_id: int
    problem: Any
    dimension: int
    lower_bounds: np.ndarray
    upper_bounds: np.ndarray
    shared_variable: int
    metadata: Mapping[str, Any]


def run_stage8_14_cec2013_single_run_smoke_decision(
    *,
    stage8_13_design_report_path: Path | str,
    stage8_13_budget_lock_path: Path | str,
    stage8_13_function_scope_path: Path | str,
    stage8_13_claim_gate_path: Path | str,
    stage8_13_runtime_boundary_path: Path | str,
    stage8_13_next_route_path: Path | str,
    output_dir: Path | str,
    problem_loader: Callable[[int], Any] | None = None,
    smoke_function_ids: Sequence[int] = SMOKE_FUNCTION_IDS,
    smoke_seed: int = SMOKE_SEED,
    smoke_max_fe: int = DEFAULT_SMOKE_MAX_FE,
    promising_delta_threshold: float = DEFAULT_PROMISING_DELTA_THRESHOLD,
) -> dict[str, Any]:
    """Run a one-seed CEC2013 F13/F14 smoke and write route artifacts."""

    design_report = _read_json(Path(stage8_13_design_report_path))
    budget_lock = _read_json(Path(stage8_13_budget_lock_path))
    function_scope = _read_json(Path(stage8_13_function_scope_path))
    claim_gate = _read_json(Path(stage8_13_claim_gate_path))
    runtime_boundary = _read_json(Path(stage8_13_runtime_boundary_path))
    next_route = _read_json(Path(stage8_13_next_route_path))
    _validate_inputs(
        design_report=design_report,
        budget_lock=budget_lock,
        function_scope=function_scope,
        claim_gate=claim_gate,
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
    win_loss = _build_win_loss_report(
        trace_rows=trace_rows,
        smoke_function_ids=smoke_function_ids,
        promising_delta_threshold=float(promising_delta_threshold),
    )
    initial_objective_fe = len(smoke_function_ids) * len(methods)
    ledger = _build_fe_ledger(
        trace_rows=trace_rows,
        inherited_stage8_13_FE_total=int(budget_lock["stage8_13_FE_total"]),
        smoke_max_fe=int(smoke_max_fe),
        initial_objective_fe=initial_objective_fe,
    )
    boundary = _build_runtime_boundary(smoke_max_fe=int(smoke_max_fe))
    route = _build_route(win_loss)
    report = _build_report(
        trace_rows=trace_rows,
        method_summary=method_summary,
        win_loss=win_loss,
        ledger=ledger,
        route=route,
        design_report=design_report,
        budget_lock=budget_lock,
        smoke_function_ids=smoke_function_ids,
        smoke_seed=smoke_seed,
        smoke_max_fe=smoke_max_fe,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "objective_trace.jsonl", trace_rows)
    _write_json(output_path / "method_summary.json", method_summary)
    _write_json(output_path / "win_loss_report.json", win_loss)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    _write_json(output_path / "single_run_smoke_report.json", report)
    return report


def _validate_inputs(
    *,
    design_report: Mapping[str, Any],
    budget_lock: Mapping[str, Any],
    function_scope: Mapping[str, Any],
    claim_gate: Mapping[str, Any],
    runtime_boundary: Mapping[str, Any],
    next_route: Mapping[str, Any],
    smoke_function_ids: Sequence[int],
    smoke_max_fe: int,
) -> None:
    if design_report.get("stage") != "8.13" or design_report.get("status") != "PASS":
        raise ValueError("Stage 8.14 requires a passing Stage 8.13 design report.")
    if design_report.get("formal_execution_ready") is not True:
        raise ValueError("Stage 8.13 did not mark formal execution ready.")
    if int(design_report.get("run_count", 0)) != 25:
        raise ValueError("Stage 8.14 requires the Stage 8.13 25-run lock.")
    if budget_lock.get("stage") != "8.13" or budget_lock.get("status") != "PASS":
        raise ValueError("Stage 8.14 requires the Stage 8.13 budget lock.")
    if int(budget_lock.get("stage8_13_FE_total", -1)) != 0:
        raise ValueError("Stage 8.14 requires a zero-FE Stage 8.13 design gate.")
    if function_scope.get("stage") != "8.13":
        raise ValueError("Stage 8.14 requires the Stage 8.13 function scope.")
    overlap_ids = {int(item[1:]) for item in function_scope["overlap_focus_function_ids"]}
    if not set(map(int, smoke_function_ids)).issubset(overlap_ids):
        raise ValueError("Stage 8.14 smoke is limited to overlap-focused F13/F14.")
    if claim_gate.get("full_sota_claim_allowed_now") is not False:
        raise ValueError("Stage 8.14 refuses an already-open SOTA claim gate.")
    if runtime_boundary.get("official_cec2013_panel_run") is not False:
        raise ValueError("Stage 8.14 expects no prior official CEC2013 panel run.")
    if runtime_boundary.get("not_sota_claim") is not True:
        raise ValueError("Stage 8.14 requires the no-SOTA boundary.")
    if next_route.get("next_stage") != "Stage 8.14":
        raise ValueError("Stage 8.14 requires the Stage 8.13 route.")
    if next_route.get("run_formal_cec2013_panel_next") is not True:
        raise ValueError("Stage 8.13 did not route toward CEC2013 execution.")
    if int(smoke_max_fe) <= 0:
        raise ValueError("smoke_max_fe must be positive.")


def _build_methods() -> list[_Method]:
    generalized_policy = _GeneralizedPolicy()
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
        _Method(GENERALIZED_METHOD, generalized_policy.name, True, generalized_policy.coordinate),
    ]


def _load_smoke_problem(loader: Callable[[int], Any], function_id: int) -> _SmokeProblem:
    problem = loader(function_id)
    dimension = int(problem.dimension())
    lower, upper = problem.bounds()
    lower_bounds = np.asarray(lower, dtype=float)
    upper_bounds = np.asarray(upper, dtype=float)
    if lower_bounds.shape != (dimension,) or upper_bounds.shape != (dimension,):
        raise ValueError(f"F{function_id} bounds do not match dimension {dimension}.")
    shared_variables = sorted(int(item) for item in problem.shared_variables())
    if not shared_variables:
        raise ValueError(f"F{function_id} does not expose shared variables.")
    selected_shared = shared_variables[len(shared_variables) // 2]
    return _SmokeProblem(
        function_id=int(function_id),
        problem=problem,
        dimension=dimension,
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds,
        shared_variable=selected_shared,
        metadata=dict(problem.metadata()),
    )


def _run_method_loop(
    *, method: _Method, problem: _SmokeProblem, seed: int, max_fe: int
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


def _initial_vector(problem: _SmokeProblem, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed + problem.function_id * 1009)
    lower = problem.lower_bounds
    upper = problem.upper_bounds
    midpoint = (lower + upper) / 2.0
    width = np.maximum(upper - lower, 1e-12)
    vector = midpoint + rng.uniform(-0.02, 0.02, size=problem.dimension) * width
    return np.clip(vector, lower, upper)


def _build_conflict_state(
    *,
    current: np.ndarray,
    problem: _SmokeProblem,
    step_index: int,
    consensus_history: Sequence[float],
) -> SharedVariableConflictState:
    variable = problem.shared_variable
    current_value = float(current[variable])
    lower = float(problem.lower_bounds[variable])
    upper = float(problem.upper_bounds[variable])
    scale = max((upper - lower) * 0.08 / step_index, 1e-9)
    toward_center = current_value - np.sign(current_value if current_value else 1.0) * scale
    conflicting = current_value + np.sign(current_value if current_value else 1.0) * scale * 0.85
    moderate = current_value - np.sign(current_value if current_value else 1.0) * scale * 0.35
    function_id = int(problem.function_id)
    proposals = [
        GroupProposal(
            group_id=function_id * 100 + 1,
            variable_id=variable,
            proposed_value=toward_center,
            reward=0.82 + 0.01 * min(step_index, 5),
            metadata={"proposal_role": "toward_center", "fixed_baseopt": True},
        ),
        GroupProposal(
            group_id=function_id * 100 + 2,
            variable_id=variable,
            proposed_value=conflicting,
            reward=0.34,
            metadata={"proposal_role": "conflicting", "fixed_baseopt": True},
        ),
        GroupProposal(
            group_id=function_id * 100 + 3,
            variable_id=variable,
            proposed_value=moderate,
            reward=0.58,
            metadata={"proposal_role": "moderate", "fixed_baseopt": True},
        ),
    ]
    return SharedVariableConflictState.from_group_proposals(
        variable_id=variable,
        current_value=current_value,
        bounds=(lower, upper),
        proposals=proposals,
        consensus_history=consensus_history,
        diagnostics={
            "panel": (
                "synthetic_conflicting_overlap_panel"
                if function_id == 14
                else "synthetic_high_overlap_panel"
            ),
            "benchmark_suite": BENCHMARK_SUITE,
            "function_id": f"F{function_id}",
            "objective_loop_step": step_index,
            "fixed_baseopt": True,
            "official_cec2013_smoke": True,
        },
    )


def _trace_row(
    *,
    method: _Method,
    problem: _SmokeProblem,
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
        "source_stage": "8.13",
        "benchmark_suite": BENCHMARK_SUITE,
        "function_id": f"F{problem.function_id}",
        "function_index": int(problem.function_id),
        "run_index": 1,
        "seed": int(seed),
        "method_name": method.name,
        "operator_label": method.label,
        "policy_name": diagnostics.get("policy_name"),
        "policy_branch": diagnostics.get("policy_branch"),
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
        "source_stage": "8.13",
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
        policy_final = final_by_method[GENERALIZED_METHOD]
        best_baseline_method = min(
            BASELINE_METHOD_NAMES, key=lambda name: final_by_method[name]
        )
        best_baseline_final = final_by_method[best_baseline_method]
        delta = round(policy_final - best_baseline_final, 12)
        case_rows.append(
            {
                "function_id": f"F{int(function_id)}",
                "run_index": 1,
                "seed": int(trace_rows[0]["seed"]),
                "policy_name": POLICY_NAME,
                "policy_final_best": policy_final,
                "best_baseline_method": best_baseline_method,
                "best_baseline_final_best": best_baseline_final,
                "policy_vs_best_baseline_delta": delta,
                "policy_vs_best_baseline_result": _comparison_result(
                    delta, promising_delta_threshold
                ),
            }
        )
    counts = _count_results(row["policy_vs_best_baseline_result"] for row in case_rows)
    promising = int(counts["loss"]) == 0
    return {
        "schema_version": WIN_LOSS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.13",
        "benchmark_suite": BENCHMARK_SUITE,
        "run_count": 1,
        "comparison_case_count": len(case_rows),
        "case_rows": case_rows,
        "policy_vs_best_baseline": counts,
        "single_run_promising": promising,
        "baseline_comparison_made": True,
        "promising_delta_threshold": float(promising_delta_threshold),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    inherited_stage8_13_FE_total: int,
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
        "budget_scope": "cec2013_single_run_overlap_smoke",
        "run_count": 1,
        "smoke_max_fe_per_method_per_function": int(smoke_max_fe),
        "inherited_stage8_13_FE_total": int(inherited_stage8_13_FE_total),
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
        "claim_scope": "CEC2013 single-run smoke and route decision only",
        "run_count": 1,
        "smoke_max_fe_per_method_per_function": int(smoke_max_fe),
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "official_cec2013_panel_run": False,
        "single_run_smoke_executed": True,
        "not_full_25_run_panel": True,
        "not_full_f1_f15_panel": True,
        "full_official_budget_deferred": True,
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
            "full 25-run CEC2013 result",
            "full F1..F15 CEC2013 result",
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_route(win_loss: Mapping[str, Any]) -> dict[str, Any]:
    promising = bool(win_loss["single_run_promising"])
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": (
            "PROMISING_SINGLE_RUN_PROCEED_TO_25_RUN_PANEL"
            if promising
            else "NOT_PROMISING_SINGLE_RUN_DIAGNOSE_BEFORE_25_RUN_PANEL"
        ),
        "decision_reason": (
            "Stage 8.14 ran one overlap-focused CEC2013 smoke before spending "
            "the full 25-run formal budget."
        ),
        "next_stage": NEXT_STAGE,
        "if_promising_next": "execute_full_25_run_formal_panel",
        "if_not_promising_next": "failure_honest_cec2013_smoke_diagnosis",
        "run_full_25_run_panel_next": promising,
        "run_failure_diagnosis_next": not promising,
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
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
    design_report: Mapping[str, Any],
    budget_lock: Mapping[str, Any],
    smoke_function_ids: Sequence[int],
    smoke_seed: int,
    smoke_max_fe: int,
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.13",
        "smoke_scope": "cec2013_single_run_overlap_smoke",
        "benchmark_suite": BENCHMARK_SUITE,
        "policy_name": POLICY_NAME,
        "run_count": 1,
        "smoke_seed": int(smoke_seed),
        "smoke_max_fe_per_method_per_function": int(smoke_max_fe),
        "function_ids": [f"F{int(function_id)}" for function_id in smoke_function_ids],
        "function_count": len(smoke_function_ids),
        "full_formal_run_count": int(design_report["run_count"]),
        "full_formal_function_count": int(design_report["official_function_count"]),
        "full_formal_max_fe": int(budget_lock["max_fe"]),
        "not_full_25_run_panel": True,
        "not_full_f1_f15_panel": True,
        "full_official_budget_deferred": True,
        "single_run_smoke_executed": True,
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
        "method_summary_written": bool(method_summary["method_rows"]),
        "win_loss_report_written": True,
        "stage8_14_route_decision": route["decision"],
        "single_run_promising": bool(win_loss["single_run_promising"]),
        "recommended_next_stage": NEXT_STAGE,
        "recommended_next_work": (
            "execute_full_25_run_formal_panel"
            if win_loss["single_run_promising"]
            else "failure_honest_cec2013_smoke_diagnosis"
        ),
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


def _evaluate(problem: Any, vector: np.ndarray) -> float:
    return float(problem.evaluate(vector))


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

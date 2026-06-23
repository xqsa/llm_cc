"""Stage 8.23 CEC2013 F13/F14 multiseed pilot for the frozen LLM policy."""

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
    DEFAULT_SMOKE_MAX_FE,
    SMOKE_FUNCTION_IDS,
    _build_conflict_state,
    _evaluate,
    _initial_vector,
    _load_smoke_problem,
)


STAGE = "8.23"
REPORT_SCHEMA_VERSION = "loco.stage8_23_multiseed_pilot_report.v1"
TRACE_SCHEMA_VERSION = "loco.stage8_23_objective_trace.v1"
METHOD_SUMMARY_SCHEMA_VERSION = "loco.stage8_23_method_summary.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_23_win_loss_report.v1"
BRANCH_SCHEMA_VERSION = "loco.stage8_23_policy_branch_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_23_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_23_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_23_next_route_decision.v1"

FROZEN_METHOD = "stage8_22_frozen_llm_policy"
BASELINE_METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
]
METHOD_NAMES = [*BASELINE_METHOD_NAMES, FROZEN_METHOD]
DEFAULT_RUN_SEEDS = [0, 1, 2]
NEXT_IF_PROMISING = "Stage 8.24"
NEXT_IF_NOT_PROMISING = "Stage 8.23"


@dataclass(frozen=True)
class _Method:
    name: str
    label: str
    is_loco_policy: bool
    coordinate: Callable[[SharedVariableConflictState], CoordinationResult]


class FrozenLLMPolicy:
    """Execute the frozen Stage 8.22 policy DSL without LLM calls."""

    name = "FrozenStage822LLMPolicy"

    def __init__(self, frozen_policy: Mapping[str, Any]):
        self.candidate_id = str(frozen_policy["candidate_id"])
        self.family = str(frozen_policy["family"])
        self.rules = tuple(dict(rule) for rule in frozen_policy["rules"])
        self._best_reward = BestRewardSelection()
        self._weighted = WeightedConsensus(temperature=1.0)
        self._simple = AverageConsensus()

    def coordinate(self, conflict_state: SharedVariableConflictState) -> CoordinationResult:
        features = _policy_features(conflict_state)
        action = "damp_best_reward"
        for rule in self.rules:
            if _condition_matches(str(rule["condition"]), features):
                action = str(rule["action"])
                break
        value = self._action_value(action, conflict_state)
        return CoordinationResult(
            variable_id=conflict_state.variable_id,
            coordinated_value=conflict_state.clip(value),
            operator_name=self.name,
            extra_fe=0,
            diagnostics={
                "policy_name": self.candidate_id,
                "policy_family": self.family,
                "policy_branch": action,
                "frozen_policy_used": True,
            },
        )

    def _action_value(self, action: str, state: SharedVariableConflictState) -> float:
        if action == "trust_best_reward":
            return self._best_reward.coordinate(state).coordinated_value
        if action == "weighted_consensus":
            return self._weighted.coordinate(state).coordinated_value
        if action == "simple_consensus":
            return self._simple.coordinate(state).coordinated_value
        if action == "damp_best_reward":
            best = self._best_reward.coordinate(state).coordinated_value
            return state.current_value + 0.5 * (best - state.current_value)
        if action == "shrinkage_repair":
            weighted = self._weighted.coordinate(state).coordinated_value
            return state.current_value + 0.5 * (weighted - state.current_value)
        if action == "reject_unstable_best_reward":
            return self._simple.coordinate(state).coordinated_value
        raise ValueError(f"unsupported frozen policy action: {action}")


def run_stage8_23_cec2013_f13_f14_multiseed_pilot(
    *,
    stage8_22_frozen_policy_path: Path | str,
    stage8_22_frozen_policy_payload_path: Path | str,
    stage8_22_manifest_path: Path | str,
    stage8_22_readiness_protocol_path: Path | str,
    stage8_22_fe_ledger_path: Path | str,
    stage8_22_runtime_boundary_path: Path | str,
    stage8_22_next_route_path: Path | str,
    output_dir: Path | str,
    problem_loader: Callable[[int], Any] | None = None,
    smoke_function_ids: Sequence[int] = SMOKE_FUNCTION_IDS,
    run_seeds: Sequence[int] = DEFAULT_RUN_SEEDS,
    max_fe_per_method_per_function: int = DEFAULT_SMOKE_MAX_FE,
    promising_delta_threshold: float = 0.0,
) -> dict[str, Any]:
    """Run the frozen LLM policy on a bounded F13/F14 multiseed pilot."""

    frozen_policy = _read_json(Path(stage8_22_frozen_policy_path))
    frozen_payload = _read_json(Path(stage8_22_frozen_policy_payload_path))
    manifest = _read_json(Path(stage8_22_manifest_path))
    readiness = _read_json(Path(stage8_22_readiness_protocol_path))
    stage8_22_ledger = _read_json(Path(stage8_22_fe_ledger_path))
    stage8_22_boundary = _read_json(Path(stage8_22_runtime_boundary_path))
    stage8_22_route = _read_json(Path(stage8_22_next_route_path))
    _validate_inputs(
        frozen_policy=frozen_policy,
        frozen_payload=frozen_payload,
        manifest=manifest,
        readiness=readiness,
        stage8_22_ledger=stage8_22_ledger,
        stage8_22_boundary=stage8_22_boundary,
        stage8_22_route=stage8_22_route,
        smoke_function_ids=smoke_function_ids,
        run_seeds=run_seeds,
        max_fe=int(max_fe_per_method_per_function),
    )

    loader = problem_loader or load_cec2013lsgo_problem
    methods = _build_methods(frozen_policy)
    trace_rows: list[dict[str, Any]] = []
    for function_id in smoke_function_ids:
        smoke_problem = _load_smoke_problem(loader, int(function_id))
        for seed in run_seeds:
            for method in methods:
                trace_rows.extend(
                    _run_method_loop(
                        method=method,
                        problem=smoke_problem,
                        seed=int(seed),
                        max_fe=int(max_fe_per_method_per_function),
                        selected_candidate_id=str(frozen_policy["candidate_id"]),
                    )
                )

    method_summary = _build_method_summary(
        trace_rows=trace_rows,
        smoke_function_ids=smoke_function_ids,
        run_seeds=run_seeds,
    )
    win_loss = _build_win_loss_report(
        trace_rows=trace_rows,
        smoke_function_ids=smoke_function_ids,
        run_seeds=run_seeds,
        promising_delta_threshold=float(promising_delta_threshold),
    )
    branch_report = _build_policy_branch_report(trace_rows, frozen_policy)
    initial_objective_fe = len(smoke_function_ids) * len(run_seeds) * len(methods)
    ledger = _build_fe_ledger(
        trace_rows=trace_rows,
        inherited_stage8_22_FE_total=int(stage8_22_ledger["FE_total"]),
        max_fe=int(max_fe_per_method_per_function),
        run_count=len(run_seeds),
        initial_objective_fe=initial_objective_fe,
    )
    boundary = _build_runtime_boundary(
        run_count=len(run_seeds), max_fe=int(max_fe_per_method_per_function)
    )
    route = _build_route(win_loss)
    report = _build_report(
        trace_rows=trace_rows,
        win_loss=win_loss,
        branch_report=branch_report,
        ledger=ledger,
        route=route,
        frozen_policy=frozen_policy,
        smoke_function_ids=smoke_function_ids,
        run_seeds=run_seeds,
        max_fe=int(max_fe_per_method_per_function),
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "objective_trace.jsonl", trace_rows)
    _write_json(output_path / "method_summary.json", method_summary)
    _write_json(output_path / "win_loss_report.json", win_loss)
    _write_json(output_path / "policy_branch_report.json", branch_report)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    _write_json(output_path / "multiseed_pilot_report.json", report)
    return report


def _validate_inputs(
    *,
    frozen_policy: Mapping[str, Any],
    frozen_payload: Mapping[str, Any],
    manifest: Mapping[str, Any],
    readiness: Mapping[str, Any],
    stage8_22_ledger: Mapping[str, Any],
    stage8_22_boundary: Mapping[str, Any],
    stage8_22_route: Mapping[str, Any],
    smoke_function_ids: Sequence[int],
    run_seeds: Sequence[int],
    max_fe: int,
) -> None:
    if frozen_policy.get("stage") != "8.22":
        raise ValueError("Stage 8.23 requires a Stage 8.22 frozen policy.")
    if frozen_policy.get("freeze_status") != "FROZEN_FOR_CEC2013_F13_F14_MULTISEED_NOT_FINAL":
        raise ValueError("Stage 8.23 requires the Stage 8.22 F13/F14 freeze status.")
    if frozen_payload.get("policy_id") != frozen_policy.get("candidate_id"):
        raise ValueError("Frozen policy payload and policy metadata mismatch.")
    if manifest.get("frozen_policy_payload_matches_stage8_20") is not True:
        raise ValueError("Stage 8.23 requires exact Stage 8.20 payload freeze.")
    if readiness.get("status") != "READY_FOR_STAGE8_23_CEC2013_F13_F14_MULTISEED_PILOT":
        raise ValueError("Stage 8.23 requires the Stage 8.22 readiness protocol.")
    if int(stage8_22_ledger.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.23 requires zero-FE Stage 8.22 freeze input.")
    if stage8_22_boundary.get("objective_loop_executed") is not False:
        raise ValueError("Stage 8.22 must not have executed objective loops.")
    if stage8_22_route.get("next_stage") != "Stage 8.23":
        raise ValueError("Stage 8.23 requires the Stage 8.22 route.")
    if set(map(int, smoke_function_ids)) != {13, 14}:
        raise ValueError("Stage 8.23 is limited to CEC2013 F13/F14.")
    if len(list(run_seeds)) < 2:
        raise ValueError("Stage 8.23 requires multiple seeds.")
    if int(max_fe) <= 0:
        raise ValueError("max_fe_per_method_per_function must be positive.")


def _build_methods(frozen_policy: Mapping[str, Any]) -> list[_Method]:
    frozen = FrozenLLMPolicy(frozen_policy)
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
        _Method(FROZEN_METHOD, frozen.name, True, frozen.coordinate),
    ]


def _run_method_loop(
    *,
    method: _Method,
    problem: Any,
    seed: int,
    max_fe: int,
    selected_candidate_id: str,
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
                selected_candidate_id=selected_candidate_id,
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
    selected_candidate_id: str,
) -> dict[str, Any]:
    metadata = dict(problem.metadata)
    diagnostics = dict(result.diagnostics or {})
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "8.22",
        "benchmark_suite": BENCHMARK_SUITE,
        "function_id": f"F{problem.function_id}",
        "function_index": int(problem.function_id),
        "run_index": int(seed) + 1,
        "seed": int(seed),
        "method_name": method.name,
        "operator_label": method.label,
        "selected_candidate_id": selected_candidate_id if method.name == FROZEN_METHOD else None,
        "policy_name": diagnostics.get("policy_name"),
        "policy_branch": diagnostics.get("policy_branch"),
        "frozen_policy_used": bool(method.name == FROZEN_METHOD),
        "is_loco_policy": method.is_loco_policy,
        "official_cec2013_multiseed_pilot": True,
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
        "selected_policy_revision_used": False,
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
    run_seeds: Sequence[int],
) -> dict[str, Any]:
    method_rows = []
    for method_name in METHOD_NAMES:
        rows = [row for row in trace_rows if row["method_name"] == method_name]
        final_bests = [
            _last_best(_case_seed_rows(trace_rows, function_id, seed), method_name)
            for function_id in smoke_function_ids
            for seed in run_seeds
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
        "source_stage": "8.22",
        "benchmark_suite": BENCHMARK_SUITE,
        "run_count": len(run_seeds),
        "seeds": [int(seed) for seed in run_seeds],
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
    run_seeds: Sequence[int],
    promising_delta_threshold: float,
) -> dict[str, Any]:
    case_rows = []
    for function_id in smoke_function_ids:
        for seed in run_seeds:
            rows = _case_seed_rows(trace_rows, int(function_id), int(seed))
            final_by_method = {
                method_name: _last_best(rows, method_name) for method_name in METHOD_NAMES
            }
            frozen_final = final_by_method[FROZEN_METHOD]
            best_reward_final = final_by_method["best_reward_select"]
            best_baseline_method = min(
                BASELINE_METHOD_NAMES, key=lambda name: final_by_method[name]
            )
            best_baseline_final = final_by_method[best_baseline_method]
            case_rows.append(
                {
                    "function_id": f"F{int(function_id)}",
                    "seed": int(seed),
                    "selected_candidate_id": rows[0].get("selected_candidate_id"),
                    "frozen_policy_final_best": frozen_final,
                    "best_reward_select_final_best": best_reward_final,
                    "best_baseline_method": best_baseline_method,
                    "best_baseline_final_best": best_baseline_final,
                    "frozen_vs_best_reward_select_delta": round(
                        frozen_final - best_reward_final, 12
                    ),
                    "frozen_vs_best_baseline_delta": round(
                        frozen_final - best_baseline_final, 12
                    ),
                    "frozen_vs_best_reward_select_result": _comparison_result(
                        frozen_final - best_reward_final,
                        promising_delta_threshold,
                    ),
                    "frozen_vs_best_baseline_result": _comparison_result(
                        frozen_final - best_baseline_final,
                        promising_delta_threshold,
                    ),
                }
            )
    frozen_vs_best_reward = _count_results(
        row["frozen_vs_best_reward_select_result"] for row in case_rows
    )
    frozen_vs_best_baseline = _count_results(
        row["frozen_vs_best_baseline_result"] for row in case_rows
    )
    promising = int(frozen_vs_best_reward["loss"]) == 0
    return {
        "schema_version": WIN_LOSS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.22",
        "benchmark_suite": BENCHMARK_SUITE,
        "run_count": len(run_seeds),
        "comparison_case_count": len(case_rows),
        "case_rows": case_rows,
        "frozen_policy_vs_best_reward_select": frozen_vs_best_reward,
        "frozen_policy_vs_best_baseline": frozen_vs_best_baseline,
        "multiseed_pilot_promising": promising,
        "baseline_comparison_made": True,
        "promising_delta_threshold": float(promising_delta_threshold),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_policy_branch_report(
    trace_rows: Sequence[Mapping[str, Any]], frozen_policy: Mapping[str, Any]
) -> dict[str, Any]:
    policy_rows = [row for row in trace_rows if row["method_name"] == FROZEN_METHOD]
    branch_names = ["trust_best_reward", "damp_best_reward", "shrinkage_repair"]
    branch_counts = {
        branch: sum(1 for row in policy_rows if row.get("policy_branch") == branch)
        for branch in branch_names
    }
    return {
        "schema_version": BRANCH_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.22",
        "selected_candidate_id": str(frozen_policy["candidate_id"]),
        "freeze_status": str(frozen_policy["freeze_status"]),
        "policy_trace_row_count": len(policy_rows),
        "branch_counts": branch_counts,
        "trust_best_reward_exercised": int(branch_counts["trust_best_reward"]) >= 1,
        "non_trust_branch_exercised": any(
            count > 0
            for branch, count in branch_counts.items()
            if branch != "trust_best_reward"
        ),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    inherited_stage8_22_FE_total: int,
    max_fe: int,
    run_count: int,
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
        "budget_scope": "cec2013_f13_f14_multiseed_pilot",
        "run_count": int(run_count),
        "max_fe_per_method_per_function": int(max_fe),
        "inherited_stage8_22_FE_total": int(inherited_stage8_22_FE_total),
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


def _build_runtime_boundary(*, run_count: int, max_fe: int) -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "CEC2013 F13/F14 frozen-policy multiseed pilot only",
        "run_count": int(run_count),
        "max_fe_per_method_per_function": int(max_fe),
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "official_cec2013_panel_run": False,
        "multiseed_pilot_executed": True,
        "not_full_25_run_panel": True,
        "not_full_f1_f15_panel": True,
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "selected_policy_revision": False,
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


def _build_route(win_loss: Mapping[str, Any]) -> dict[str, Any]:
    promising = bool(win_loss["multiseed_pilot_promising"])
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": (
            "PROMISING_MULTISEED_ROUTE_TO_CHECKPOINT_BUDGET_PILOT"
            if promising
            else "NOT_PROMISING_MULTISEED_DIAGNOSE_BEFORE_FORMAL_PANEL"
        ),
        "next_stage": NEXT_IF_PROMISING if promising else NEXT_IF_NOT_PROMISING,
        "allowed_next_work": (
            "cec2013_f13_f14_checkpoint_budget_pilot"
            if promising
            else "failure_honest_frozen_policy_multiseed_diagnosis"
        ),
        "run_full_25_run_panel_next": False,
        "run_checkpoint_budget_pilot_next": bool(promising),
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    win_loss: Mapping[str, Any],
    branch_report: Mapping[str, Any],
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
    frozen_policy: Mapping[str, Any],
    smoke_function_ids: Sequence[int],
    run_seeds: Sequence[int],
    max_fe: int,
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.22",
        "pilot_scope": "cec2013_f13_f14_frozen_policy_multiseed_pilot",
        "benchmark_suite": BENCHMARK_SUITE,
        "selected_candidate_id": str(frozen_policy["candidate_id"]),
        "freeze_status": str(frozen_policy["freeze_status"]),
        "frozen_policy_used": True,
        "run_count": len(run_seeds),
        "seed_count": len(run_seeds),
        "seeds": [int(seed) for seed in run_seeds],
        "max_fe_per_method_per_function": int(max_fe),
        "function_ids": [f"F{int(function_id)}" for function_id in smoke_function_ids],
        "function_count": len(smoke_function_ids),
        "not_full_25_run_panel": True,
        "not_full_f1_f15_panel": True,
        "multiseed_pilot_executed": True,
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
        "frozen_policy_vs_best_reward_select": dict(
            win_loss["frozen_policy_vs_best_reward_select"]
        ),
        "frozen_policy_vs_best_baseline": dict(
            win_loss["frozen_policy_vs_best_baseline"]
        ),
        "policy_branch_report_written": True,
        "trust_best_reward_branch_count": int(
            branch_report["branch_counts"]["trust_best_reward"]
        ),
        "multiseed_pilot_promising": bool(win_loss["multiseed_pilot_promising"]),
        "run_full_25_run_panel_next": False,
        "recommended_next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "selected_policy_revision_used": False,
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


def _policy_features(state: SharedVariableConflictState) -> dict[str, float]:
    rewards = np.asarray(state.group_rewards, dtype=float)
    sorted_rewards = np.sort(rewards)
    reward_margin = (
        float(sorted_rewards[-1] - sorted_rewards[-2]) if len(sorted_rewards) >= 2 else 1.0
    )
    return {
        "shared_variable_oscillation": float(oscillation_score(state)),
        "reward_margin": reward_margin,
    }


def _condition_matches(condition: str, features: Mapping[str, float]) -> bool:
    text = " ".join(condition.strip().split())
    if text.lower() == "always":
        return True
    for operator in ["<=", ">=", "<", ">"]:
        if operator in text:
            left, right = text.split(operator, 1)
            value = float(features.get(left.strip(), 0.0))
            threshold = float(right.strip())
            if operator == "<=":
                return value <= threshold
            if operator == ">=":
                return value >= threshold
            if operator == "<":
                return value < threshold
            return value > threshold
    return bool(features.get(text, 0.0) >= 0.5)


def _case_seed_rows(
    trace_rows: Sequence[Mapping[str, Any]], function_id: int, seed: int
) -> list[Mapping[str, Any]]:
    return [
        row
        for row in trace_rows
        if row["function_id"] == f"F{int(function_id)}" and int(row["seed"]) == int(seed)
    ]


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

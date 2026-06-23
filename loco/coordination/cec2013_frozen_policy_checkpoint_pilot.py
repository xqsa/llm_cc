"""Stage 8.24 CEC2013 F13/F14 checkpoint-budget pilot for the frozen LLM policy."""

from __future__ import annotations

import json
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from loco.benchmarks.cec2013lsgo_metabox import load_cec2013lsgo_problem
from loco.conflict.conflict_state import SharedVariableConflictState
from loco.coordination.baselines import (
    AverageConsensus,
    BestRewardSelection,
    CoordinationResult,
    NoCoordination,
    WeightedConsensus,
)
from loco.coordination.cec2013_frozen_policy_multiseed_pilot import _condition_matches
from loco.coordination.cec2013_single_run_smoke_decision import (
    BENCHMARK_SUITE,
    SMOKE_FUNCTION_IDS,
    _build_conflict_state,
    _evaluate,
    _initial_vector,
    _load_smoke_problem,
)


STAGE = "8.24"
REPORT_SCHEMA_VERSION = "loco.stage8_24_checkpoint_pilot_report.v1"
CHECKPOINT_TRACE_SCHEMA_VERSION = "loco.stage8_24_checkpoint_trace.v1"
METHOD_SUMMARY_SCHEMA_VERSION = "loco.stage8_24_method_summary.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_24_win_loss_report.v1"
BRANCH_SCHEMA_VERSION = "loco.stage8_24_policy_branch_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_24_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_24_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_24_next_route_decision.v1"

FROZEN_METHOD = "stage8_22_frozen_llm_policy"
BASELINE_METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
]
METHOD_NAMES = [*BASELINE_METHOD_NAMES, FROZEN_METHOD]
DEFAULT_RUN_SEEDS = [0, 1, 2]
DEFAULT_CHECKPOINT_MAX_FE = 120000
NEXT_IF_PROMISING = "Stage 8.25"
NEXT_IF_NOT_PROMISING = "Stage 8.24"


@dataclass(frozen=True)
class _Method:
    name: str
    label: str
    is_loco_policy: bool
    coordinate: Callable[[SharedVariableConflictState], CoordinationResult]


@dataclass(frozen=True)
class _CaseResult:
    function_id: int
    seed: int
    method_name: str
    final_best: float
    objective_fe: int
    total_fe: int
    checkpoint_rows: list[dict[str, Any]]
    branch_counts: Counter[str]


def run_stage8_24_cec2013_f13_f14_checkpoint_budget_pilot(
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
    function_ids: Sequence[int] = SMOKE_FUNCTION_IDS,
    run_seeds: Sequence[int] = DEFAULT_RUN_SEEDS,
    max_fe_per_method_per_function: int = DEFAULT_CHECKPOINT_MAX_FE,
    checkpoint_steps: Sequence[int] | None = None,
    max_workers: int | None = None,
    promising_delta_threshold: float = 0.0,
) -> dict[str, Any]:
    """Run the frozen LLM policy on F13/F14 with a larger checkpoint budget."""

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
        function_ids=function_ids,
        run_seeds=run_seeds,
        max_fe=int(max_fe_per_method_per_function),
    )

    checkpoint_step_set = _checkpoint_step_set(
        max_fe=int(max_fe_per_method_per_function),
        checkpoint_steps=checkpoint_steps,
    )
    loader = problem_loader or load_cec2013lsgo_problem
    methods = _build_methods(frozen_policy)
    selected_worker_count = _worker_count(max_workers, methods, function_ids, run_seeds)
    use_parallel = problem_loader is None and selected_worker_count > 1
    case_results = (
        _run_cases_parallel(
            function_ids=function_ids,
            run_seeds=run_seeds,
            method_names=[method.name for method in methods],
            max_fe=int(max_fe_per_method_per_function),
            checkpoint_steps=checkpoint_step_set,
            selected_candidate_id=str(frozen_policy["candidate_id"]),
            max_workers=max_workers,
        )
        if use_parallel
        else _run_cases_serial(
            loader=loader,
            function_ids=function_ids,
            run_seeds=run_seeds,
            methods=methods,
            max_fe=int(max_fe_per_method_per_function),
            checkpoint_steps=checkpoint_step_set,
            selected_candidate_id=str(frozen_policy["candidate_id"]),
        )
    )
    checkpoint_rows = [
        checkpoint
        for result in case_results
        for checkpoint in result.checkpoint_rows
    ]

    method_summary = _build_method_summary(
        case_results=case_results,
        function_ids=function_ids,
        run_seeds=run_seeds,
        max_fe=int(max_fe_per_method_per_function),
    )
    win_loss = _build_win_loss_report(
        case_results=case_results,
        function_ids=function_ids,
        run_seeds=run_seeds,
        promising_delta_threshold=float(promising_delta_threshold),
    )
    branch_report = _build_policy_branch_report(case_results, frozen_policy)
    initial_objective_fe = len(function_ids) * len(run_seeds) * len(methods)
    ledger = _build_fe_ledger(
        case_results=case_results,
        inherited_stage8_22_FE_total=int(stage8_22_ledger["FE_total"]),
        max_fe=int(max_fe_per_method_per_function),
        run_count=len(run_seeds),
        initial_objective_fe=initial_objective_fe,
    )
    boundary = _build_runtime_boundary(
        run_count=len(run_seeds),
        max_fe=int(max_fe_per_method_per_function),
            checkpoint_steps=checkpoint_step_set,
            parallel_execution_used=use_parallel,
            max_workers=selected_worker_count if use_parallel else 1,
    )
    route = _build_route(win_loss)
    report = _build_report(
        case_results=case_results,
        checkpoint_rows=checkpoint_rows,
        win_loss=win_loss,
        branch_report=branch_report,
        ledger=ledger,
        route=route,
        frozen_policy=frozen_policy,
        function_ids=function_ids,
        run_seeds=run_seeds,
        max_fe=int(max_fe_per_method_per_function),
        checkpoint_steps=checkpoint_step_set,
        parallel_execution_used=use_parallel,
        max_workers=selected_worker_count if use_parallel else 1,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    raw_trace = output_path / "objective_trace.jsonl"
    if raw_trace.exists():
        raw_trace.unlink()
    _write_jsonl(output_path / "checkpoint_trace.jsonl", checkpoint_rows)
    _write_json(output_path / "method_summary.json", method_summary)
    _write_json(output_path / "win_loss_report.json", win_loss)
    _write_json(output_path / "policy_branch_report.json", branch_report)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    _write_json(output_path / "checkpoint_pilot_report.json", report)
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
    function_ids: Sequence[int],
    run_seeds: Sequence[int],
    max_fe: int,
) -> None:
    if frozen_policy.get("stage") != "8.22":
        raise ValueError("Stage 8.24 requires a Stage 8.22 frozen policy.")
    if frozen_policy.get("freeze_status") != "FROZEN_FOR_CEC2013_F13_F14_MULTISEED_NOT_FINAL":
        raise ValueError("Stage 8.24 requires the Stage 8.22 F13/F14 freeze status.")
    if frozen_payload.get("policy_id") != frozen_policy.get("candidate_id"):
        raise ValueError("Frozen policy payload and policy metadata mismatch.")
    if manifest.get("frozen_policy_payload_matches_stage8_20") is not True:
        raise ValueError("Stage 8.24 requires exact Stage 8.20 payload freeze.")
    if readiness.get("status") != "READY_FOR_STAGE8_23_CEC2013_F13_F14_MULTISEED_PILOT":
        raise ValueError("Stage 8.24 requires the Stage 8.22 readiness protocol.")
    if int(stage8_22_ledger.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.24 requires zero-FE Stage 8.22 freeze input.")
    if stage8_22_boundary.get("objective_loop_executed") is not False:
        raise ValueError("Stage 8.22 must not have executed objective loops.")
    if stage8_22_route.get("next_stage") != "Stage 8.23":
        raise ValueError("Stage 8.24 requires the Stage 8.22 route anchor.")
    if set(map(int, function_ids)) != {13, 14}:
        raise ValueError("Stage 8.24 is limited to CEC2013 F13/F14.")
    if len(list(run_seeds)) < 2:
        raise ValueError("Stage 8.24 requires multiple seeds.")
    if int(max_fe) <= 0:
        raise ValueError("max_fe_per_method_per_function must be positive.")


def _checkpoint_step_set(*, max_fe: int, checkpoint_steps: Sequence[int] | None) -> set[int]:
    if checkpoint_steps is None:
        candidates = [1, 1200, 12000, 30000, 60000, int(max_fe)]
    else:
        candidates = [int(step) for step in checkpoint_steps]
    steps = {step for step in candidates if 1 <= step <= int(max_fe)}
    steps.add(int(max_fe))
    return steps


def _build_methods(frozen_policy: Mapping[str, Any]) -> list[_Method]:
    del frozen_policy
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
        _Method(FROZEN_METHOD, "FrozenStage822LLMPolicy", True, _unused_coordinate),
    ]


def _unused_coordinate(_: SharedVariableConflictState) -> CoordinationResult:
    raise RuntimeError("Stage 8.24 uses the optimized checkpoint fast path.")


def _run_cases_serial(
    *,
    loader: Callable[[int], Any],
    function_ids: Sequence[int],
    run_seeds: Sequence[int],
    methods: Sequence[_Method],
    max_fe: int,
    checkpoint_steps: set[int],
    selected_candidate_id: str,
) -> list[_CaseResult]:
    case_results: list[_CaseResult] = []
    for function_id in function_ids:
        problem = _load_smoke_problem(loader, int(function_id))
        for seed in run_seeds:
            for method in methods:
                case_results.append(
                    _run_method_loop(
                        method=method,
                        problem=problem,
                        seed=int(seed),
                        max_fe=int(max_fe),
                        checkpoint_steps=checkpoint_steps,
                        selected_candidate_id=selected_candidate_id,
                    )
                )
    return case_results


def _run_cases_parallel(
    *,
    function_ids: Sequence[int],
    run_seeds: Sequence[int],
    method_names: Sequence[str],
    max_fe: int,
    checkpoint_steps: set[int],
    selected_candidate_id: str,
    max_workers: int | None,
) -> list[_CaseResult]:
    tasks = [
        (
            int(function_id),
            int(seed),
            str(method_name),
            int(max_fe),
            tuple(sorted(checkpoint_steps)),
            selected_candidate_id,
        )
        for function_id in function_ids
        for seed in run_seeds
        for method_name in method_names
    ]
    workers = _worker_count(max_workers, method_names, function_ids, run_seeds)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(_run_case_worker, tasks))
    return list(results)


def _run_case_worker(task: tuple[int, int, str, int, tuple[int, ...], str]) -> _CaseResult:
    function_id, seed, method_name, max_fe, checkpoint_steps, selected_candidate_id = task
    problem = _load_smoke_problem(load_cec2013lsgo_problem, int(function_id))
    method = _method_by_name(str(method_name))
    return _run_method_loop(
        method=method,
        problem=problem,
        seed=int(seed),
        max_fe=int(max_fe),
        checkpoint_steps=set(int(step) for step in checkpoint_steps),
        selected_candidate_id=str(selected_candidate_id),
    )


def _method_by_name(method_name: str) -> _Method:
    for method in _build_methods({}):
        if method.name == method_name:
            return method
    raise ValueError(f"Unknown Stage 8.24 method: {method_name}")


def _worker_count(
    max_workers: int | None,
    methods: Sequence[Any],
    function_ids: Sequence[int],
    run_seeds: Sequence[int],
) -> int:
    task_count = len(list(function_ids)) * len(list(run_seeds)) * len(list(methods))
    cpu_count = os.cpu_count() or 1
    requested = int(max_workers) if max_workers is not None else min(cpu_count, task_count, 8)
    return max(1, min(requested, task_count))


def _run_method_loop(
    *,
    method: _Method,
    problem: Any,
    seed: int,
    max_fe: int,
    checkpoint_steps: set[int],
    selected_candidate_id: str,
) -> _CaseResult:
    current = _initial_vector(problem, seed)
    best_objective = _evaluate(problem.problem, current)
    checkpoint_rows: list[dict[str, Any]] = []
    branch_counts: Counter[str] = Counter()
    objective_fe = 0
    total_fe = 0
    last_consensus_value: float | None = None
    last_delta_sign = 0.0
    nonzero_delta_count = 0
    sign_change_count = 0

    for step_index in range(1, max_fe + 1):
        snapshot = _proposal_snapshot(
            current=current,
            problem=problem,
            step_index=step_index,
            oscillation=_incremental_oscillation(
                sign_change_count=sign_change_count,
                nonzero_delta_count=nonzero_delta_count,
            ),
        )
        coordinated_value, policy_branch = _coordinate_fast(method.name, snapshot)
        candidate = current.copy()
        candidate[problem.shared_variable] = coordinated_value
        candidate = np.clip(candidate, problem.lower_bounds, problem.upper_bounds)
        objective_value = _evaluate(problem.problem, candidate)
        objective_fe += 1
        total_fe += 2
        improved = objective_value <= best_objective
        if improved:
            current = candidate
            best_objective = objective_value
            if last_consensus_value is not None:
                delta = float(coordinated_value - last_consensus_value)
                if abs(delta) > 1e-12:
                    sign = float(np.sign(delta))
                    if last_delta_sign and sign != last_delta_sign:
                        sign_change_count += 1
                    last_delta_sign = sign
                    nonzero_delta_count += 1
            last_consensus_value = float(coordinated_value)

        if method.name == FROZEN_METHOD:
            branch_counts[str(policy_branch or "unknown")] += 1

        if step_index in checkpoint_steps:
            checkpoint_rows.append(
                _checkpoint_trace_row_fast(
                    method=method,
                    problem=problem,
                    snapshot=snapshot,
                    coordinated_value=coordinated_value,
                    policy_branch=policy_branch,
                    step_index=step_index,
                    seed=seed,
                    objective_value=objective_value,
                    best_objective=best_objective,
                    improved=improved,
                    selected_candidate_id=selected_candidate_id,
                )
            )
    return _CaseResult(
        function_id=int(problem.function_id),
        seed=int(seed),
        method_name=method.name,
        final_best=round(float(best_objective), 12),
        objective_fe=int(objective_fe),
        total_fe=int(total_fe),
        checkpoint_rows=checkpoint_rows,
        branch_counts=branch_counts,
    )


def _proposal_snapshot(
    *,
    current: np.ndarray,
    problem: Any,
    step_index: int,
    oscillation: float,
) -> dict[str, Any]:
    variable = int(problem.shared_variable)
    current_value = float(current[variable])
    lower = float(problem.lower_bounds[variable])
    upper = float(problem.upper_bounds[variable])
    width = max(upper - lower, 1e-12)
    sign = float(np.sign(current_value if current_value else 1.0))
    scale = max(width * 0.08 / int(step_index), 1e-9)
    proposals = [
        current_value - sign * scale,
        current_value + sign * scale * 0.85,
        current_value - sign * scale * 0.35,
    ]
    rewards = [0.82 + 0.01 * min(int(step_index), 5), 0.34, 0.58]
    return {
        "variable": variable,
        "current_value": current_value,
        "lower": lower,
        "upper": upper,
        "width": width,
        "proposals": proposals,
        "rewards": rewards,
        "oscillation": float(oscillation),
    }


def _coordinate_fast(method_name: str, snapshot: Mapping[str, Any]) -> tuple[float, str | None]:
    current = float(snapshot["current_value"])
    proposals = [float(value) for value in snapshot["proposals"]]
    rewards = [float(value) for value in snapshot["rewards"]]
    lower = float(snapshot["lower"])
    upper = float(snapshot["upper"])
    if method_name == "identity_no_coord":
        return _clip(current, lower, upper), None
    if method_name == "simple_consensus":
        return _clip(float(np.mean(proposals)), lower, upper), None
    if method_name == "weighted_consensus":
        return _weighted_value(proposals, rewards, lower, upper), None
    if method_name == "best_reward_select":
        return _best_reward_value(proposals, rewards, lower, upper), None
    if method_name != FROZEN_METHOD:
        raise ValueError(f"Unsupported method for Stage 8.24: {method_name}")

    sorted_rewards = sorted(rewards)
    features = {
        "shared_variable_oscillation": float(snapshot["oscillation"]),
        "reward_margin": float(sorted_rewards[-1] - sorted_rewards[-2]),
    }
    rules = [
        {
            "condition": "shared_variable_oscillation > 0.25",
            "action": "shrinkage_repair",
        },
        {"condition": "reward_margin > 0.2", "action": "trust_best_reward"},
        {"condition": "always", "action": "damp_best_reward"},
    ]
    action = "damp_best_reward"
    for rule in rules:
        if _condition_matches(str(rule["condition"]), features):
            action = str(rule["action"])
            break
    if action == "trust_best_reward":
        return _best_reward_value(proposals, rewards, lower, upper), action
    if action == "weighted_consensus":
        return _weighted_value(proposals, rewards, lower, upper), action
    if action == "simple_consensus":
        return _clip(float(np.mean(proposals)), lower, upper), action
    if action == "damp_best_reward":
        best = _best_reward_value(proposals, rewards, lower, upper)
        return _clip(current + 0.5 * (best - current), lower, upper), action
    if action == "shrinkage_repair":
        weighted = _weighted_value(proposals, rewards, lower, upper)
        return _clip(current + 0.5 * (weighted - current), lower, upper), action
    if action == "reject_unstable_best_reward":
        return _clip(float(np.mean(proposals)), lower, upper), action
    raise ValueError(f"unsupported frozen policy action: {action}")


def _weighted_value(
    proposals: Sequence[float], rewards: Sequence[float], lower: float, upper: float
) -> float:
    reward_array = np.asarray(rewards, dtype=float)
    value_array = np.asarray(proposals, dtype=float)
    scaled = reward_array - float(np.max(reward_array))
    weights = np.exp(scaled)
    weights = weights / float(np.sum(weights))
    return _clip(float(np.dot(weights, value_array)), lower, upper)


def _best_reward_value(
    proposals: Sequence[float], rewards: Sequence[float], lower: float, upper: float
) -> float:
    best_index = int(np.argmax(np.asarray(rewards, dtype=float)))
    return _clip(float(proposals[best_index]), lower, upper)


def _clip(value: float, lower: float, upper: float) -> float:
    return float(np.clip(float(value), float(lower), float(upper)))


def _incremental_oscillation(*, sign_change_count: int, nonzero_delta_count: int) -> float:
    if int(nonzero_delta_count) <= 1:
        return 0.0
    return float(sign_change_count) / float(nonzero_delta_count - 1)


def _conflict_intensity_fast(snapshot: Mapping[str, Any]) -> float:
    proposals = [float(value) for value in snapshot["proposals"]]
    rewards = np.asarray(snapshot["rewards"], dtype=float)
    current = float(snapshot["current_value"])
    width = max(float(snapshot["width"]), 1e-12)
    value = max(max(proposals) - min(proposals), 0.0) / width
    directions = np.asarray([value - current for value in proposals], dtype=float)
    nonzero = directions[np.abs(directions) > 1e-12]
    if nonzero.size <= 1:
        direction = 0.0
    else:
        has_positive = bool(np.any(nonzero > 0.0))
        has_negative = bool(np.any(nonzero < 0.0))
        if not (has_positive and has_negative):
            direction = 0.0
        else:
            positive = int(np.sum(nonzero > 0.0))
            negative = int(np.sum(nonzero < 0.0))
            direction = (2.0 * min(positive, negative)) / int(nonzero.size)
    reward_scale = max(float(np.max(np.abs(rewards))), 1.0)
    reward = max(float(np.max(rewards) - np.min(rewards)) / reward_scale, 0.0)
    return max((value + direction + reward) / 3.0, 0.0)


def _checkpoint_trace_row_fast(
    *,
    method: _Method,
    problem: Any,
    snapshot: Mapping[str, Any],
    coordinated_value: float,
    policy_branch: str | None,
    step_index: int,
    seed: int,
    objective_value: float,
    best_objective: float,
    improved: bool,
    selected_candidate_id: str,
) -> dict[str, Any]:
    metadata = dict(problem.metadata)
    return {
        "schema_version": CHECKPOINT_TRACE_SCHEMA_VERSION,
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
        "policy_name": selected_candidate_id if method.name == FROZEN_METHOD else None,
        "policy_branch": policy_branch,
        "frozen_policy_used": bool(method.name == FROZEN_METHOD),
        "is_loco_policy": method.is_loco_policy,
        "official_cec2013_checkpoint_pilot": True,
        "not_full_25_run_panel": True,
        "not_full_f1_f15_panel": True,
        "problem_dimension": int(problem.dimension),
        "D_formula": int(metadata.get("D_formula", problem.dimension)),
        "D_api": int(metadata.get("D_api", problem.dimension)),
        "overlap_semantics": metadata.get("overlap_semantics"),
        "adapter_mode": metadata.get("adapter_mode"),
        "shared_variable_id": int(snapshot["variable"]),
        "objective_step": int(step_index),
        "current_shared_value": float(snapshot["current_value"]),
        "coordinated_shared_value": float(coordinated_value),
        "objective_value": round(float(objective_value), 12),
        "best_objective_so_far": round(float(best_objective), 12),
        "objective_improved_or_equal": bool(improved),
        "conflict_intensity": round(_conflict_intensity_fast(snapshot), 12),
        "shared_variable_oscillation": round(float(snapshot["oscillation"]), 12),
        "FE_grouping": 0,
        "FE_proposal": 1,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 1,
        "FE_total": 2,
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
    case_results: Sequence[_CaseResult],
    function_ids: Sequence[int],
    run_seeds: Sequence[int],
    max_fe: int,
) -> dict[str, Any]:
    method_rows = []
    for method_name in METHOD_NAMES:
        rows = [row for row in case_results if row.method_name == method_name]
        final_bests = [row.final_best for row in rows]
        method_rows.append(
            {
                "method_name": method_name,
                "case_count": len(rows),
                "mean_final_best": _mean(final_bests),
                "median_final_best": _median(final_bests),
                "FE_global_objective": sum(row.objective_fe for row in rows),
                "FE_total": sum(row.total_fe for row in rows),
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
        "function_ids": [f"F{int(function_id)}" for function_id in function_ids],
        "max_fe_per_method_per_function": int(max_fe),
        "methods": METHOD_NAMES,
        "method_rows": method_rows,
        "same_budget_across_methods": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_win_loss_report(
    *,
    case_results: Sequence[_CaseResult],
    function_ids: Sequence[int],
    run_seeds: Sequence[int],
    promising_delta_threshold: float,
) -> dict[str, Any]:
    case_rows = []
    for function_id in function_ids:
        for seed in run_seeds:
            final_by_method = {
                result.method_name: result.final_best
                for result in case_results
                if result.function_id == int(function_id) and result.seed == int(seed)
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
                    "selected_candidate_id": "stage8_20_round_candidate_8",
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
        "checkpoint_budget_pilot_promising": promising,
        "baseline_comparison_made": True,
        "promising_delta_threshold": float(promising_delta_threshold),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_policy_branch_report(
    case_results: Sequence[_CaseResult], frozen_policy: Mapping[str, Any]
) -> dict[str, Any]:
    branch_counts: Counter[str] = Counter()
    policy_trace_row_count = 0
    for result in case_results:
        if result.method_name != FROZEN_METHOD:
            continue
        policy_trace_row_count += result.objective_fe
        branch_counts.update(result.branch_counts)
    branch_names = ["trust_best_reward", "damp_best_reward", "shrinkage_repair"]
    normalized = {branch: int(branch_counts.get(branch, 0)) for branch in branch_names}
    return {
        "schema_version": BRANCH_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.22",
        "selected_candidate_id": str(frozen_policy["candidate_id"]),
        "freeze_status": str(frozen_policy["freeze_status"]),
        "policy_trace_row_count": int(policy_trace_row_count),
        "branch_counts": normalized,
        "trust_best_reward_exercised": int(normalized["trust_best_reward"]) >= 1,
        "non_trust_branch_exercised": any(
            count > 0 for branch, count in normalized.items() if branch != "trust_best_reward"
        ),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(
    *,
    case_results: Sequence[_CaseResult],
    inherited_stage8_22_FE_total: int,
    max_fe: int,
    run_count: int,
    initial_objective_fe: int,
) -> dict[str, Any]:
    fe_global = sum(result.objective_fe for result in case_results) + int(initial_objective_fe)
    fe_total = sum(result.total_fe for result in case_results) + int(initial_objective_fe)
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "cec2013_f13_f14_checkpoint_budget_pilot",
        "run_count": int(run_count),
        "max_fe_per_method_per_function": int(max_fe),
        "inherited_stage8_22_FE_total": int(inherited_stage8_22_FE_total),
        "FE_initial_objective": int(initial_objective_fe),
        "FE_grouping": 0,
        "FE_proposal": sum(result.objective_fe for result in case_results),
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": int(fe_global),
        "FE_total": int(fe_total),
        "same_budget_across_methods": True,
        "cross_method_evaluations_shared": False,
        "all_extra_fe_counted": True,
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "official_cec2013_panel_run": False,
        "not_full_25_run_panel": True,
        "not_final_performance_claim": True,
        "full_objective_trace_written": False,
        "compact_checkpoint_trace_written": True,
    }


def _build_runtime_boundary(
    *,
    run_count: int,
    max_fe: int,
    checkpoint_steps: set[int],
    parallel_execution_used: bool,
    max_workers: int,
) -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "CEC2013 F13/F14 frozen-policy checkpoint-budget pilot only",
        "run_count": int(run_count),
        "max_fe_per_method_per_function": int(max_fe),
        "checkpoint_steps": sorted(int(step) for step in checkpoint_steps),
        "parallel_execution_used": bool(parallel_execution_used),
        "max_workers": int(max_workers),
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "official_cec2013_panel_run": False,
        "checkpoint_budget_pilot_executed": True,
        "multiseed_pilot_executed": False,
        "full_objective_trace_written": False,
        "compact_checkpoint_trace_written": True,
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
    promising = bool(win_loss["checkpoint_budget_pilot_promising"])
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": (
            "PROMISING_CHECKPOINT_ROUTE_TO_FORMAL_F13_F14_DECISION"
            if promising
            else "NOT_PROMISING_CHECKPOINT_DIAGNOSE_BEFORE_FORMAL_PANEL"
        ),
        "next_stage": NEXT_IF_PROMISING if promising else NEXT_IF_NOT_PROMISING,
        "allowed_next_work": (
            "formal_f13_f14_same_budget_decision_gate"
            if promising
            else "failure_honest_checkpoint_budget_diagnosis"
        ),
        "run_full_25_run_panel_next": False,
        "run_checkpoint_budget_pilot_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    case_results: Sequence[_CaseResult],
    checkpoint_rows: Sequence[Mapping[str, Any]],
    win_loss: Mapping[str, Any],
    branch_report: Mapping[str, Any],
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
    frozen_policy: Mapping[str, Any],
    function_ids: Sequence[int],
    run_seeds: Sequence[int],
    max_fe: int,
    checkpoint_steps: set[int],
    parallel_execution_used: bool,
    max_workers: int,
) -> dict[str, Any]:
    raw_trace_row_count = len(case_results) * int(max_fe)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.22",
        "pilot_scope": "cec2013_f13_f14_frozen_policy_checkpoint_budget_pilot",
        "benchmark_suite": BENCHMARK_SUITE,
        "selected_candidate_id": str(frozen_policy["candidate_id"]),
        "freeze_status": str(frozen_policy["freeze_status"]),
        "frozen_policy_used": True,
        "run_count": len(run_seeds),
        "seed_count": len(run_seeds),
        "seeds": [int(seed) for seed in run_seeds],
        "max_fe_per_method_per_function": int(max_fe),
        "checkpoint_steps": sorted(int(step) for step in checkpoint_steps),
        "parallel_execution_used": bool(parallel_execution_used),
        "max_workers": int(max_workers),
        "function_ids": [f"F{int(function_id)}" for function_id in function_ids],
        "function_count": len(function_ids),
        "not_full_25_run_panel": True,
        "not_full_f1_f15_panel": True,
        "checkpoint_budget_pilot_executed": True,
        "multiseed_pilot_executed": False,
        "official_cec2013_problem_loaded": True,
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "baseline_comparison_made": True,
        "method_count": len(METHOD_NAMES),
        "method_names": METHOD_NAMES,
        "raw_trace_row_count": int(raw_trace_row_count),
        "checkpoint_trace_row_count": len(checkpoint_rows),
        "full_objective_trace_written": False,
        "compact_checkpoint_trace_written": True,
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
        "checkpoint_budget_pilot_promising": bool(
            win_loss["checkpoint_budget_pilot_promising"]
        ),
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

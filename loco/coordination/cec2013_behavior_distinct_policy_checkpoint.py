"""Stage 8.30 CEC2013 F13/F14 checkpoint for the Stage 8.29 policy."""

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
from loco.coordination.cec2013_single_run_smoke_decision import (
    BENCHMARK_SUITE,
    SMOKE_FUNCTION_IDS,
    _evaluate,
    _initial_vector,
    _load_smoke_problem,
)


STAGE = "8.30"
REPORT_SCHEMA_VERSION = "loco.stage8_30_checkpoint_pilot_report.v1"
CHECKPOINT_TRACE_SCHEMA_VERSION = "loco.stage8_30_checkpoint_trace.v1"
METHOD_SUMMARY_SCHEMA_VERSION = "loco.stage8_30_method_summary.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_30_win_loss_report.v1"
BRANCH_SCHEMA_VERSION = "loco.stage8_30_policy_branch_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_30_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_30_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_30_next_route_decision.v1"

BEHAVIOR_METHOD = "stage8_29_behavior_distinct_policy"
BASELINE_METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
]
METHOD_NAMES = [*BASELINE_METHOD_NAMES, BEHAVIOR_METHOD]
DEFAULT_RUN_SEEDS = [0, 1, 2]
DEFAULT_CHECKPOINT_MAX_FE = 1200


@dataclass(frozen=True)
class _Method:
    name: str
    label: str
    is_loco_policy: bool


@dataclass(frozen=True)
class _CaseResult:
    function_id: int
    seed: int
    method_name: str
    final_best: float
    objective_fe: int
    total_fe: int
    checkpoint_rows: list[dict[str, Any]]
    action_counts: Counter[str]
    owner_counts: Counter[str]
    linkage_counts: Counter[str]


def run_stage8_30_cec2013_behavior_distinct_policy_checkpoint(
    *,
    stage8_29_frozen_policy_path: Path | str,
    stage8_29_frozen_strategy_payload_path: Path | str,
    stage8_29_manifest_path: Path | str,
    stage8_29_readiness_protocol_path: Path | str,
    stage8_29_fe_ledger_path: Path | str,
    stage8_29_runtime_boundary_path: Path | str,
    stage8_29_next_route_path: Path | str,
    output_dir: Path | str,
    problem_loader: Callable[[int], Any] | None = None,
    function_ids: Sequence[int] = SMOKE_FUNCTION_IDS,
    run_seeds: Sequence[int] = DEFAULT_RUN_SEEDS,
    max_fe_per_method_per_function: int = DEFAULT_CHECKPOINT_MAX_FE,
    checkpoint_steps: Sequence[int] | None = None,
    max_workers: int | None = None,
    promising_delta_threshold: float = 0.0,
) -> dict[str, Any]:
    """Run the frozen behavior-distinct policy on CEC2013 F13/F14."""

    frozen_policy = _read_json(Path(stage8_29_frozen_policy_path))
    strategy_payload = _read_json(Path(stage8_29_frozen_strategy_payload_path))
    manifest = _read_json(Path(stage8_29_manifest_path))
    readiness = _read_json(Path(stage8_29_readiness_protocol_path))
    stage8_29_ledger = _read_json(Path(stage8_29_fe_ledger_path))
    stage8_29_boundary = _read_json(Path(stage8_29_runtime_boundary_path))
    stage8_29_route = _read_json(Path(stage8_29_next_route_path))
    _validate_inputs(
        frozen_policy=frozen_policy,
        strategy_payload=strategy_payload,
        manifest=manifest,
        readiness=readiness,
        stage8_29_ledger=stage8_29_ledger,
        stage8_29_boundary=stage8_29_boundary,
        stage8_29_route=stage8_29_route,
        function_ids=function_ids,
        run_seeds=run_seeds,
        max_fe=int(max_fe_per_method_per_function),
    )

    checkpoint_step_set = _checkpoint_step_set(
        max_fe=int(max_fe_per_method_per_function),
        checkpoint_steps=checkpoint_steps,
    )
    methods = _build_methods()
    worker_count = _worker_count(max_workers, methods, function_ids, run_seeds)
    use_parallel = problem_loader is None and worker_count > 1
    case_results = (
        _run_cases_parallel(
            function_ids=function_ids,
            run_seeds=run_seeds,
            method_names=[method.name for method in methods],
            max_fe=int(max_fe_per_method_per_function),
            checkpoint_steps=checkpoint_step_set,
            strategy_payload=strategy_payload,
            max_workers=worker_count,
        )
        if use_parallel
        else _run_cases_serial(
            loader=problem_loader or load_cec2013lsgo_problem,
            function_ids=function_ids,
            run_seeds=run_seeds,
            methods=methods,
            max_fe=int(max_fe_per_method_per_function),
            checkpoint_steps=checkpoint_step_set,
            strategy_payload=strategy_payload,
        )
    )
    checkpoint_rows = [
        checkpoint for result in case_results for checkpoint in result.checkpoint_rows
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
        strategy_id=str(strategy_payload["strategy_id"]),
        promising_delta_threshold=float(promising_delta_threshold),
    )
    branch_report = _build_policy_branch_report(case_results, strategy_payload)
    initial_objective_fe = len(function_ids) * len(run_seeds) * len(methods)
    ledger = _build_fe_ledger(
        case_results=case_results,
        inherited_stage8_29_fe_total=int(stage8_29_ledger["FE_total"]),
        max_fe=int(max_fe_per_method_per_function),
        run_count=len(run_seeds),
        initial_objective_fe=initial_objective_fe,
    )
    boundary = _build_runtime_boundary(
        run_count=len(run_seeds),
        max_fe=int(max_fe_per_method_per_function),
        checkpoint_steps=checkpoint_step_set,
        parallel_execution_used=use_parallel,
        max_workers=worker_count if use_parallel else 1,
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
        strategy_payload=strategy_payload,
        function_ids=function_ids,
        run_seeds=run_seeds,
        max_fe=int(max_fe_per_method_per_function),
        checkpoint_steps=checkpoint_step_set,
        parallel_execution_used=use_parallel,
        max_workers=worker_count if use_parallel else 1,
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
    strategy_payload: Mapping[str, Any],
    manifest: Mapping[str, Any],
    readiness: Mapping[str, Any],
    stage8_29_ledger: Mapping[str, Any],
    stage8_29_boundary: Mapping[str, Any],
    stage8_29_route: Mapping[str, Any],
    function_ids: Sequence[int],
    run_seeds: Sequence[int],
    max_fe: int,
) -> None:
    if frozen_policy.get("stage") != "8.29":
        raise ValueError("Stage 8.30 requires a Stage 8.29 frozen policy.")
    if (
        frozen_policy.get("frozen_policy_status")
        != "FROZEN_FOR_CEC2013_F13_F14_CHECKPOINT_NOT_FINAL"
    ):
        raise ValueError("Stage 8.30 requires the Stage 8.29 checkpoint freeze.")
    if strategy_payload.get("strategy_id") != frozen_policy.get("strategy_id"):
        raise ValueError("Frozen policy metadata and strategy payload mismatch.")
    if manifest.get("frozen_strategy_payload_matches_stage8_27") is not True:
        raise ValueError("Stage 8.30 requires exact Stage 8.27 strategy freeze.")
    if readiness.get("status") != "READY_FOR_STAGE8_30_CEC2013_F13_F14_CHECKPOINT":
        raise ValueError("Stage 8.30 requires the Stage 8.29 readiness protocol.")
    if int(stage8_29_ledger.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.30 requires zero-FE Stage 8.29 freeze input.")
    if stage8_29_boundary.get("objective_loop_executed") is not False:
        raise ValueError("Stage 8.29 must not have executed objective loops.")
    if stage8_29_route.get("next_stage") != "Stage 8.30":
        raise ValueError("Stage 8.30 requires the Stage 8.29 route anchor.")
    if set(map(int, function_ids)) != {13, 14}:
        raise ValueError("Stage 8.30 is limited to CEC2013 F13/F14.")
    if len(list(run_seeds)) < 2:
        raise ValueError("Stage 8.30 requires multiple seeds.")
    if int(max_fe) <= 0:
        raise ValueError("max_fe_per_method_per_function must be positive.")


def _checkpoint_step_set(*, max_fe: int, checkpoint_steps: Sequence[int] | None) -> set[int]:
    candidates = (
        [1, 120, 600, int(max_fe)]
        if checkpoint_steps is None
        else [int(step) for step in checkpoint_steps]
    )
    steps = {step for step in candidates if 1 <= step <= int(max_fe)}
    steps.add(int(max_fe))
    return steps


def _build_methods() -> list[_Method]:
    return [
        _Method("identity_no_coord", "NoCoordination", False),
        _Method("simple_consensus", "AverageConsensus", False),
        _Method("weighted_consensus", "WeightedConsensus", False),
        _Method("best_reward_select", "BestRewardSelection", False),
        _Method(BEHAVIOR_METHOD, "Stage829BehaviorDistinctPolicy", True),
    ]


def _run_cases_serial(
    *,
    loader: Callable[[int], Any],
    function_ids: Sequence[int],
    run_seeds: Sequence[int],
    methods: Sequence[_Method],
    max_fe: int,
    checkpoint_steps: set[int],
    strategy_payload: Mapping[str, Any],
) -> list[_CaseResult]:
    results: list[_CaseResult] = []
    for function_id in function_ids:
        problem = _load_smoke_problem(loader, int(function_id))
        for seed in run_seeds:
            for method in methods:
                results.append(
                    _run_method_loop(
                        method=method,
                        problem=problem,
                        seed=int(seed),
                        max_fe=int(max_fe),
                        checkpoint_steps=checkpoint_steps,
                        strategy_payload=strategy_payload,
                    )
                )
    return results


def _run_cases_parallel(
    *,
    function_ids: Sequence[int],
    run_seeds: Sequence[int],
    method_names: Sequence[str],
    max_fe: int,
    checkpoint_steps: set[int],
    strategy_payload: Mapping[str, Any],
    max_workers: int,
) -> list[_CaseResult]:
    tasks = [
        (
            int(function_id),
            int(seed),
            str(method_name),
            int(max_fe),
            tuple(sorted(checkpoint_steps)),
            dict(strategy_payload),
        )
        for function_id in function_ids
        for seed in run_seeds
        for method_name in method_names
    ]
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_run_case_worker, tasks))


def _run_case_worker(
    task: tuple[int, int, str, int, tuple[int, ...], dict[str, Any]]
) -> _CaseResult:
    function_id, seed, method_name, max_fe, checkpoint_steps, strategy_payload = task
    problem = _load_smoke_problem(load_cec2013lsgo_problem, int(function_id))
    return _run_method_loop(
        method=_method_by_name(str(method_name)),
        problem=problem,
        seed=int(seed),
        max_fe=int(max_fe),
        checkpoint_steps=set(int(step) for step in checkpoint_steps),
        strategy_payload=strategy_payload,
    )


def _method_by_name(method_name: str) -> _Method:
    for method in _build_methods():
        if method.name == method_name:
            return method
    raise ValueError(f"Unknown Stage 8.30 method: {method_name}")


def _worker_count(
    max_workers: int | None,
    methods: Sequence[Any],
    function_ids: Sequence[int],
    run_seeds: Sequence[int],
) -> int:
    task_count = len(list(function_ids)) * len(list(run_seeds)) * len(list(methods))
    requested = int(max_workers) if max_workers is not None else min(os.cpu_count() or 1, task_count, 8)
    return max(1, min(requested, task_count))


def _run_method_loop(
    *,
    method: _Method,
    problem: Any,
    seed: int,
    max_fe: int,
    checkpoint_steps: set[int],
    strategy_payload: Mapping[str, Any],
) -> _CaseResult:
    current = _initial_vector(problem, seed)
    best_objective = _evaluate(problem.problem, current)
    checkpoint_rows: list[dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    owner_counts: Counter[str] = Counter()
    linkage_counts: Counter[str] = Counter()
    objective_fe = 0
    total_fe = 0
    last_value: float | None = None
    last_delta_sign = 0.0
    sign_change_count = 0
    nonzero_delta_count = 0

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
        coordinated_value, decision = _coordinate(method.name, snapshot, strategy_payload)
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
            if last_value is not None:
                delta = float(coordinated_value - last_value)
                if abs(delta) > 1e-12:
                    sign = float(np.sign(delta))
                    if last_delta_sign and sign != last_delta_sign:
                        sign_change_count += 1
                    last_delta_sign = sign
                    nonzero_delta_count += 1
            last_value = float(coordinated_value)

        if method.name == BEHAVIOR_METHOD and decision is not None:
            action_counts[str(decision["coordination_action"])] += 1
            owner_counts[str(decision["shared_variable_owner"])] += 1
            linkage_counts[str(decision["linkage_decision"])] += 1

        if step_index in checkpoint_steps:
            checkpoint_rows.append(
                _checkpoint_trace_row(
                    method=method,
                    problem=problem,
                    snapshot=snapshot,
                    coordinated_value=coordinated_value,
                    decision=decision,
                    step_index=step_index,
                    seed=seed,
                    objective_value=objective_value,
                    best_objective=best_objective,
                    improved=improved,
                    strategy_id=str(strategy_payload["strategy_id"]),
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
        action_counts=action_counts,
        owner_counts=owner_counts,
        linkage_counts=linkage_counts,
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
    metadata = dict(problem.metadata)
    conflicting = metadata.get("overlap_semantics") == "conflicting_overlap"
    contribution_scores = [0.25, 0.95, 0.10] if conflicting else [0.76, 0.77, 0.75]
    return {
        "variable": variable,
        "current_value": current_value,
        "lower": lower,
        "upper": upper,
        "width": width,
        "proposals": proposals,
        "rewards": rewards,
        "contribution_scores": contribution_scores,
        "historical_owner_group_id": 2,
        "overlap_semantics": metadata.get("overlap_semantics"),
        "oscillation": float(oscillation),
    }


def _coordinate(
    method_name: str, snapshot: Mapping[str, Any], strategy_payload: Mapping[str, Any]
) -> tuple[float, dict[str, Any] | None]:
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
    if method_name != BEHAVIOR_METHOD:
        raise ValueError(f"Unsupported method for Stage 8.30: {method_name}")

    rule = _select_strategy_rule(strategy_payload, snapshot)
    action = str(rule["coordination_action"])
    if not _condition_matches(str(rule["condition"]), _features(snapshot)):
        action = str(rule["fallback_repair_action"])
    value = _apply_action(action, rule, snapshot)
    decision = {
        "condition": str(rule["condition"]),
        "shared_variable_owner": str(rule["shared_variable_owner"]),
        "allow_multi_assignment": bool(rule.get("allow_multi_assignment", False)),
        "linkage_decision": str(rule["linkage_decision"]),
        "coordination_action": action,
        "fallback_repair_action": str(rule["fallback_repair_action"]),
    }
    return value, decision


def _select_strategy_rule(
    strategy_payload: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> Mapping[str, Any]:
    rules = list(strategy_payload.get("rules", []))
    if not rules:
        raise ValueError("Stage 8.30 strategy payload has no rules.")
    features = _features(snapshot)
    for rule in rules:
        if _condition_matches(str(rule["condition"]), features):
            return rule
    return rules[-1]


def _features(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    rewards = [float(value) for value in snapshot["rewards"]]
    contributions = [float(value) for value in snapshot["contribution_scores"]]
    return {
        "always": True,
        "conflicting_overlap": snapshot.get("overlap_semantics") == "conflicting_overlap",
        "conforming_overlap": snapshot.get("overlap_semantics") == "conforming_overlap",
        "high_owner_regret": int(np.argmax(rewards)) != int(np.argmax(contributions)),
        "low_owner_confidence": max(contributions) < 0.5,
        "unstable_best_reward": float(snapshot["oscillation"]) > 0.25,
    }


def _condition_matches(condition: str, features: Mapping[str, Any]) -> bool:
    normalized = " ".join(condition.strip().split())
    if not normalized:
        return False
    if normalized.lower() == "always":
        return True
    return any(
        all(bool(features.get(part.strip(), False)) for part in or_part.split(" AND "))
        for or_part in normalized.split(" OR ")
    )


def _apply_action(
    action: str, rule: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> float:
    current = float(snapshot["current_value"])
    proposals = [float(value) for value in snapshot["proposals"]]
    rewards = [float(value) for value in snapshot["rewards"]]
    lower = float(snapshot["lower"])
    upper = float(snapshot["upper"])
    if action == "trust_best_reward":
        value = _best_reward_value(proposals, rewards, lower, upper)
    elif action == "weighted_consensus":
        value = _weighted_value(proposals, rewards, lower, upper)
    elif action == "simple_consensus":
        value = float(np.mean(proposals))
    elif action == "damp_best_reward":
        best = _best_reward_value(proposals, rewards, lower, upper)
        value = current + 0.5 * (best - current)
    elif action == "shrinkage_repair":
        weighted = _weighted_value(proposals, rewards, lower, upper)
        value = current + 0.5 * (weighted - current)
    elif action == "reject_unstable_best_reward":
        value = _apply_action(str(rule["fallback_repair_action"]), rule, snapshot)
    elif action == "owner_proposal_select":
        value = _owner_proposal_value(str(rule["shared_variable_owner"]), snapshot)
    elif action == "multi_owner_weighted_vote":
        value = _multi_owner_weighted_vote(snapshot)
    else:
        raise ValueError(f"Unsupported Stage 8.30 coordination_action: {action}")
    return _clip(float(value), lower, upper)


def _owner_proposal_value(owner: str, snapshot: Mapping[str, Any]) -> float:
    proposals = [float(value) for value in snapshot["proposals"]]
    rewards = [float(value) for value in snapshot["rewards"]]
    contributions = [float(value) for value in snapshot["contribution_scores"]]
    if owner == "contribution_leader":
        index = int(np.argmax(contributions))
    elif owner == "historical_owner":
        index = max(0, min(int(snapshot["historical_owner_group_id"]) - 1, len(proposals) - 1))
    elif owner == "best_reward_group":
        index = int(np.argmax(rewards))
    else:
        return _multi_owner_weighted_vote(snapshot)
    return float(proposals[index])


def _multi_owner_weighted_vote(snapshot: Mapping[str, Any]) -> float:
    rewards = np.asarray(snapshot["rewards"], dtype=float)
    contributions = np.asarray(snapshot["contribution_scores"], dtype=float)
    proposals = np.asarray(snapshot["proposals"], dtype=float)
    weights = np.maximum(rewards, 0.0) + np.maximum(contributions, 0.0)
    if float(np.sum(weights)) <= 1e-12:
        return float(np.mean(proposals))
    return float(np.dot(weights / float(np.sum(weights)), proposals))


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
    return _clip(float(proposals[int(np.argmax(np.asarray(rewards, dtype=float)))]), lower, upper)


def _clip(value: float, lower: float, upper: float) -> float:
    return float(np.clip(float(value), float(lower), float(upper)))


def _incremental_oscillation(*, sign_change_count: int, nonzero_delta_count: int) -> float:
    if int(nonzero_delta_count) <= 1:
        return 0.0
    return float(sign_change_count) / float(nonzero_delta_count - 1)


def _conflict_intensity(snapshot: Mapping[str, Any]) -> float:
    proposals = [float(value) for value in snapshot["proposals"]]
    rewards = np.asarray(snapshot["rewards"], dtype=float)
    width = max(float(snapshot["width"]), 1e-12)
    value_spread = max(max(proposals) - min(proposals), 0.0) / width
    reward_scale = max(float(np.max(np.abs(rewards))), 1.0)
    reward_spread = max(float(np.max(rewards) - np.min(rewards)) / reward_scale, 0.0)
    return max((value_spread + reward_spread) / 2.0, 0.0)


def _checkpoint_trace_row(
    *,
    method: _Method,
    problem: Any,
    snapshot: Mapping[str, Any],
    coordinated_value: float,
    decision: Mapping[str, Any] | None,
    step_index: int,
    seed: int,
    objective_value: float,
    best_objective: float,
    improved: bool,
    strategy_id: str,
) -> dict[str, Any]:
    metadata = dict(problem.metadata)
    return {
        "schema_version": CHECKPOINT_TRACE_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "8.29",
        "benchmark_suite": BENCHMARK_SUITE,
        "function_id": f"F{problem.function_id}",
        "function_index": int(problem.function_id),
        "run_index": int(seed) + 1,
        "seed": int(seed),
        "method_name": method.name,
        "operator_label": method.label,
        "selected_strategy_id": strategy_id if method.name == BEHAVIOR_METHOD else None,
        "policy_name": strategy_id if method.name == BEHAVIOR_METHOD else None,
        "policy_branch": decision.get("coordination_action") if decision else None,
        "shared_variable_owner": decision.get("shared_variable_owner") if decision else None,
        "linkage_decision": decision.get("linkage_decision") if decision else None,
        "frozen_behavior_distinct_policy_used": bool(method.name == BEHAVIOR_METHOD),
        "is_loco_policy": method.is_loco_policy,
        "official_cec2013_checkpoint": True,
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
        "conflict_intensity": round(_conflict_intensity(snapshot), 12),
        "shared_variable_oscillation": round(float(snapshot["oscillation"]), 12),
        "FE_grouping": 0,
        "FE_proposal": 1,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 1,
        "FE_total": 2,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "new_llm_strategy_generation_used": False,
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
    rows = []
    for method_name in METHOD_NAMES:
        method_results = [row for row in case_results if row.method_name == method_name]
        final_bests = [row.final_best for row in method_results]
        rows.append(
            {
                "method_name": method_name,
                "case_count": len(method_results),
                "mean_final_best": _mean(final_bests),
                "median_final_best": _median(final_bests),
                "FE_global_objective": sum(row.objective_fe for row in method_results),
                "FE_total": sum(row.total_fe for row in method_results),
            }
        )
    return {
        "schema_version": METHOD_SUMMARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.29",
        "benchmark_suite": BENCHMARK_SUITE,
        "run_count": len(run_seeds),
        "seeds": [int(seed) for seed in run_seeds],
        "function_ids": [f"F{int(function_id)}" for function_id in function_ids],
        "max_fe_per_method_per_function": int(max_fe),
        "methods": METHOD_NAMES,
        "method_rows": rows,
        "same_budget_across_methods": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_win_loss_report(
    *,
    case_results: Sequence[_CaseResult],
    function_ids: Sequence[int],
    run_seeds: Sequence[int],
    strategy_id: str,
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
            policy_final = final_by_method[BEHAVIOR_METHOD]
            best_reward_final = final_by_method["best_reward_select"]
            best_baseline_method = min(
                BASELINE_METHOD_NAMES, key=lambda name: final_by_method[name]
            )
            best_baseline_final = final_by_method[best_baseline_method]
            case_rows.append(
                {
                    "function_id": f"F{int(function_id)}",
                    "seed": int(seed),
                    "selected_strategy_id": strategy_id,
                    "behavior_policy_final_best": policy_final,
                    "best_reward_select_final_best": best_reward_final,
                    "best_baseline_method": best_baseline_method,
                    "best_baseline_final_best": best_baseline_final,
                    "behavior_vs_best_reward_select_delta": round(
                        policy_final - best_reward_final, 12
                    ),
                    "behavior_vs_best_baseline_delta": round(
                        policy_final - best_baseline_final, 12
                    ),
                    "behavior_vs_best_reward_select_result": _comparison_result(
                        policy_final - best_reward_final,
                        promising_delta_threshold,
                    ),
                    "behavior_vs_best_baseline_result": _comparison_result(
                        policy_final - best_baseline_final,
                        promising_delta_threshold,
                    ),
                }
            )
    vs_best_reward = _count_results(
        row["behavior_vs_best_reward_select_result"] for row in case_rows
    )
    vs_best_baseline = _count_results(
        row["behavior_vs_best_baseline_result"] for row in case_rows
    )
    return {
        "schema_version": WIN_LOSS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.29",
        "benchmark_suite": BENCHMARK_SUITE,
        "run_count": len(run_seeds),
        "comparison_case_count": len(case_rows),
        "case_rows": case_rows,
        "behavior_policy_vs_best_reward_select": vs_best_reward,
        "behavior_policy_vs_best_baseline": vs_best_baseline,
        "checkpoint_promising": int(vs_best_reward["loss"]) == 0,
        "baseline_comparison_made": True,
        "promising_delta_threshold": float(promising_delta_threshold),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_policy_branch_report(
    case_results: Sequence[_CaseResult], strategy_payload: Mapping[str, Any]
) -> dict[str, Any]:
    action_counts: Counter[str] = Counter()
    owner_counts: Counter[str] = Counter()
    linkage_counts: Counter[str] = Counter()
    policy_trace_row_count = 0
    for result in case_results:
        if result.method_name != BEHAVIOR_METHOD:
            continue
        policy_trace_row_count += result.objective_fe
        action_counts.update(result.action_counts)
        owner_counts.update(result.owner_counts)
        linkage_counts.update(result.linkage_counts)
    action_names = [
        "trust_best_reward",
        "damp_best_reward",
        "weighted_consensus",
        "simple_consensus",
        "shrinkage_repair",
        "reject_unstable_best_reward",
        "owner_proposal_select",
        "multi_owner_weighted_vote",
    ]
    owner_names = ["best_reward_group", "contribution_leader", "multi_owner", "historical_owner"]
    linkage_names = ["preserve", "break"]
    action_dict = {name: int(action_counts.get(name, 0)) for name in action_names}
    owner_dict = {name: int(owner_counts.get(name, 0)) for name in owner_names}
    linkage_dict = {name: int(linkage_counts.get(name, 0)) for name in linkage_names}
    return {
        "schema_version": BRANCH_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.29",
        "selected_strategy_id": str(strategy_payload["strategy_id"]),
        "selected_strategy_origin": str(strategy_payload["origin"]),
        "policy_trace_row_count": int(policy_trace_row_count),
        "coordination_action_counts": action_dict,
        "owner_counts": owner_dict,
        "linkage_decision_counts": linkage_dict,
        "ownership_action_exercised": int(action_dict["owner_proposal_select"]) >= 1,
        "ownership_or_linkage_decision_exercised": (
            int(owner_dict["contribution_leader"]) >= 1 or int(linkage_dict["break"]) >= 1
        ),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(
    *,
    case_results: Sequence[_CaseResult],
    inherited_stage8_29_fe_total: int,
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
        "budget_scope": "cec2013_f13_f14_behavior_distinct_policy_checkpoint",
        "run_count": int(run_count),
        "max_fe_per_method_per_function": int(max_fe),
        "inherited_stage8_29_FE_total": int(inherited_stage8_29_fe_total),
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
        "claim_scope": "CEC2013 F13/F14 behavior-distinct policy checkpoint only",
        "run_count": int(run_count),
        "max_fe_per_method_per_function": int(max_fe),
        "checkpoint_steps": sorted(int(step) for step in checkpoint_steps),
        "parallel_execution_used": bool(parallel_execution_used),
        "max_workers": int(max_workers),
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "official_cec2013_panel_run": False,
        "checkpoint_executed": True,
        "full_objective_trace_written": False,
        "compact_checkpoint_trace_written": True,
        "not_full_25_run_panel": True,
        "not_full_f1_f15_panel": True,
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "new_llm_strategy_generation": False,
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
    promising = bool(win_loss["checkpoint_promising"])
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": (
            "PROMISING_CHECKPOINT_ROUTE_TO_STAGE8_31_FORMAL_DECISION"
            if promising
            else "CHECKPOINT_NOT_PROMISING_DIAGNOSE_BEFORE_FORMAL_PANEL"
        ),
        "next_stage": "Stage 8.31",
        "allowed_next_work": (
            "formal_f13_f14_same_budget_decision_gate"
            if promising
            else "failure_honest_behavior_distinct_checkpoint_diagnosis"
        ),
        "run_full_25_run_panel_next": False,
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
    strategy_payload: Mapping[str, Any],
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
        "source_stage": "8.29",
        "pilot_scope": "cec2013_f13_f14_behavior_distinct_policy_checkpoint",
        "benchmark_suite": BENCHMARK_SUITE,
        "selected_strategy_id": str(strategy_payload["strategy_id"]),
        "selected_strategy_origin": str(strategy_payload["origin"]),
        "frozen_policy_status": str(frozen_policy["frozen_policy_status"]),
        "frozen_behavior_distinct_policy_used": True,
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
        "checkpoint_executed": True,
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
        "behavior_policy_vs_best_reward_select": dict(
            win_loss["behavior_policy_vs_best_reward_select"]
        ),
        "behavior_policy_vs_best_baseline": dict(
            win_loss["behavior_policy_vs_best_baseline"]
        ),
        "policy_branch_report_written": True,
        "ownership_action_exercised": bool(branch_report["ownership_action_exercised"]),
        "ownership_or_linkage_decision_exercised": bool(
            branch_report["ownership_or_linkage_decision_exercised"]
        ),
        "checkpoint_promising": bool(win_loss["checkpoint_promising"]),
        "run_full_25_run_panel_next": False,
        "recommended_next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "new_llm_strategy_generation_used": False,
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

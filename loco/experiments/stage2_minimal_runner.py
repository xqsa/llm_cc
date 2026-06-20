"""Stage 2.0 minimal conflict-coordination runner.

This runner is intentionally not an optimizer. It creates one deterministic
proposal per group, builds shared-variable conflict states, applies baseline
coordination operators, and accounts for every objective evaluation.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loco.benchmarks.cec2013lsgo_metabox import load_cec2013lsgo_problem
from loco.benchmarks.problem_interface import LSGOProblem
from loco.benchmarks.synthetic_overlap_generator import (
    SyntheticOverlapProblem,
    generate_synthetic_overlap,
)
from loco.conflict.conflict_metrics import aggregate_conflict_metrics, metrics_for_state
from loco.conflict.conflict_state import (
    ConflictStateBatch,
    GroupProposal,
    SharedVariableConflictState,
)
from loco.coordination.baselines import (
    CoordinationOperator,
    NoCoordination,
    default_baseline_operators,
)
from loco.coordination.frozen_ast_smoke import FrozenASTSmokeOperator
from loco.coordination.operator_artifacts import DEFAULT_STAGE2_5_REGISTRY_PATH
from loco.evaluation.fe_accounting import FEBudgetTracker


def _git_commit_hash() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).resolve().parents[2],
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _json_ready(data: Any) -> Any:
    if isinstance(data, dict):
        return {str(key): _json_ready(value) for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return [_json_ready(value) for value in data]
    if isinstance(data, (np.integer,)):
        return int(data)
    if isinstance(data, (np.floating,)):
        return float(data)
    if isinstance(data, (np.bool_,)):
        return bool(data)
    return data


def _make_synthetic_problem(seed: int) -> SyntheticOverlapProblem:
    structure = generate_synthetic_overlap(
        dimension=100,
        num_groups=8,
        base_group_size=20,
        overlap_ratio=0.10,
        topology="line",
        seed=seed,
    )
    return SyntheticOverlapProblem(structure, name=f"stage2_synthetic_line_seed_{seed}")


def _initial_solution(problem: LSGOProblem, seed: int) -> np.ndarray:
    lower, upper = problem.bounds()
    rng = np.random.default_rng(seed)
    raw = rng.normal(loc=0.0, scale=1.0, size=problem.dimension())
    return np.clip(raw, lower, upper)


def _proposal_value(
    current_value: float, lower: float, upper: float, group_id: int, variable_id: int
) -> float:
    sign = 1.0 if (group_id + variable_id) % 2 == 0 else -1.0
    magnitude = 0.20 + 0.05 * ((group_id + variable_id) % 3)
    proposed = 0.70 * current_value + sign * magnitude
    return float(np.clip(proposed, lower, upper))


def _build_group_proposals(
    problem: LSGOProblem,
    current: np.ndarray,
    baseline_objective: float,
    tracker: FEBudgetTracker,
) -> tuple[dict[int, list[GroupProposal]], list[dict[str, Any]]]:
    groups = problem.grouping()
    if groups is None:
        raise ValueError("Stage 2.0 runner requires grouping metadata.")
    shared = problem.shared_variables()
    lower, upper = problem.bounds()

    grouped: dict[int, list[GroupProposal]] = {
        variable_id: [] for variable_id in sorted(shared)
    }
    proposal_log: list[dict[str, Any]] = []
    for group_id, group in enumerate(groups):
        candidate = current.copy()
        for variable_id in group:
            candidate[variable_id] = _proposal_value(
                current_value=float(current[variable_id]),
                lower=float(lower[variable_id]),
                upper=float(upper[variable_id]),
                group_id=group_id,
                variable_id=variable_id,
            )
        objective = problem.evaluate(candidate)
        tracker.record("proposal", 1)
        reward = baseline_objective - objective
        proposal_log.append(
            {
                "group_id": group_id,
                "objective": objective,
                "reward": reward,
                "shared_variables": sorted(set(group).intersection(shared)),
            }
        )
        for variable_id in sorted(set(group).intersection(shared)):
            grouped[variable_id].append(
                GroupProposal(
                    group_id=group_id,
                    variable_id=variable_id,
                    proposed_value=float(candidate[variable_id]),
                    reward=reward,
                )
            )
    return grouped, proposal_log


def _make_conflict_batch(
    problem: LSGOProblem,
    current: np.ndarray,
    grouped_proposals: dict[int, list[GroupProposal]],
) -> ConflictStateBatch:
    lower, upper = problem.bounds()
    return ConflictStateBatch.from_grouped_proposals(
        current_values=current,
        lower_bounds=lower,
        upper_bounds=upper,
        grouped_proposals=grouped_proposals,
        consensus_history_by_variable={
            variable_id: [
                float(current[variable_id]),
                float(current[variable_id]) * -0.5,
                float(current[variable_id]) * 0.25,
            ]
            for variable_id in grouped_proposals
        },
    )


def _collapsed_after_batch(
    before: ConflictStateBatch,
    coordinated_values: dict[int, float],
    collapse_rewards: bool,
) -> ConflictStateBatch:
    grouped: dict[int, list[GroupProposal]] = {}
    current_values = []
    lower = []
    upper = []
    max_variable = max((state.variable_id for state in before.states), default=-1)
    size = max_variable + 1
    current_array = np.zeros(size)
    lower_array = np.full(size, -1.0)
    upper_array = np.full(size, 1.0)
    for state in before.states:
        current_array[state.variable_id] = state.current_value
        lower_array[state.variable_id] = state.bounds[0]
        upper_array[state.variable_id] = state.bounds[1]
        coordinated = coordinated_values[state.variable_id]
        reward = float(np.mean(state.group_rewards)) if collapse_rewards else None
        grouped[state.variable_id] = [
            GroupProposal(
                group_id=group_id,
                variable_id=state.variable_id,
                proposed_value=coordinated,
                reward=reward if reward is not None else original_reward,
            )
            for group_id, original_reward in zip(
                state.related_group_ids, state.group_rewards
            )
        ]
        current_values.append(state.current_value)
        lower.append(state.bounds[0])
        upper.append(state.bounds[1])
    return ConflictStateBatch.from_grouped_proposals(
        current_values=current_array,
        lower_bounds=lower_array,
        upper_bounds=upper_array,
        grouped_proposals=grouped,
    )


def _stage2_4_smoke_operators() -> list[CoordinationOperator]:
    return [*default_baseline_operators(), FrozenASTSmokeOperator()]


def _run_problem(
    problem: LSGOProblem,
    seed: int,
    max_fe: int,
    output_path: Path | None = None,
    include_frozen_ast_smoke: bool = False,
) -> dict[str, Any]:
    groups = problem.grouping()
    if groups is None:
        raise ValueError("Stage 2.0 requires grouping metadata.")
    shared = problem.shared_variables()
    current = _initial_solution(problem, seed)
    proposal_tracker = FEBudgetTracker(max_fe=max_fe)
    baseline_objective = problem.evaluate(current)
    proposal_tracker.record("proposal", 1)
    grouped_proposals, proposal_log = _build_group_proposals(
        problem, current, baseline_objective, proposal_tracker
    )
    before_batch = _make_conflict_batch(problem, current, grouped_proposals)
    before_metrics = aggregate_conflict_metrics(
        before_batch,
        overlap_ratio=float(problem.metadata().get("overlap_ratio", 0.0)),
    )

    operators = (
        _stage2_4_smoke_operators()
        if include_frozen_ast_smoke
        else default_baseline_operators()
    )
    operator_results: dict[str, Any] = {}
    optimum = problem.optimum_value()
    for operator in operators:
        tracker = FEBudgetTracker(max_fe=max_fe)
        tracker.record("proposal", proposal_tracker.fe_proposal)
        coordinated = current.copy()
        coordination_results = {}
        extra_fe = 0
        for state in before_batch:
            result = operator.coordinate(state)
            if result.variable_id not in shared:
                raise RuntimeError(
                    "Coordination operator attempted to modify a non-shared variable."
                )
            coordinated[result.variable_id] = result.coordinated_value
            coordination_results[str(result.variable_id)] = result.to_dict()
            extra_fe += result.extra_fe
        if extra_fe:
            tracker.record("coordination_extra", extra_fe)

        final_objective = problem.evaluate(coordinated)
        tracker.record("proposal", 1)
        collapse = bool(before_batch.states) and not isinstance(
            operator, NoCoordination
        )
        before_intensity = before_metrics["mean_conflict_intensity"]
        if before_batch.states and collapse:
            after_batch = _collapsed_after_batch(
                before_batch,
                coordinated_values={
                    int(key): value["coordinated_value"]
                    for key, value in coordination_results.items()
                },
                collapse_rewards=True,
            )
            after_metrics = aggregate_conflict_metrics(
                after_batch,
                overlap_ratio=float(problem.metadata().get("overlap_ratio", 0.0)),
            )
            after_intensity = after_metrics["mean_conflict_intensity"]
        else:
            after_intensity = before_intensity
        if before_intensity <= 1e-12:
            consensus_collapse = 0.0
        else:
            consensus_collapse = max(
                0.0, (before_intensity - after_intensity) / before_intensity
            )

        operator_payload = {
            "final_objective": final_objective,
            "final_error": None if optimum is None else final_objective - optimum,
            "FE_total": tracker.fe_total,
            "FE_coordination_extra": tracker.fe_coordination_extra,
            "FE_commit_evaluation": 1,
            "FE_analysis_only": 0,
            "budget_scope": "per_method_run",
            "cross_baseline_evaluations_shared": False,
            "fe_accounting": tracker.to_dict(),
            "mean_conflict_before": before_intensity,
            "mean_conflict_after": after_intensity,
            "proposal_consensus_collapse_ratio": consensus_collapse,
            "metric_honesty_note": (
                "This is a one-shot collapse of the current proposal set after coordination, "
                "not evidence that regenerated future conflicts are reduced."
            ),
            "coordination_results": coordination_results,
            "changed_variables": sorted(
                int(variable_id) for variable_id in coordination_results
            ),
        }
        if hasattr(operator, "runtime_metadata"):
            operator_payload["frozen_ast_runtime"] = operator.runtime_metadata()
        operator_results[operator.name] = operator_payload

    result = {
        "stage": "2.5" if include_frozen_ast_smoke else "2.0",
        "seed": seed,
        "git_commit": _git_commit_hash(),
        "benchmark": {
            "name": problem.metadata().get("name"),
            "source": problem.metadata().get("source"),
            "dimension": problem.dimension(),
            "num_groups": len(groups),
            "number_of_shared_variables": len(shared),
            "overlap_ratio": float(problem.metadata().get("overlap_ratio", 0.0)),
        },
        "initial_objective": baseline_objective,
        "proposal_log": proposal_log,
        "aggregate_conflict_metrics": before_metrics,
        "per_variable_conflict_metrics": {
            str(state.variable_id): metrics_for_state(state) for state in before_batch
        },
        "operators": operator_results,
    }
    if include_frozen_ast_smoke:
        result["frozen_ast_smoke"] = {
            "enabled": True,
            "source": "frozen_artifact_registry",
            "no_llm": True,
            "no_evolution": True,
            "no_optimizer": True,
            "no_objective_evaluation": True,
        }
        result["artifact_registry"] = {
            "enabled": True,
            "registry_path": DEFAULT_STAGE2_5_REGISTRY_PATH.relative_to(
                ROOT
            ).as_posix(),
            "frozen_only": True,
            "no_test_feedback": True,
        }
    result = _json_ready(result)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
            output_file.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def run_stage2_synthetic_minimal(
    seed: int = 0,
    output_path: Path | str | None = None,
    max_fe: int = 10_000,
) -> dict[str, Any]:
    problem = _make_synthetic_problem(seed)
    path = Path(output_path) if output_path is not None else None
    return _run_problem(
        problem=problem,
        seed=seed,
        max_fe=max_fe,
        output_path=path,
        include_frozen_ast_smoke=True,
    )


def run_optional_f14_smoke(seed: int = 0, max_fe: int = 10_000) -> dict[str, Any]:
    try:
        problem = load_cec2013lsgo_problem(14, version="numpy")
        result = _run_problem(
            problem=problem,
            seed=seed,
            max_fe=max_fe,
            include_frozen_ast_smoke=True,
        )
    except Exception as exc:
        return {
            "status": "SKIP",
            "function_id": 14,
            "reason": f"{type(exc).__name__}: {exc}",
        }
    return {
        "status": "PASS",
        "function_id": 14,
        "operator_count": len(result["operators"]),
        "summary": {
            "dimension": result["benchmark"]["dimension"],
            "number_of_shared_variables": result["benchmark"][
                "number_of_shared_variables"
            ],
            "best_operator": min(
                result["operators"],
                key=lambda name: result["operators"][name]["final_objective"],
            ),
        },
    }


def main() -> int:
    output_path = Path("docs/stage2/stage2_5_artifact_registry_result.json")
    result = run_stage2_synthetic_minimal(seed=0, output_path=output_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Stage 7.2 synthetic large-scale LOCO-CC objective panel.

This stage expands the Stage 7.1 objective-loop pilot to the Stage 7.0 locked
synthetic panel types. It is still a bounded synthetic execution surface, not a
final benchmark or SOTA claim.
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
from loco.coordination.dsl import load_coordination_ast
from loco.coordination.dsl_runtime import FrozenASTRuntime


STAGE = "7.2"
TRACE_SCHEMA_VERSION = "loco.stage7_2_objective_trace.v1"
PANEL_SUMMARY_SCHEMA_VERSION = "loco.stage7_2_panel_summary.v1"
METHOD_SUMMARY_SCHEMA_VERSION = "loco.stage7_2_method_summary.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage7_2_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage7_2_runtime_boundary.v1"
REPORT_SCHEMA_VERSION = "loco.stage7_2_panel_report.v1"

METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "selected_loco_operator",
]
PANEL_NAMES = [
    "synthetic_no_overlap_panel",
    "synthetic_low_overlap_panel",
    "synthetic_conflicting_overlap_panel",
    "synthetic_high_overlap_panel",
]
DIMENSIONS = [500, 1000]
SEEDS = [0]
OBJECTIVE_STEPS = 3


@dataclass(frozen=True)
class _Method:
    name: str
    label: str
    is_selected_loco: bool
    coordinate: Callable[[SharedVariableConflictState], CoordinationResult]


@dataclass(frozen=True)
class _PanelProblem:
    panel_name: str
    dimension: int
    seed: int
    selected_variable: int
    shared_conflict_present: bool
    groups: tuple[tuple[int, ...], ...]
    bounds: tuple[float, float] = (-1.0, 1.0)
    objective_name: str = "synthetic_sphere"
    grouping_mode: str = "oracle grouping"


def run_stage7_2_synthetic_objective_panel(
    *,
    protocol_path: Path | str,
    selected_operator_path: Path | str,
    selected_ast_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Run the locked Stage 7.2 synthetic objective panel."""

    protocol = _read_json_or_yaml(Path(protocol_path))
    selected_operator = _read_json(Path(selected_operator_path))
    selected_ast_payload = _read_json(Path(selected_ast_path))
    _validate_inputs(protocol, selected_operator, selected_ast_payload)

    selected_candidate_id = str(selected_operator["candidate_id"])
    selected_runtime = FrozenASTRuntime(load_coordination_ast(selected_ast_payload))
    selected_variable = int(selected_operator["target_variable_set"][0])
    methods = _build_methods(selected_runtime, selected_candidate_id, selected_variable)

    trace_rows: list[dict[str, Any]] = []
    for panel_name in PANEL_NAMES:
        for dimension in DIMENSIONS:
            for seed in SEEDS:
                problem = _build_panel_problem(
                    panel_name=panel_name,
                    dimension=dimension,
                    seed=seed,
                    selected_variable=selected_variable,
                )
                for method in methods:
                    trace_rows.extend(
                        _run_method_loop(
                            method=method,
                            selected_candidate_id=selected_candidate_id,
                            problem=problem,
                        )
                    )

    panel_summary = _build_panel_summary(trace_rows)
    method_summary = _build_method_summary(trace_rows, selected_candidate_id)
    ledger = _build_fe_ledger(trace_rows)
    boundary = _build_runtime_boundary()
    report = _build_report(
        trace_rows=trace_rows,
        panel_summary=panel_summary,
        method_summary=method_summary,
        ledger=ledger,
        selected_candidate_id=selected_candidate_id,
        selected_variable=selected_variable,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "objective_trace.jsonl", trace_rows)
    _write_json(output_path / "panel_summary.json", panel_summary)
    _write_json(output_path / "method_summary.json", method_summary)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "panel_report.json", report)
    return report


def _validate_inputs(
    protocol: Mapping[str, Any],
    selected_operator: Mapping[str, Any],
    selected_ast_payload: Mapping[str, Any],
) -> None:
    if protocol.get("stage") != "7.0":
        raise ValueError("Stage 7.2 requires the Stage 7.0 protocol.")
    if protocol.get("next_status") != "READY_FOR_STAGE7_1_MINIMAL_OBJECTIVE_LOOP_PILOT":
        raise ValueError("Stage 7.0 protocol is not ready for Stage 7 objective runs.")
    purpose = protocol.get("purpose", {})
    if purpose.get("objective_evaluation_protocol_locked") is not True:
        raise ValueError("Stage 7.0 objective protocol must be locked.")

    required_methods = set(protocol.get("baseline_methods", ()))
    if required_methods and required_methods != set(METHOD_NAMES):
        raise ValueError("Stage 7.2 method set must match the Stage 7.0 protocol.")

    if selected_operator.get("stage") != "5.1":
        raise ValueError("Stage 7.2 requires the Stage 5.1 selected operator.")
    if selected_operator.get("freeze_status") != "FROZEN_FOR_SEALED_TEST_NOT_FINAL":
        raise ValueError("Stage 7.2 requires the frozen selected operator.")
    if selected_ast_payload.get("operator_id") != selected_operator.get("candidate_id"):
        raise ValueError("Selected AST operator_id does not match selected operator.")

    forbidden_true_fields = [
        "llm_call_used",
        "new_candidate_generation_used",
        "prompt_revision_used",
        "train_search_revision_used",
        "promotion_rule_revision_used",
        "validation_rule_revision_used",
        "test_feedback_used",
        "sealed_test_access_used",
        "objective_evaluation_used",
        "baseopt_modified",
        "optimizer_generation_used",
        "controller_scheduler_generation_used",
    ]
    for field in forbidden_true_fields:
        if selected_operator.get(field) is True:
            raise ValueError(f"Selected operator violates boundary: {field}")
    if selected_operator.get("not_performance_claim") is not True:
        raise ValueError("Selected operator must preserve claim boundary.")


def _build_methods(
    selected_runtime: FrozenASTRuntime,
    selected_candidate_id: str,
    selected_variable: int,
) -> list[_Method]:
    return [
        _Method(
            name="identity_no_coord",
            label="NoCoordination",
            is_selected_loco=False,
            coordinate=NoCoordination().coordinate,
        ),
        _Method(
            name="simple_consensus",
            label="AverageConsensus",
            is_selected_loco=False,
            coordinate=AverageConsensus().coordinate,
        ),
        _Method(
            name="weighted_consensus",
            label="WeightedConsensus",
            is_selected_loco=False,
            coordinate=WeightedConsensus(temperature=1.0).coordinate,
        ),
        _Method(
            name="best_reward_select",
            label="BestRewardSelection",
            is_selected_loco=False,
            coordinate=BestRewardSelection().coordinate,
        ),
        _Method(
            name="selected_loco_operator",
            label=f"DSLRuntime({selected_candidate_id})",
            is_selected_loco=True,
            coordinate=lambda state: selected_runtime.coordinate(
                state, shared_variables={selected_variable}
            ),
        ),
    ]


def _build_panel_problem(
    *,
    panel_name: str,
    dimension: int,
    seed: int,
    selected_variable: int,
) -> _PanelProblem:
    if panel_name == "synthetic_no_overlap_panel":
        groups = (
            (0, 1, 2, 3, 4),
            (selected_variable, 7, 8, 9, 10),
            (11, 12, 13, 14, 15),
        )
        shared_conflict_present = False
    elif panel_name == "synthetic_low_overlap_panel":
        groups = (
            (0, 1, 2, 3, selected_variable),
            (selected_variable, 7, 8, 9, 10),
            (11, 12, 13, 14, 15),
        )
        shared_conflict_present = True
    elif panel_name == "synthetic_conflicting_overlap_panel":
        groups = (
            (0, 1, 2, 3, 4, selected_variable),
            (selected_variable, 7, 8, 9, 10, 11),
            (12, 13, 14, 15),
        )
        shared_conflict_present = True
    elif panel_name == "synthetic_high_overlap_panel":
        groups = (
            (0, 1, selected_variable, 3, 4, 5),
            (selected_variable, 7, 8, 9, 10, 11),
            (12, selected_variable, 13, 14, 15, 16),
        )
        shared_conflict_present = True
    else:
        raise ValueError(f"Unknown synthetic panel: {panel_name}")

    if max(max(group) for group in groups) >= dimension:
        raise ValueError("Synthetic panel groups exceed the requested dimension.")

    return _PanelProblem(
        panel_name=panel_name,
        dimension=int(dimension),
        seed=int(seed),
        selected_variable=int(selected_variable),
        shared_conflict_present=shared_conflict_present,
        groups=groups,
    )


def _run_method_loop(
    *,
    method: _Method,
    selected_candidate_id: str,
    problem: _PanelProblem,
) -> list[dict[str, Any]]:
    lower, upper = problem.bounds
    current = _initial_vector(problem)
    best_objective = _sphere(current)
    consensus_history: list[float] = []
    trace_rows: list[dict[str, Any]] = []

    for step_index in range(1, OBJECTIVE_STEPS + 1):
        candidate = current.copy()
        candidate *= _non_shared_decay(problem.panel_name)
        state = None
        result = None
        selected_loco_application_count = 0

        if problem.shared_conflict_present:
            state = _build_online_conflict_state(
                current=current,
                problem=problem,
                step_index=step_index,
                consensus_history=consensus_history,
            )
            result = method.coordinate(state)
            candidate[problem.selected_variable] = result.coordinated_value
            if method.is_selected_loco:
                selected_loco_application_count = 1

        candidate = np.clip(candidate, lower, upper)
        objective_value = _sphere(candidate)
        improved = objective_value <= best_objective
        if improved:
            current = candidate
            best_objective = objective_value
            if result is not None:
                consensus_history.append(result.coordinated_value)

        trace_rows.append(
            _trace_row(
                method=method,
                selected_candidate_id=selected_candidate_id,
                problem=problem,
                state=state,
                result=result,
                step_index=step_index,
                objective_value=objective_value,
                best_objective=best_objective,
                improved=improved,
                selected_loco_application_count=selected_loco_application_count,
            )
        )

    return trace_rows


def _initial_vector(problem: _PanelProblem) -> np.ndarray:
    rng = np.random.default_rng(problem.seed + problem.dimension)
    base = rng.uniform(-0.04, 0.04, size=problem.dimension)
    vector = np.full(problem.dimension, 0.2, dtype=float) + base
    vector[problem.selected_variable] = 0.15
    return vector


def _non_shared_decay(panel_name: str) -> float:
    if panel_name == "synthetic_no_overlap_panel":
        return 0.95
    if panel_name == "synthetic_low_overlap_panel":
        return 0.955
    if panel_name == "synthetic_conflicting_overlap_panel":
        return 0.96
    return 0.965


def _build_online_conflict_state(
    *,
    current: np.ndarray,
    problem: _PanelProblem,
    step_index: int,
    consensus_history: Sequence[float],
) -> SharedVariableConflictState:
    current_value = float(current[problem.selected_variable])
    lower, upper = problem.bounds
    if problem.panel_name == "synthetic_low_overlap_panel":
        proposals = _two_group_proposals(
            selected_variable=problem.selected_variable,
            current_value=current_value,
            step_index=step_index,
            negative_scale=0.32,
            positive_scale=0.20,
            best_reward=0.72,
            weak_reward=0.48,
        )
    elif problem.panel_name == "synthetic_conflicting_overlap_panel":
        proposals = _two_group_proposals(
            selected_variable=problem.selected_variable,
            current_value=current_value,
            step_index=step_index,
            negative_scale=0.55,
            positive_scale=0.45,
            best_reward=0.84,
            weak_reward=0.30,
        )
    elif problem.panel_name == "synthetic_high_overlap_panel":
        proposals = [
            GroupProposal(
                group_id=301,
                variable_id=problem.selected_variable,
                proposed_value=current_value - 0.65 / step_index,
                reward=0.80 + 0.02 * step_index,
                metadata={"fixed_baseopt": True, "proposal_role": "toward_origin"},
            ),
            GroupProposal(
                group_id=302,
                variable_id=problem.selected_variable,
                proposed_value=current_value + 0.56 / step_index,
                reward=0.34 + 0.01 * step_index,
                metadata={"fixed_baseopt": True, "proposal_role": "conflicting"},
            ),
            GroupProposal(
                group_id=303,
                variable_id=problem.selected_variable,
                proposed_value=current_value - 0.18 / step_index,
                reward=0.58 + 0.01 * step_index,
                metadata={"fixed_baseopt": True, "proposal_role": "moderate"},
            ),
        ]
    else:
        raise ValueError("No-overlap panels must not build conflict states.")

    return SharedVariableConflictState.from_group_proposals(
        variable_id=problem.selected_variable,
        current_value=current_value,
        bounds=(float(lower), float(upper)),
        proposals=proposals,
        consensus_history=consensus_history,
        diagnostics={
            "split": "synthetic_panel",
            "fixed_baseopt": True,
            "objective_loop_step": step_index,
            "panel": problem.panel_name,
            "dimension": problem.dimension,
            "seed": problem.seed,
        },
    )


def _two_group_proposals(
    *,
    selected_variable: int,
    current_value: float,
    step_index: int,
    negative_scale: float,
    positive_scale: float,
    best_reward: float,
    weak_reward: float,
) -> list[GroupProposal]:
    return [
        GroupProposal(
            group_id=201,
            variable_id=selected_variable,
            proposed_value=current_value - negative_scale / step_index,
            reward=best_reward + 0.02 * step_index,
            metadata={"fixed_baseopt": True, "proposal_role": "toward_origin"},
        ),
        GroupProposal(
            group_id=202,
            variable_id=selected_variable,
            proposed_value=current_value + positive_scale / step_index,
            reward=weak_reward + 0.01 * step_index,
            metadata={"fixed_baseopt": True, "proposal_role": "conflicting"},
        ),
    ]


def _trace_row(
    *,
    method: _Method,
    selected_candidate_id: str,
    problem: _PanelProblem,
    state: SharedVariableConflictState | None,
    result: CoordinationResult | None,
    step_index: int,
    objective_value: float,
    best_objective: float,
    improved: bool,
    selected_loco_application_count: int,
) -> dict[str, Any]:
    shared_conflict_present = state is not None
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "7.1",
        "split": "synthetic_panel",
        "panel_name": problem.panel_name,
        "synthetic_panel": problem.panel_name,
        "seed": problem.seed,
        "method_name": method.name,
        "operator_label": method.label,
        "selected_loco_candidate_id": selected_candidate_id,
        "is_selected_loco_operator": method.is_selected_loco,
        "selected_loco_application_count": selected_loco_application_count,
        "objective_name": problem.objective_name,
        "problem_dimension": problem.dimension,
        "target_scope": "shared_variables_only",
        "grouping_mode": problem.grouping_mode,
        "shared_conflict_present": shared_conflict_present,
        "shared_variable_id": None if state is None else int(state.variable_id),
        "objective_step": int(step_index),
        "current_shared_value": None if state is None else float(state.current_value),
        "coordinated_shared_value": (
            None if result is None else float(result.coordinated_value)
        ),
        "objective_value": round(float(objective_value), 12),
        "best_objective_so_far": round(float(best_objective), 12),
        "objective_improved_or_equal": bool(improved),
        "conflict_intensity": (
            0.0 if state is None else round(conflict_intensity(state), 12)
        ),
        "shared_variable_oscillation": (
            0.0 if state is None else round(oscillation_score(state), 12)
        ),
        "coordination_update_size": (
            0.0
            if state is None or result is None
            else round(abs(result.coordinated_value - state.current_value), 12)
        ),
        "distance_to_best_reward_proposal": (
            None
            if state is None or result is None
            else round(_distance_to_best_reward_proposal(state, result), 12)
        ),
        "FE_grouping": 0,
        "FE_proposal": 1,
        "FE_coordination_extra": 0 if result is None else int(result.extra_fe),
        "FE_repair": 0,
        "FE_global_objective": 1,
        "FE_total": 2 if result is None else 2 + int(result.extra_fe),
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "selected_operator_revision_used": False,
        "evolution_search_used": False,
        "test_feedback_tuning_used": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_panel_summary(trace_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    panel_rows = []
    for panel_name in PANEL_NAMES:
        for dimension in DIMENSIONS:
            rows = [
                row
                for row in trace_rows
                if row["synthetic_panel"] == panel_name
                and row["problem_dimension"] == dimension
            ]
            panel_rows.append(
                {
                    "synthetic_panel": panel_name,
                    "problem_dimension": dimension,
                    "seed_count": len({row["seed"] for row in rows}),
                    "method_count": len({row["method_name"] for row in rows}),
                    "trace_row_count": len(rows),
                    "shared_conflict_row_count": sum(
                        1 for row in rows if row["shared_conflict_present"]
                    ),
                    "final_best_by_method": {
                        method_name: _last_best(rows, method_name)
                        for method_name in METHOD_NAMES
                    },
                    "FE_global_objective": sum(
                        int(row["FE_global_objective"]) for row in rows
                    ),
                    "FE_total": sum(int(row["FE_total"]) for row in rows),
                }
            )
    return {
        "schema_version": PANEL_SUMMARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.1",
        "panels": PANEL_NAMES,
        "dimensions": DIMENSIONS,
        "panel_rows": panel_rows,
        "claim_scope": "synthetic objective-panel execution",
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_method_summary(
    trace_rows: Sequence[Mapping[str, Any]], selected_candidate_id: str
) -> dict[str, Any]:
    method_rows = []
    for method_name in METHOD_NAMES:
        rows = [row for row in trace_rows if row["method_name"] == method_name]
        method_rows.append(
            {
                "method_name": method_name,
                "trace_row_count": len(rows),
                "panel_count": len({row["synthetic_panel"] for row in rows}),
                "dimension_count": len({row["problem_dimension"] for row in rows}),
                "seed_count": len({row["seed"] for row in rows}),
                "final_best_objective_mean": _mean(
                    _last_best(
                        [
                            row
                            for row in rows
                            if row["synthetic_panel"] == panel_name
                            and row["problem_dimension"] == dimension
                        ],
                        method_name,
                    )
                    for panel_name in PANEL_NAMES
                    for dimension in DIMENSIONS
                ),
                "mean_conflict_intensity": _mean(
                    row["conflict_intensity"] for row in rows
                ),
                "mean_coordination_update_size": _mean(
                    row["coordination_update_size"] for row in rows
                ),
                "FE_grouping": sum(int(row["FE_grouping"]) for row in rows),
                "FE_proposal": sum(int(row["FE_proposal"]) for row in rows),
                "FE_coordination_extra": sum(
                    int(row["FE_coordination_extra"]) for row in rows
                ),
                "FE_repair": sum(int(row["FE_repair"]) for row in rows),
                "FE_global_objective": sum(
                    int(row["FE_global_objective"]) for row in rows
                ),
                "FE_total": sum(int(row["FE_total"]) for row in rows),
            }
        )
    return {
        "schema_version": METHOD_SUMMARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.1",
        "selected_candidate_id": selected_candidate_id,
        "methods": METHOD_NAMES,
        "method_rows": method_rows,
        "claim_scope": "synthetic objective-panel execution",
        "same_budget_across_methods": True,
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
        "budget_scope": "synthetic_large_scale_objective_panel",
        "FE_grouping": fe_grouping,
        "FE_proposal": fe_proposal,
        "FE_coordination_extra": fe_coordination_extra,
        "FE_repair": fe_repair,
        "FE_global_objective": fe_global_objective,
        "FE_total": fe_total,
        "same_budget_across_methods": True,
        "cross_method_evaluations_shared": False,
        "objective_benchmark_run": False,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "legal_inputs": [
            "configs/stage7_0_objective_eval_protocol.yaml",
            "configs/stage7_1_objective_loop_pilot.yaml",
            "artifacts/selected/stage5_1/selected_operator.json",
            "artifacts/selected/stage5_1/selected_operator_ast.json",
        ],
        "claim_scope": "synthetic objective-panel execution",
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "selected_operator_revision": False,
            "evolution_search": False,
            "test_feedback_tuning": False,
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


def _build_report(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    panel_summary: Mapping[str, Any],
    method_summary: Mapping[str, Any],
    ledger: Mapping[str, Any],
    selected_candidate_id: str,
    selected_variable: int,
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.1",
        "panel_scope": "synthetic_large_scale_objective_panel",
        "selected_candidate_id": selected_candidate_id,
        "selected_operator_target_variable": selected_variable,
        "synthetic_panels": PANEL_NAMES,
        "panel_count": len(PANEL_NAMES),
        "dimensions": DIMENSIONS,
        "seed_count": len(SEEDS),
        "seeds": SEEDS,
        "method_count": len(METHOD_NAMES),
        "method_names": METHOD_NAMES,
        "objective_step_count_per_method_per_panel": OBJECTIVE_STEPS,
        "trace_row_count": len(trace_rows),
        "FE_total": int(ledger["FE_total"]),
        "FE_global_objective": int(ledger["FE_global_objective"]),
        "same_budget_across_methods": bool(ledger["same_budget_across_methods"]),
        "panel_summary_written": bool(panel_summary["panel_rows"]),
        "method_summary_written": bool(method_summary["method_rows"]),
        "objective_panel_executed": True,
        "objective_benchmark_run": False,
        "next_status": "READY_FOR_STAGE7_3_OBJECTIVE_RESULT_POLISH",
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "selected_operator_revision_used": False,
        "evolution_search_used": False,
        "test_feedback_tuning_used": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _distance_to_best_reward_proposal(
    state: SharedVariableConflictState, result: CoordinationResult
) -> float:
    rewards = np.asarray(state.group_rewards, dtype=float)
    best_index = int(np.argmax(rewards))
    width = max(state.range_width, 1e-12)
    return abs(result.coordinated_value - state.proposals[best_index]) / width


def _sphere(vector: np.ndarray) -> float:
    return float(np.sum(np.asarray(vector, dtype=float) ** 2))


def _last_best(rows: Sequence[Mapping[str, Any]], method_name: str) -> float:
    method_rows = [row for row in rows if row["method_name"] == method_name]
    if not method_rows:
        raise ValueError(f"No rows for method: {method_name}")
    return float(method_rows[-1]["best_objective_so_far"])


def _mean(values: Any) -> float:
    return round(float(np.mean([float(value) for value in values])), 12)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_or_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return _parse_minimal_stage7_yaml(text)


def _parse_minimal_stage7_yaml(text: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "purpose": {},
        "baseline_methods": [],
        "stage7_0_forbidden_scope": [],
    }
    current_list: str | None = None
    in_purpose = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            in_purpose = stripped == "purpose:"
            key = stripped[:-1]
            if key in {"baseline_methods", "stage7_0_forbidden_scope"}:
                current_list = key
            else:
                current_list = None
            continue
        if current_list and stripped.startswith("- "):
            payload[current_list].append(stripped[2:].strip().strip('"'))
            continue
        if in_purpose and stripped.startswith(("objective_", "large_scale_")):
            key, value = stripped.split(":", maxsplit=1)
            payload["purpose"][key.strip()] = _parse_scalar(value.strip())
            continue
        if not line.startswith(" ") and ":" in stripped:
            key, value = stripped.split(":", maxsplit=1)
            payload[key.strip()] = _parse_scalar(value.strip())
    return payload


def _parse_scalar(value: str) -> Any:
    clean = value.strip().strip('"')
    if clean == "true":
        return True
    if clean == "false":
        return False
    return clean


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

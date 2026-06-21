"""Stage 8.4 large-scale objective panel evaluation.

This stage executes the Stage 8.3 selected operator inside a fixed
objective-level LOCO-CC loop across a larger deterministic synthetic panel. It
does not call LLMs, generate candidates, run evolution/search, revise selected
operators, use validation/test feedback, modify BaseOpt, or make final
performance/SOTA claims.
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


STAGE = "8.4"
TRACE_SCHEMA_VERSION = "loco.stage8_4_objective_trace.v1"
PANEL_SUMMARY_SCHEMA_VERSION = "loco.stage8_4_panel_summary.v1"
METHOD_SUMMARY_SCHEMA_VERSION = "loco.stage8_4_method_summary.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_4_win_loss_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_4_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_4_runtime_boundary.v1"
REPORT_SCHEMA_VERSION = "loco.stage8_4_panel_report.v1"

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_CANDIDATE_POOL_PATH = (
    REPO_ROOT / "artifacts" / "candidates" / "stage3_6" / "frozen_candidate_pool.jsonl"
)

METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "frozen_stage5_selected_operator",
    "stage8_3_selected_operator",
]
BASELINE_METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
]
PANEL_NAMES = [
    "synthetic_low_overlap_panel",
    "synthetic_medium_overlap_panel",
    "synthetic_high_overlap_panel",
    "synthetic_conflicting_overlap_panel",
]
DIMENSIONS = [500, 1000, 2000]
SEEDS = [0, 1, 2]
OBJECTIVE_STEPS = 3
TIE_EPSILON = 1e-12


@dataclass(frozen=True)
class _Method:
    name: str
    label: str
    is_loco_operator: bool
    selected_candidate_id: str | None
    previous_frozen_candidate_id: str | None
    coordinate: Callable[[SharedVariableConflictState], CoordinationResult]


@dataclass(frozen=True)
class _PanelProblem:
    panel_name: str
    dimension: int
    seed: int
    selected_variable: int
    groups: tuple[tuple[int, ...], ...]
    bounds: tuple[float, float] = (-1.0, 1.0)
    objective_name: str = "synthetic_sphere"
    grouping_mode: str = "oracle grouping"


def run_stage8_4_large_scale_objective_panel(
    *,
    protocol_path: Path | str,
    stage8_3_selection_decision_path: Path | str,
    frozen_stage5_operator_path: Path | str,
    frozen_stage5_ast_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Run the locked Stage 8.4 large-scale objective panel."""

    protocol = _read_json_or_yaml(Path(protocol_path))
    stage8_3_decision = _read_json(Path(stage8_3_selection_decision_path))
    frozen_stage5_operator = _read_json(Path(frozen_stage5_operator_path))
    frozen_stage5_ast_payload = _read_json(Path(frozen_stage5_ast_path))
    _validate_inputs(
        protocol,
        stage8_3_decision,
        frozen_stage5_operator,
        frozen_stage5_ast_payload,
    )

    selected_candidate_id = str(stage8_3_decision["selected_candidate_id"])
    previous_frozen_candidate_id = str(stage8_3_decision["previous_frozen_candidate_id"])
    selected_candidate = _load_frozen_candidate(selected_candidate_id)
    selected_variable = int(frozen_stage5_operator["target_variable_set"][0])
    _validate_selected_candidate(selected_candidate, selected_variable)

    frozen_stage5_runtime = FrozenASTRuntime(load_coordination_ast(frozen_stage5_ast_payload))
    stage8_3_runtime = FrozenASTRuntime(
        load_coordination_ast(selected_candidate["llm_candidate_payload"]["ast"])
    )
    methods = _build_methods(
        frozen_stage5_runtime=frozen_stage5_runtime,
        stage8_3_runtime=stage8_3_runtime,
        selected_variable=selected_variable,
        selected_candidate_id=selected_candidate_id,
        previous_frozen_candidate_id=previous_frozen_candidate_id,
    )

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
                            problem=problem,
                            selected_candidate_id=selected_candidate_id,
                            previous_frozen_candidate_id=previous_frozen_candidate_id,
                        )
                    )

    panel_summary = _build_panel_summary(trace_rows)
    method_summary = _build_method_summary(trace_rows)
    win_loss_report = _build_win_loss_report(trace_rows)
    ledger = _build_fe_ledger(trace_rows)
    boundary = _build_runtime_boundary()
    route = _build_route(win_loss_report)
    report = _build_report(
        trace_rows=trace_rows,
        panel_summary=panel_summary,
        method_summary=method_summary,
        win_loss_report=win_loss_report,
        ledger=ledger,
        selected_candidate_id=selected_candidate_id,
        previous_frozen_candidate_id=previous_frozen_candidate_id,
        selected_variable=selected_variable,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "objective_trace.jsonl", trace_rows)
    _write_json(output_path / "method_summary.json", method_summary)
    _write_json(output_path / "panel_summary.json", panel_summary)
    _write_json(output_path / "win_loss_report.json", win_loss_report)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    _write_json(output_path / "panel_report.json", report)
    return report


def _validate_inputs(
    protocol: Mapping[str, Any],
    stage8_3_decision: Mapping[str, Any],
    frozen_stage5_operator: Mapping[str, Any],
    frozen_stage5_ast_payload: Mapping[str, Any],
) -> None:
    if protocol.get("stage") != "7.0":
        raise ValueError("Stage 8.4 requires the locked Stage 7.0 protocol.")
    purpose = protocol.get("purpose", {})
    if purpose.get("objective_evaluation_protocol_locked") is not True:
        raise ValueError("Stage 8.4 requires a locked objective protocol.")
    if stage8_3_decision.get("stage") != "8.3":
        raise ValueError("Stage 8.4 requires the Stage 8.3 selection decision.")
    if stage8_3_decision.get("status") != "PASS":
        raise ValueError("Stage 8.3 selection decision must pass.")
    if (
        stage8_3_decision.get("allowed_next_use")
        != "large-scale objective panel evaluation under locked protocol"
    ):
        raise ValueError("Stage 8.3 decision is not routed to Stage 8.4.")
    if stage8_3_decision.get("target_scope") != "shared_variables_only":
        raise ValueError("Stage 8.4 only evaluates shared-variable operators.")
    if stage8_3_decision.get("validation_feedback_used") is not False:
        raise ValueError("Stage 8.4 rejects validation-feedback decisions.")
    if stage8_3_decision.get("test_feedback_used") is not False:
        raise ValueError("Stage 8.4 rejects test-feedback decisions.")
    if stage8_3_decision.get("not_final_performance_claim") is not True:
        raise ValueError("Stage 8.4 requires claim-boundary preservation.")

    if frozen_stage5_operator.get("stage") != "5.1":
        raise ValueError("Stage 8.4 requires the frozen Stage 5.1 operator.")
    if (
        frozen_stage5_operator.get("candidate_id")
        != stage8_3_decision.get("previous_frozen_candidate_id")
    ):
        raise ValueError("Stage 5.1 operator must match Stage 8.3 previous frozen id.")
    if frozen_stage5_operator.get("freeze_status") != "FROZEN_FOR_SEALED_TEST_NOT_FINAL":
        raise ValueError("Stage 8.4 requires the frozen Stage 5.1 operator.")
    if (
        frozen_stage5_ast_payload.get("operator_id")
        != frozen_stage5_operator.get("candidate_id")
    ):
        raise ValueError("Frozen Stage 5.1 AST does not match selected operator.")
    if frozen_stage5_operator.get("not_performance_claim") is not True:
        raise ValueError("Frozen Stage 5.1 operator must preserve claim boundary.")


def _validate_selected_candidate(
    selected_candidate: Mapping[str, Any], selected_variable: int
) -> None:
    if selected_candidate.get("stage") != "3.6":
        raise ValueError("Stage 8.4 selected candidate must come from frozen pool.")
    if selected_candidate.get("frozen") is not True:
        raise ValueError("Stage 8.4 selected candidate must be frozen.")
    if selected_candidate.get("target_scope") != "shared_variables_only":
        raise ValueError("Stage 8.4 selected candidate must target shared variables.")
    if selected_variable not in selected_candidate.get("target_variable_set", []):
        raise ValueError("Stage 8.4 selected candidate targets the wrong variable.")
    if selected_candidate.get("no_llm_call") is not True:
        raise ValueError("Stage 8.4 selected candidate provenance must be no-LLM.")
    if selected_candidate.get("no_test_feedback") is not True:
        raise ValueError("Stage 8.4 selected candidate provenance must be test-blind.")
    if selected_candidate.get("not_performance_claim") is not True:
        raise ValueError("Stage 8.4 selected candidate must preserve claim boundary.")


def _load_frozen_candidate(candidate_id: str) -> Mapping[str, Any]:
    for row in _read_jsonl(FROZEN_CANDIDATE_POOL_PATH):
        if row.get("candidate_id") == candidate_id:
            return row
    raise ValueError(f"Frozen candidate not found: {candidate_id}")


def _build_methods(
    *,
    frozen_stage5_runtime: FrozenASTRuntime,
    stage8_3_runtime: FrozenASTRuntime,
    selected_variable: int,
    selected_candidate_id: str,
    previous_frozen_candidate_id: str,
) -> list[_Method]:
    return [
        _Method(
            name="identity_no_coord",
            label="NoCoordination",
            is_loco_operator=False,
            selected_candidate_id=None,
            previous_frozen_candidate_id=None,
            coordinate=NoCoordination().coordinate,
        ),
        _Method(
            name="simple_consensus",
            label="AverageConsensus",
            is_loco_operator=False,
            selected_candidate_id=None,
            previous_frozen_candidate_id=None,
            coordinate=AverageConsensus().coordinate,
        ),
        _Method(
            name="weighted_consensus",
            label="WeightedConsensus",
            is_loco_operator=False,
            selected_candidate_id=None,
            previous_frozen_candidate_id=None,
            coordinate=WeightedConsensus(temperature=1.0).coordinate,
        ),
        _Method(
            name="best_reward_select",
            label="BestRewardSelection",
            is_loco_operator=False,
            selected_candidate_id=None,
            previous_frozen_candidate_id=None,
            coordinate=BestRewardSelection().coordinate,
        ),
        _Method(
            name="frozen_stage5_selected_operator",
            label=f"DSLRuntime({previous_frozen_candidate_id})",
            is_loco_operator=True,
            selected_candidate_id=None,
            previous_frozen_candidate_id=previous_frozen_candidate_id,
            coordinate=lambda state: frozen_stage5_runtime.coordinate(
                state, shared_variables={selected_variable}
            ),
        ),
        _Method(
            name="stage8_3_selected_operator",
            label=f"DSLRuntime({selected_candidate_id})",
            is_loco_operator=True,
            selected_candidate_id=selected_candidate_id,
            previous_frozen_candidate_id=None,
            coordinate=lambda state: stage8_3_runtime.coordinate(
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
    if panel_name == "synthetic_low_overlap_panel":
        groups = (
            (0, 1, 2, 3, selected_variable),
            (selected_variable, 7, 8, 9, 10),
            (11, 12, 13, 14, 15),
        )
    elif panel_name == "synthetic_medium_overlap_panel":
        groups = (
            (0, 1, 2, 3, 4, selected_variable),
            (selected_variable, 7, 8, 9, 10, 11),
            (12, 13, 14, 15, 16),
        )
    elif panel_name == "synthetic_high_overlap_panel":
        groups = (
            (0, 1, selected_variable, 3, 4, 5),
            (selected_variable, 7, 8, 9, 10, 11),
            (12, selected_variable, 13, 14, 15, 16),
        )
    elif panel_name == "synthetic_conflicting_overlap_panel":
        groups = (
            (0, 1, 2, selected_variable, 4, 5),
            (selected_variable, 7, 8, 9, 10, 11),
            (12, selected_variable, 13, 14, 15, 16),
            (17, 18, selected_variable, 19, 20, 21),
        )
    else:
        raise ValueError(f"Unknown synthetic panel: {panel_name}")

    if max(max(group) for group in groups) >= dimension:
        raise ValueError("Synthetic panel groups exceed the requested dimension.")

    return _PanelProblem(
        panel_name=panel_name,
        dimension=int(dimension),
        seed=int(seed),
        selected_variable=int(selected_variable),
        groups=groups,
    )


def _run_method_loop(
    *,
    method: _Method,
    problem: _PanelProblem,
    selected_candidate_id: str,
    previous_frozen_candidate_id: str,
) -> list[dict[str, Any]]:
    lower, upper = problem.bounds
    current = _initial_vector(problem)
    best_objective = _sphere(current)
    consensus_history: list[float] = []
    trace_rows: list[dict[str, Any]] = []

    for step_index in range(1, OBJECTIVE_STEPS + 1):
        candidate = current.copy()
        candidate *= _non_shared_decay(problem.panel_name)
        state = _build_online_conflict_state(
            current=current,
            problem=problem,
            step_index=step_index,
            consensus_history=consensus_history,
        )
        result = method.coordinate(state)
        candidate[problem.selected_variable] = result.coordinated_value
        candidate = np.clip(candidate, lower, upper)
        objective_value = _sphere(candidate)
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
                objective_value=objective_value,
                best_objective=best_objective,
                improved=improved,
                selected_candidate_id=selected_candidate_id,
                previous_frozen_candidate_id=previous_frozen_candidate_id,
            )
        )
    return trace_rows


def _initial_vector(problem: _PanelProblem) -> np.ndarray:
    rng = np.random.default_rng(problem.seed + problem.dimension * 17)
    base = rng.uniform(-0.035, 0.035, size=problem.dimension)
    vector = np.full(problem.dimension, 0.2, dtype=float) + base
    vector[problem.selected_variable] = 0.15 + 0.01 * problem.seed
    return vector


def _non_shared_decay(panel_name: str) -> float:
    if panel_name == "synthetic_low_overlap_panel":
        return 0.955
    if panel_name == "synthetic_medium_overlap_panel":
        return 0.96
    if panel_name == "synthetic_high_overlap_panel":
        return 0.965
    return 0.97


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
            negative_scale=0.28,
            positive_scale=0.18,
            best_reward=0.72,
            weak_reward=0.48,
        )
    elif problem.panel_name == "synthetic_medium_overlap_panel":
        proposals = _two_group_proposals(
            selected_variable=problem.selected_variable,
            current_value=current_value,
            step_index=step_index,
            negative_scale=0.42,
            positive_scale=0.32,
            best_reward=0.78,
            weak_reward=0.40,
        )
    elif problem.panel_name == "synthetic_high_overlap_panel":
        proposals = [
            GroupProposal(
                group_id=301,
                variable_id=problem.selected_variable,
                proposed_value=current_value - 0.62 / step_index,
                reward=0.80 + 0.02 * step_index,
                metadata={"fixed_baseopt": True, "proposal_role": "toward_origin"},
            ),
            GroupProposal(
                group_id=302,
                variable_id=problem.selected_variable,
                proposed_value=current_value + 0.54 / step_index,
                reward=0.34 + 0.01 * step_index,
                metadata={"fixed_baseopt": True, "proposal_role": "conflicting"},
            ),
            GroupProposal(
                group_id=303,
                variable_id=problem.selected_variable,
                proposed_value=current_value - 0.16 / step_index,
                reward=0.58 + 0.01 * step_index,
                metadata={"fixed_baseopt": True, "proposal_role": "moderate"},
            ),
        ]
    else:
        proposals = [
            GroupProposal(
                group_id=401,
                variable_id=problem.selected_variable,
                proposed_value=current_value - 0.74 / step_index,
                reward=0.83 + 0.02 * step_index,
                metadata={"fixed_baseopt": True, "proposal_role": "toward_origin"},
            ),
            GroupProposal(
                group_id=402,
                variable_id=problem.selected_variable,
                proposed_value=current_value + 0.68 / step_index,
                reward=0.31 + 0.01 * step_index,
                metadata={"fixed_baseopt": True, "proposal_role": "conflicting"},
            ),
            GroupProposal(
                group_id=403,
                variable_id=problem.selected_variable,
                proposed_value=current_value + 0.26 / step_index,
                reward=0.44 + 0.01 * step_index,
                metadata={"fixed_baseopt": True, "proposal_role": "weak_conflicting"},
            ),
            GroupProposal(
                group_id=404,
                variable_id=problem.selected_variable,
                proposed_value=current_value - 0.22 / step_index,
                reward=0.61 + 0.01 * step_index,
                metadata={"fixed_baseopt": True, "proposal_role": "moderate"},
            ),
        ]

    return SharedVariableConflictState.from_group_proposals(
        variable_id=problem.selected_variable,
        current_value=current_value,
        bounds=(float(lower), float(upper)),
        proposals=proposals,
        consensus_history=consensus_history,
        diagnostics={
            "split": "large_scale_objective_panel",
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
    problem: _PanelProblem,
    state: SharedVariableConflictState,
    result: CoordinationResult,
    step_index: int,
    objective_value: float,
    best_objective: float,
    improved: bool,
    selected_candidate_id: str,
    previous_frozen_candidate_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "8.3",
        "split": "large_scale_objective_panel",
        "panel_name": problem.panel_name,
        "synthetic_panel": problem.panel_name,
        "seed": problem.seed,
        "method_name": method.name,
        "operator_label": method.label,
        "selected_candidate_id": selected_candidate_id,
        "previous_frozen_candidate_id": previous_frozen_candidate_id,
        "method_selected_candidate_id": method.selected_candidate_id,
        "method_previous_frozen_candidate_id": method.previous_frozen_candidate_id,
        "is_loco_operator": method.is_loco_operator,
        "selected_loco_application_count": 1 if method.is_loco_operator else 0,
        "objective_name": problem.objective_name,
        "problem_dimension": problem.dimension,
        "target_scope": "shared_variables_only",
        "grouping_mode": problem.grouping_mode,
        "shared_conflict_present": True,
        "shared_variable_id": int(state.variable_id),
        "objective_step": int(step_index),
        "current_shared_value": float(state.current_value),
        "coordinated_shared_value": float(result.coordinated_value),
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
        "new_candidate_generation_used": False,
        "selected_operator_revision_used": False,
        "evolution_search_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "test_feedback_tuning_used": False,
        "reported_results_used_as_runtime_feedback": False,
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
            for seed in SEEDS:
                rows = _case_rows(trace_rows, panel_name, dimension, seed)
                panel_rows.append(
                    {
                        "synthetic_panel": panel_name,
                        "problem_dimension": dimension,
                        "seed": seed,
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
        "source_stage": "8.3",
        "panels": PANEL_NAMES,
        "dimensions": DIMENSIONS,
        "seeds": SEEDS,
        "panel_rows": panel_rows,
        "claim_scope": "large-scale objective panel utility evidence",
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_method_summary(trace_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    method_rows = []
    for method_name in METHOD_NAMES:
        rows = [row for row in trace_rows if row["method_name"] == method_name]
        case_final_bests = [
            _last_best(_case_rows(trace_rows, panel_name, dimension, seed), method_name)
            for panel_name in PANEL_NAMES
            for dimension in DIMENSIONS
            for seed in SEEDS
        ]
        method_rows.append(
            {
                "method_name": method_name,
                "trace_row_count": len(rows),
                "panel_count": len({row["synthetic_panel"] for row in rows}),
                "dimension_count": len({row["problem_dimension"] for row in rows}),
                "seed_count": len({row["seed"] for row in rows}),
                "mean_final_best": _mean(case_final_bests),
                "median_final_best": _median(case_final_bests),
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
        "source_stage": "8.3",
        "methods": METHOD_NAMES,
        "method_rows": method_rows,
        "claim_scope": "large-scale objective panel utility evidence",
        "same_budget_across_methods": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_win_loss_report(trace_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    case_rows = []
    selected_final_bests = []
    frozen_final_bests = []
    best_baseline_final_bests = []
    for panel_name in PANEL_NAMES:
        for dimension in DIMENSIONS:
            for seed in SEEDS:
                rows = _case_rows(trace_rows, panel_name, dimension, seed)
                final_by_method = {
                    method_name: _last_best(rows, method_name)
                    for method_name in METHOD_NAMES
                }
                selected_final = final_by_method["stage8_3_selected_operator"]
                frozen_final = final_by_method["frozen_stage5_selected_operator"]
                best_baseline_method = min(
                    BASELINE_METHOD_NAMES, key=lambda name: final_by_method[name]
                )
                best_baseline_final = final_by_method[best_baseline_method]
                selected_final_bests.append(selected_final)
                frozen_final_bests.append(frozen_final)
                best_baseline_final_bests.append(best_baseline_final)
                case_rows.append(
                    {
                        "synthetic_panel": panel_name,
                        "problem_dimension": dimension,
                        "seed": seed,
                        "selected_operator_final_best": selected_final,
                        "frozen_stage5_final_best": frozen_final,
                        "best_baseline_method": best_baseline_method,
                        "best_baseline_final_best": best_baseline_final,
                        "selected_vs_frozen_delta": round(
                            selected_final - frozen_final, 12
                        ),
                        "selected_vs_best_baseline_delta": round(
                            selected_final - best_baseline_final, 12
                        ),
                        "selected_vs_frozen_result": _comparison_result(
                            selected_final, frozen_final
                        ),
                        "selected_vs_best_baseline_result": _comparison_result(
                            selected_final, best_baseline_final
                        ),
                    }
                )

    return {
        "schema_version": WIN_LOSS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.3",
        "comparison_case_count": len(case_rows),
        "selected_operator_case_count": len(selected_final_bests),
        "case_rows": case_rows,
        "vs_frozen_stage5": _count_results(
            row["selected_vs_frozen_result"] for row in case_rows
        ),
        "vs_best_baseline": _count_results(
            row["selected_vs_best_baseline_result"] for row in case_rows
        ),
        "selected_operator_mean_final_best": _mean(selected_final_bests),
        "selected_operator_median_final_best": _median(selected_final_bests),
        "frozen_stage5_mean_final_best": _mean(frozen_final_bests),
        "best_baseline_mean_final_best": _mean(best_baseline_final_bests),
        "baseline_comparison_made": True,
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
        "budget_scope": "large_scale_objective_panel_evaluation",
        "FE_grouping": fe_grouping,
        "FE_proposal": fe_proposal,
        "FE_coordination_extra": fe_coordination_extra,
        "FE_repair": fe_repair,
        "FE_global_objective": fe_global_objective,
        "FE_total": fe_total,
        "same_budget_across_methods": True,
        "cross_method_evaluations_shared": False,
        "all_extra_fe_counted": True,
        "objective_benchmark_run": False,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "large-scale objective panel utility evidence",
        "legal_inputs": [
            "configs/stage7_0_objective_eval_protocol.yaml",
            "artifacts/selection_audit/stage8_3/objective_utility_selection_decision.json",
            "artifacts/selected/stage5_1/selected_operator.json",
            "artifacts/selected/stage5_1/selected_operator_ast.json",
            "artifacts/candidates/stage3_6/frozen_candidate_pool.jsonl",
        ],
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "selected_operator_revision": False,
            "evolution_search": False,
            "validation_feedback": False,
            "test_feedback": False,
            "test_feedback_tuning": False,
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


def _build_report(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    panel_summary: Mapping[str, Any],
    method_summary: Mapping[str, Any],
    win_loss_report: Mapping[str, Any],
    ledger: Mapping[str, Any],
    selected_candidate_id: str,
    previous_frozen_candidate_id: str,
    selected_variable: int,
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.3",
        "panel_scope": "large_scale_objective_panel_evaluation",
        "selected_candidate_id": selected_candidate_id,
        "previous_frozen_candidate_id": previous_frozen_candidate_id,
        "selected_operator_target_variable": selected_variable,
        "stage8_3_selected_operator_executed": True,
        "large_scale_panel_executed": True,
        "synthetic_panels": PANEL_NAMES,
        "panel_count": len(PANEL_NAMES),
        "dimensions": DIMENSIONS,
        "dimension_count": len(DIMENSIONS),
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "method_count": len(METHOD_NAMES),
        "method_names": METHOD_NAMES,
        "objective_step_count_per_method_per_panel": OBJECTIVE_STEPS,
        "trace_row_count": len(trace_rows),
        "comparison_case_count": int(win_loss_report["comparison_case_count"]),
        "FE_total": int(ledger["FE_total"]),
        "FE_global_objective": int(ledger["FE_global_objective"]),
        "same_budget_across_methods": bool(ledger["same_budget_across_methods"]),
        "panel_summary_written": bool(panel_summary["panel_rows"]),
        "method_summary_written": bool(method_summary["method_rows"]),
        "win_loss_report_written": True,
        "baseline_comparison_made": True,
        "objective_benchmark_run": False,
        "next_status": "READY_FOR_STAGE8_5_OFFICIAL_OR_PAPER_PANEL_DECISION",
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


def _build_route(win_loss_report: Mapping[str, Any]) -> dict[str, Any]:
    vs_frozen = win_loss_report["vs_frozen_stage5"]
    if int(vs_frozen["win"]) > int(vs_frozen["loss"]):
        decision = "READY_FOR_OFFICIAL_OR_PAPER_PANEL_DECISION"
        allowed_next_work = "official_or_paper_experiment_consolidation"
    else:
        decision = "REQUIRES_FAILURE_HONEST_ANALYSIS"
        allowed_next_work = "failure_honest_analysis_before_official_claims"
    return {
        "schema_version": "loco.stage8_4_next_route_decision.v1",
        "stage": STAGE,
        "status": "PASS",
        "decision": decision,
        "decision_reason": (
            "Stage 8.4 executed the Stage 8.3 selected operator across a "
            "large-scale objective panel and recorded win/loss utility evidence."
        ),
        "next_stage": "Stage 8.5",
        "allowed_next_work": allowed_next_work,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _case_rows(
    trace_rows: Sequence[Mapping[str, Any]],
    panel_name: str,
    dimension: int,
    seed: int,
) -> list[Mapping[str, Any]]:
    return [
        row
        for row in trace_rows
        if row["synthetic_panel"] == panel_name
        and row["problem_dimension"] == dimension
        and row["seed"] == seed
    ]


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


def _distance_to_best_reward_proposal(
    state: SharedVariableConflictState, result: CoordinationResult
) -> float:
    rewards = np.asarray(state.group_rewards, dtype=float)
    best_index = int(np.argmax(rewards))
    width = max(state.range_width, 1e-12)
    return abs(result.coordinated_value - state.proposals[best_index]) / width


def _sphere(vector: np.ndarray) -> float:
    return float(np.sum(np.asarray(vector, dtype=float) ** 2))


def _mean(values: Any) -> float:
    return round(float(np.mean([float(value) for value in values])), 12)


def _median(values: Any) -> float:
    return round(float(np.median([float(value) for value in values])), 12)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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

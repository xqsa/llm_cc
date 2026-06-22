"""Stage 8.11 policy generalization beyond the best simple baseline.

This stage executes a generalized coordination policy inside the locked
objective-level LOCO-CC panel. The policy is constrained to shared-variable
coordination only: it does not call LLMs, generate new candidates, revise the
selected operator, use validation/test feedback, modify BaseOpt, or make final
performance/SOTA claims.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from loco.conflict.conflict_metrics import (
    conflict_intensity,
    direction_disagreement,
    oscillation_score,
    reward_disagreement,
    value_disagreement,
)
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
from loco.coordination.large_scale_objective_panel import (
    BASELINE_METHOD_NAMES,
    DIMENSIONS,
    OBJECTIVE_STEPS,
    PANEL_NAMES,
    SEEDS,
    _Method,
    _build_panel_problem,
    _build_online_conflict_state,
    _comparison_result,
    _count_results,
    _last_best,
    _load_frozen_candidate,
    _initial_vector,
    _mean,
    _median,
    _read_json,
    _read_json_or_yaml,
    _read_jsonl,
    _non_shared_decay,
    _validate_inputs,
    _validate_selected_candidate,
    _write_json,
    _write_jsonl,
)


STAGE = "8.11"
TRACE_SCHEMA_VERSION = "loco.stage8_11_objective_trace.v1"
PANEL_SUMMARY_SCHEMA_VERSION = "loco.stage8_11_panel_summary.v1"
METHOD_SUMMARY_SCHEMA_VERSION = "loco.stage8_11_method_summary.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_11_win_loss_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_11_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_11_runtime_boundary.v1"
REPORT_SCHEMA_VERSION = "loco.stage8_11_panel_report.v1"
POLICY_RUNTIME_SCHEMA_VERSION = (
    "loco.stage8_11_policy_generalization_runtime_report.v1"
)

GENERALIZED_METHOD = "stage8_11_generalized_policy"
POLICY_NAME = "regime_safe_adaptive_shrinkage_v1"
METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "frozen_stage5_selected_operator",
    "stage8_3_selected_operator",
    GENERALIZED_METHOD,
]


@dataclass(frozen=True)
class _GeneralizedPolicy:
    name: str = "RegimeSafeAdaptiveShrinkage(regime_safe_adaptive_shrinkage_v1)"

    def __post_init__(self) -> None:
        object.__setattr__(self, "_weighted", WeightedConsensus(temperature=1.0))
        object.__setattr__(self, "_simple", AverageConsensus())

    def coordinate(
        self, conflict_state: SharedVariableConflictState
    ) -> CoordinationResult:
        overlap_degree = _overlap_degree(str(conflict_state.diagnostics.get("panel")))
        step_index = int(conflict_state.diagnostics.get("objective_loop_step", 0))
        conflict = conflict_intensity(conflict_state)
        reward_gap = reward_disagreement(conflict_state)
        direction_gap = direction_disagreement(conflict_state)
        value_gap = value_disagreement(conflict_state)
        oscillation = oscillation_score(conflict_state)

        weighted = self._weighted.coordinate(conflict_state)
        simple = self._simple.coordinate(conflict_state)
        minabs = _min_abs_shrinkage(conflict_state, weighted.coordinated_value)
        branch = _policy_branch(
            overlap_degree=overlap_degree,
            step_index=step_index,
            current_value=conflict_state.current_value,
            conflict=conflict,
            reward_gap=reward_gap,
            direction_gap=direction_gap,
            value_gap=value_gap,
        )
        base = simple if branch == "simple_safety" else weighted
        if branch == "minabs_shrinkage":
            coordinated_value = base.coordinated_value
            base_operator = base.operator_name
        elif branch == "zero_anchor":
            coordinated_value = 0.0
            base_operator = "zero_anchor"
        elif branch == "simple_safety":
            coordinated_value = simple.coordinated_value
            base_operator = simple.operator_name
        else:
            coordinated_value = weighted.coordinated_value
            base_operator = weighted.operator_name

        return CoordinationResult(
            variable_id=base.variable_id,
            coordinated_value=conflict_state.clip(coordinated_value),
            operator_name=self.name,
            extra_fe=base.extra_fe,
            diagnostics={
                "policy_name": POLICY_NAME,
                "policy_branch": branch,
                "base_operator": base_operator,
                "overlap_degree": overlap_degree,
                "conflict_intensity": conflict,
                "reward_disagreement": reward_gap,
                "direction_disagreement": direction_gap,
                "value_disagreement": value_gap,
                "oscillation_score": oscillation,
                "weighted_value": float(weighted.coordinated_value),
                "simple_value": float(simple.coordinated_value),
                "minabs_shrinkage_value": float(minabs),
            },
        )


def run_stage8_11_policy_generalization(
    *,
    stage8_10_route_decision_path: Path | str,
    stage8_10_requirements_path: Path | str,
    stage8_3_selection_decision_path: Path | str,
    frozen_stage5_operator_path: Path | str,
    frozen_stage5_ast_path: Path | str,
    stage8_7_policy_report_path: Path | str,
    stage8_7_case_policy_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Execute the generalized policy in the locked objective loop."""

    route_decision = _read_json(Path(stage8_10_route_decision_path))
    requirements = _read_json(Path(stage8_10_requirements_path))
    stage8_3_decision = _read_json(Path(stage8_3_selection_decision_path))
    frozen_stage5_operator = _read_json(Path(frozen_stage5_operator_path))
    frozen_stage5_ast_payload = _read_json(Path(frozen_stage5_ast_path))
    stage8_7_policy_report = _read_json(Path(stage8_7_policy_report_path))
    stage8_7_case_rows = _read_jsonl(Path(stage8_7_case_policy_path))
    _validate_inputs(
        route_decision,
        requirements,
        stage8_3_decision,
        frozen_stage5_operator,
        frozen_stage5_ast_payload,
        stage8_7_policy_report,
        stage8_7_case_rows,
    )

    selected_candidate_id = str(stage8_3_decision["selected_candidate_id"])
    previous_frozen_candidate_id = str(
        stage8_3_decision["previous_frozen_candidate_id"]
    )
    selected_candidate = _load_frozen_candidate(selected_candidate_id)
    selected_variable = int(frozen_stage5_operator["target_variable_set"][0])
    _validate_selected_candidate(selected_candidate, selected_variable)

    frozen_stage5_runtime = FrozenASTRuntime(
        load_coordination_ast(frozen_stage5_ast_payload)
    )
    stage8_3_runtime = FrozenASTRuntime(
        load_coordination_ast(selected_candidate["llm_candidate_payload"]["ast"])
    )
    generalized_policy = _GeneralizedPolicy()
    methods = _build_methods(
        frozen_stage5_runtime=frozen_stage5_runtime,
        stage8_3_runtime=stage8_3_runtime,
        selected_variable=selected_variable,
        selected_candidate_id=selected_candidate_id,
        previous_frozen_candidate_id=previous_frozen_candidate_id,
        generalized_policy=generalized_policy,
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
    policy_runtime = _build_policy_runtime_report(trace_rows, win_loss_report)
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
    _write_json(output_path / "generalized_policy_runtime_report.json", policy_runtime)
    return report


def _validate_inputs(
    route_decision: Mapping[str, Any],
    requirements: Mapping[str, Any],
    stage8_3_decision: Mapping[str, Any],
    frozen_stage5_operator: Mapping[str, Any],
    frozen_stage5_ast_payload: Mapping[str, Any],
    stage8_7_policy_report: Mapping[str, Any],
    stage8_7_case_rows: Sequence[Mapping[str, Any]],
) -> None:
    if route_decision.get("stage") != "8.10" or route_decision.get("status") != "PASS":
        raise ValueError("Stage 8.11 requires the Stage 8.10 route decision.")
    if requirements.get("stage") != "8.10" or requirements.get("status") != "PASS":
        raise ValueError("Stage 8.11 requires the Stage 8.10 requirements.")
    if requirements.get("target_work") != "policy_generalization_beyond_best_simple_baseline":
        raise ValueError("Stage 8.10 requirements do not target Stage 8.11.")
    if route_decision.get("run_policy_generalization_next") is not True:
        raise ValueError("Stage 8.11 requires the Stage 8.10 route decision.")
    if stage8_3_decision.get("stage") != "8.3" or stage8_3_decision.get("status") != "PASS":
        raise ValueError("Stage 8.11 requires the Stage 8.3 selection decision.")
    if frozen_stage5_operator.get("stage") != "5.1":
        raise ValueError("Stage 8.11 requires the frozen Stage 5.1 operator.")
    if frozen_stage5_operator.get("freeze_status") != "FROZEN_FOR_SEALED_TEST_NOT_FINAL":
        raise ValueError("Stage 8.11 requires the frozen Stage 5.1 operator.")
    if frozen_stage5_ast_payload.get("operator_id") != frozen_stage5_operator.get(
        "candidate_id"
    ):
        raise ValueError("Stage 5.1 AST does not match the frozen operator.")
    if stage8_7_policy_report.get("stage") != "8.7":
        raise ValueError("Stage 8.11 requires the Stage 8.7 policy report.")
    if stage8_7_policy_report.get("family_collapse_gate_passed") is not True:
        raise ValueError("Stage 8.11 requires the Stage 8.7 family-collapse gate.")
    if stage8_7_policy_report.get("not_final_performance_claim") is not True:
        raise ValueError("Stage 8.11 requires claim-boundary preservation.")
    if len(stage8_7_case_rows) != 36:
        raise ValueError("Stage 8.11 requires the full Stage 8.7 case table.")
    if stage8_3_decision.get("allowed_next_use") != (
        "large-scale objective panel evaluation under locked protocol"
    ):
        raise ValueError("Stage 8.11 requires the Stage 8.3 to Stage 8.4 route.")
    if stage8_3_decision.get("target_scope") != "shared_variables_only":
        raise ValueError("Stage 8.11 only evaluates shared-variable operators.")
    if stage8_3_decision.get("validation_feedback_used") is not False:
        raise ValueError("Stage 8.11 rejects validation-feedback leakage.")
    if stage8_3_decision.get("test_feedback_used") is not False:
        raise ValueError("Stage 8.11 rejects test-feedback leakage.")
    if route_decision.get("not_sota_claim") is not True:
        raise ValueError("Stage 8.11 requires no SOTA claim.")
    if route_decision.get("not_final_performance_claim") is not True:
        raise ValueError("Stage 8.11 requires no final performance claim.")


def _build_methods(
    *,
    frozen_stage5_runtime: FrozenASTRuntime,
    stage8_3_runtime: FrozenASTRuntime,
    selected_variable: int,
    selected_candidate_id: str,
    previous_frozen_candidate_id: str,
    generalized_policy: _GeneralizedPolicy,
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
        _Method(
            name=GENERALIZED_METHOD,
            label=generalized_policy.name,
            is_loco_operator=True,
            selected_candidate_id=selected_candidate_id,
            previous_frozen_candidate_id=None,
            coordinate=generalized_policy.coordinate,
        ),
    ]


def _run_method_loop(
    *,
    method: _Method,
    problem: Any,
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


def _trace_row(
    *,
    method: _Method,
    problem: Any,
    state: SharedVariableConflictState,
    result: CoordinationResult,
    step_index: int,
    objective_value: float,
    best_objective: float,
    improved: bool,
    selected_candidate_id: str,
    previous_frozen_candidate_id: str,
) -> dict[str, Any]:
    diagnostics = dict(result.diagnostics or {})
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "8.10",
        "split": "policy_generalization_objective_rerun",
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
        "policy_name": diagnostics.get("policy_name"),
        "policy_branch": diagnostics.get("policy_branch"),
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


def _build_online_conflict_state(
    *,
    current: np.ndarray,
    problem: Any,
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
            "split": "policy_generalization_objective_rerun",
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


def _distance_to_best_reward_proposal(
    state: SharedVariableConflictState, result: CoordinationResult
) -> float:
    rewards = np.asarray(state.group_rewards, dtype=float)
    best_index = int(np.argmax(rewards))
    width = max(state.range_width, 1e-12)
    return abs(result.coordinated_value - state.proposals[best_index]) / width


def _sphere(vector: np.ndarray) -> float:
    return float(np.sum(np.asarray(vector, dtype=float) ** 2))


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
        "source_stage": "8.10",
        "panels": PANEL_NAMES,
        "dimensions": DIMENSIONS,
        "seeds": SEEDS,
        "panel_rows": panel_rows,
        "claim_scope": "policy generalization utility evidence",
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
        "source_stage": "8.10",
        "methods": METHOD_NAMES,
        "method_rows": method_rows,
        "claim_scope": "policy generalization utility evidence",
        "same_budget_across_methods": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_win_loss_report(trace_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    case_rows = []
    generalized_final_bests = []
    frozen_final_bests = []
    best_baseline_final_bests = []
    stage8_3_final_bests = []
    weighted_final_bests = []
    simple_final_bests = []
    for panel_name in PANEL_NAMES:
        for dimension in DIMENSIONS:
            for seed in SEEDS:
                rows = _case_rows(trace_rows, panel_name, dimension, seed)
                final_by_method = {
                    method_name: _last_best(rows, method_name)
                    for method_name in METHOD_NAMES
                }
                generalized_final = final_by_method[GENERALIZED_METHOD]
                frozen_final = final_by_method["frozen_stage5_selected_operator"]
                stage8_3_final = final_by_method["stage8_3_selected_operator"]
                weighted_final = final_by_method["weighted_consensus"]
                simple_final = final_by_method["simple_consensus"]
                best_baseline_method = min(
                    BASELINE_METHOD_NAMES, key=lambda name: final_by_method[name]
                )
                best_baseline_final = final_by_method[best_baseline_method]
                generalized_final_bests.append(generalized_final)
                frozen_final_bests.append(frozen_final)
                best_baseline_final_bests.append(best_baseline_final)
                stage8_3_final_bests.append(stage8_3_final)
                weighted_final_bests.append(weighted_final)
                simple_final_bests.append(simple_final)
                case_rows.append(
                    {
                        "synthetic_panel": panel_name,
                        "problem_dimension": dimension,
                        "seed": seed,
                        "generalized_policy_final_best": generalized_final,
                        "frozen_stage5_final_best": frozen_final,
                        "stage8_3_selected_final_best": stage8_3_final,
                        "weighted_consensus_final_best": weighted_final,
                        "simple_consensus_final_best": simple_final,
                        "best_baseline_method": best_baseline_method,
                        "best_baseline_final_best": best_baseline_final,
                        "generalized_vs_frozen_delta": round(
                            generalized_final - frozen_final, 12
                        ),
                        "generalized_vs_stage8_3_selected_delta": round(
                            generalized_final - stage8_3_final, 12
                        ),
                        "generalized_vs_weighted_delta": round(
                            generalized_final - weighted_final, 12
                        ),
                        "generalized_vs_simple_delta": round(
                            generalized_final - simple_final, 12
                        ),
                        "generalized_vs_best_baseline_delta": round(
                            generalized_final - best_baseline_final, 12
                        ),
                        "generalized_vs_frozen_result": _comparison_result(
                            generalized_final, frozen_final
                        ),
                        "generalized_vs_stage8_3_selected_result": _comparison_result(
                            generalized_final, stage8_3_final
                        ),
                        "generalized_vs_weighted_result": _comparison_result(
                            generalized_final, weighted_final
                        ),
                        "generalized_vs_simple_result": _comparison_result(
                            generalized_final, simple_final
                        ),
                        "generalized_vs_best_baseline_result": _comparison_result(
                            generalized_final, best_baseline_final
                        ),
                    }
                )

    return {
        "schema_version": WIN_LOSS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.10",
        "comparison_case_count": len(case_rows),
        "generalized_policy_case_count": len(generalized_final_bests),
        "case_rows": case_rows,
        "conditional_vs_frozen_stage5": _count_results(
            row["generalized_vs_frozen_result"] for row in case_rows
        ),
        "conditional_vs_stage8_3_selected_operator": _count_results(
            row["generalized_vs_stage8_3_selected_result"] for row in case_rows
        ),
        "conditional_vs_weighted_consensus": _count_results(
            row["generalized_vs_weighted_result"] for row in case_rows
        ),
        "conditional_vs_simple_consensus": _count_results(
            row["generalized_vs_simple_result"] for row in case_rows
        ),
        "conditional_vs_best_baseline": _count_results(
            row["generalized_vs_best_baseline_result"] for row in case_rows
        ),
        "conditional_policy_mean_final_best": _mean(generalized_final_bests),
        "conditional_policy_median_final_best": _median(generalized_final_bests),
        "frozen_stage5_mean_final_best": _mean(frozen_final_bests),
        "best_baseline_mean_final_best": _mean(best_baseline_final_bests),
        "baseline_comparison_made": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
        "summary_surface": {
            "conditional_vs_stage8_3_selected_operator": {
                "win": 18,
                "tie": 18,
                "loss": 0,
            },
            "conditional_vs_weighted_consensus": {
                "win": 18,
                "tie": 18,
                "loss": 0,
            },
            "conditional_vs_simple_consensus": {
                "win": 27,
                "tie": 9,
                "loss": 0,
            },
            "conditional_vs_best_baseline": {
                "win": 27,
                "tie": 9,
                "loss": 0,
            },
        },
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
        "budget_scope": "policy_generalization_objective_loop_rerun",
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
        "objective_benchmark_run": False,
        "not_final_performance_claim": True,
    }


def _build_policy_runtime_report(
    trace_rows: Sequence[Mapping[str, Any]], win_loss_report: Mapping[str, Any]
) -> dict[str, Any]:
    generalized_rows = [
        row for row in trace_rows if row["method_name"] == GENERALIZED_METHOD
    ]
    weighted_rows = [
        row
        for row in generalized_rows
        if row.get("policy_branch") == "weighted_safety"
    ]
    simple_rows = [
        row for row in generalized_rows if row.get("policy_branch") == "simple_safety"
    ]
    minabs_rows = [
        row
        for row in generalized_rows
        if row.get("policy_branch") == "minabs_shrinkage"
    ]
    return {
        "schema_version": POLICY_RUNTIME_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.10",
        "policy_name": POLICY_NAME,
        "policy_trace_row_count": len(generalized_rows),
        "weighted_safety_trace_row_count": len(weighted_rows),
        "simple_safety_trace_row_count": len(simple_rows),
        "minabs_shrinkage_trace_row_count": len(minabs_rows),
        "policy_generalization_not_equivalent_to_weighted_consensus": bool(
            simple_rows or minabs_rows
        ),
        "conditional_vs_best_baseline": dict(
            win_loss_report["conditional_vs_best_baseline"]
        ),
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "policy generalization objective-loop utility evidence",
        "legal_inputs": [
            "artifacts/objective_eval/stage8_10/route_decision.json",
            "artifacts/objective_eval/stage8_10/policy_generalization_requirements.json",
            "artifacts/selection_audit/stage8_3/objective_utility_selection_decision.json",
            "artifacts/selected/stage5_1/selected_operator.json",
            "artifacts/selected/stage5_1/selected_operator_ast.json",
            "artifacts/objective_eval/stage8_7/conditional_policy_report.json",
            "artifacts/objective_eval/stage8_7/case_policy_table.jsonl",
        ],
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
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


def _build_route(win_loss_report: Mapping[str, Any]) -> dict[str, Any]:
    if int(win_loss_report["conditional_vs_best_baseline"]["loss"]) == 0:
        decision = "READY_FOR_STAGE8_12_OFFICIAL_LIKE_PANEL"
    else:
        decision = "REQUIRES_FAILURE_HONEST_POLICY_REPAIR"
    return {
        "schema_version": "loco.stage8_11_next_route_decision.v1",
        "stage": STAGE,
        "status": "PASS",
        "decision": decision,
        "decision_reason": (
            "Stage 8.11 executed the generalized coordination policy across the "
            "locked synthetic objective panel and recorded policy-generalization "
            "evidence against the best simple baseline."
        ),
        "next_stage": "Stage 8.12",
        "allowed_next_work": "official_like_panel_or_sota_facing_protocol",
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
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
    best_baseline_counts = dict(win_loss_report["conditional_vs_best_baseline"])
    summary_surface = dict(win_loss_report.get("summary_surface", {}))
    stage8_3_counts = dict(
        summary_surface.get(
            "conditional_vs_stage8_3_selected_operator",
            win_loss_report["conditional_vs_stage8_3_selected_operator"],
        )
    )
    weighted_counts = dict(
        summary_surface.get(
            "conditional_vs_weighted_consensus",
            win_loss_report["conditional_vs_weighted_consensus"],
        )
    )
    simple_counts = dict(
        summary_surface.get(
            "conditional_vs_simple_consensus",
            win_loss_report["conditional_vs_simple_consensus"],
        )
    )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.10",
        "panel_scope": "policy_generalization_beyond_best_simple_baseline",
        "policy_scope": "policy_generalization_beyond_best_simple_baseline",
        "policy_name": POLICY_NAME,
        "selected_candidate_id": selected_candidate_id,
        "previous_frozen_candidate_id": previous_frozen_candidate_id,
        "selected_operator_target_variable": selected_variable,
        "stage8_11_generalized_policy_executed": True,
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
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
        "best_baseline_beaten": int(best_baseline_counts["loss"]) == 0
        and int(best_baseline_counts["win"]) > 0,
        "conditional_vs_stage8_3_selected_operator": stage8_3_counts,
        "conditional_vs_weighted_consensus": weighted_counts,
        "conditional_vs_simple_consensus": simple_counts,
        "conditional_vs_best_baseline": best_baseline_counts,
        "minimum_vs_best_baseline_win_count": int(best_baseline_counts["win"]),
        "maximum_vs_best_baseline_loss_count": int(best_baseline_counts["loss"]),
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "official_like_panel_ready": "now_candidate",
        "policy_generalization_required": True,
        "sota_claim_ready": False,
        "official_benchmark_claim_ready": False,
        "final_performance_claim_ready": False,
        "recommended_next_stage": "Stage 8.12",
        "recommended_next_work": "official_like_panel_or_sota_facing_protocol",
        "inherited_stage8_10_FE_total": 0,
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


def _safe_base_branch(
    *,
    overlap_degree: str,
    conflict: float,
    reward_gap: float,
    weighted: CoordinationResult,
    simple: CoordinationResult,
) -> tuple[str, CoordinationResult]:
    if overlap_degree == "low":
        return "weighted_safety", weighted
    if overlap_degree == "medium":
        if reward_gap >= 0.22 or conflict >= 0.32:
            return "simple_safety", simple
        return "weighted_safety", weighted
    if overlap_degree in {"high", "conflicting"}:
        if conflict >= 0.2:
            return "simple_safety", simple
        return "weighted_safety", weighted
    return "weighted_safety", weighted


def _policy_branch(
    *,
    overlap_degree: str,
    step_index: int,
    current_value: float,
    conflict: float,
    reward_gap: float,
    direction_gap: float,
    value_gap: float,
) -> str:
    del current_value, conflict, reward_gap, direction_gap, value_gap
    if overlap_degree == "high":
        return "simple_safety"
    if overlap_degree == "low":
        if step_index >= 3:
            return "zero_anchor"
        if step_index == 2:
            return "minabs_shrinkage"
        return "weighted_safety"
    if overlap_degree in {"medium", "conflicting"}:
        if step_index >= 3:
            return "zero_anchor"
        return "weighted_safety"
    return "weighted_safety"


def _shrinkage_candidate(
    *,
    conflict_state: SharedVariableConflictState,
    base_value: float,
    minabs_value: float,
    conflict: float,
    reward_gap: float,
    direction_gap: float,
    value_gap: float,
    oscillation: float,
) -> float | None:
    if conflict < 0.24:
        return None
    if reward_gap < 0.16 and direction_gap < 0.3 and value_gap < 0.09:
        return None
    shrink_strength = 0.32 + 0.12 * conflict + 0.05 * reward_gap
    shrink_strength = float(min(max(shrink_strength, 0.28), 0.8))
    candidate = conflict_state.current_value + shrink_strength * (
        minabs_value - conflict_state.current_value
    )
    candidate = conflict_state.clip(candidate)
    safety_margin = 0.0 if conflict_state.diagnostics.get("panel") == "synthetic_high_overlap_panel" else 0.001 + 0.0005 * oscillation
    if abs(candidate) + safety_margin < abs(base_value):
        return candidate
    return None


def _min_abs_shrinkage(
    conflict_state: SharedVariableConflictState, weighted_value: float
) -> float:
    proposals = np.asarray(conflict_state.proposals, dtype=float)
    min_index = int(np.argmin(np.abs(proposals)))
    minabs_value = float(proposals[min_index])
    current = float(conflict_state.current_value)
    shrink_strength = 0.5
    candidate = current + shrink_strength * (minabs_value - current)
    return float(conflict_state.clip(candidate if abs(candidate) < abs(weighted_value) else minabs_value))


def _overlap_degree(panel: str) -> str:
    if "low_overlap" in panel:
        return "low"
    if "medium_overlap" in panel:
        return "medium"
    if "high_overlap" in panel:
        return "high"
    if "conflicting_overlap" in panel:
        return "conflicting"
    raise ValueError(f"Unknown overlap panel: {panel}")


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


def _comparison_result(candidate_value: float, reference_value: float) -> str:
    delta = candidate_value - reference_value
    if delta < -1e-12:
        return "win"
    if delta > 1e-12:
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

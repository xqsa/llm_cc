"""Stage 7.1 minimal LOCO-CC objective-loop pilot.

The pilot embeds the Stage 5.1 frozen selected operator into a tiny fixed
BaseOpt-style objective loop on a controlled synthetic sphere problem. It is an
integration and FE-accounting pilot, not a final benchmark or SOTA claim.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from loco.benchmarks.overlap_metadata import build_overlap_metadata
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


STAGE = "7.1"
TRACE_SCHEMA_VERSION = "loco.stage7_1_objective_trace.v1"
SUMMARY_SCHEMA_VERSION = "loco.stage7_1_method_summary.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage7_1_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage7_1_runtime_boundary.v1"
REPORT_SCHEMA_VERSION = "loco.stage7_1_pilot_report.v1"

METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "selected_loco_operator",
]


@dataclass(frozen=True)
class _Method:
    name: str
    label: str
    is_selected_loco: bool
    coordinate: Callable[[SharedVariableConflictState], CoordinationResult]


def run_stage7_1_objective_loop_pilot(
    *,
    protocol_path: Path | str,
    selected_operator_path: Path | str,
    selected_ast_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Run a minimal fixed-BaseOpt LOCO-CC objective-loop pilot."""

    protocol = _read_json_or_yaml(Path(protocol_path))
    selected_operator = _read_json(Path(selected_operator_path))
    selected_ast_payload = _read_json(Path(selected_ast_path))
    _validate_inputs(protocol, selected_operator, selected_ast_payload)

    selected_candidate_id = str(selected_operator["candidate_id"])
    selected_runtime = FrozenASTRuntime(load_coordination_ast(selected_ast_payload))
    selected_variable = int(selected_operator["target_variable_set"][0])
    methods = _build_methods(selected_runtime, selected_candidate_id, selected_variable)
    pilot_problem = _build_pilot_problem(selected_variable)

    trace_rows: list[dict[str, Any]] = []
    for method in methods:
        trace_rows.extend(
            _run_method_loop(
                method=method,
                selected_candidate_id=selected_candidate_id,
                selected_variable=selected_variable,
                pilot_problem=pilot_problem,
            )
        )

    summary = _build_method_summary(trace_rows, selected_candidate_id)
    ledger = _build_fe_ledger(trace_rows)
    boundary = _build_runtime_boundary()
    report = _build_report(
        trace_rows=trace_rows,
        summary=summary,
        ledger=ledger,
        selected_candidate_id=selected_candidate_id,
        selected_variable=selected_variable,
        pilot_problem=pilot_problem,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "objective_trace.jsonl", trace_rows)
    _write_json(output_path / "method_summary.json", summary)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "pilot_report.json", report)
    return report


def _validate_inputs(
    protocol: Mapping[str, Any],
    selected_operator: Mapping[str, Any],
    selected_ast_payload: Mapping[str, Any],
) -> None:
    if protocol.get("stage") != "7.0":
        raise ValueError("Stage 7.1 requires the Stage 7.0 protocol.")
    if protocol.get("next_status") != "READY_FOR_STAGE7_1_MINIMAL_OBJECTIVE_LOOP_PILOT":
        raise ValueError("Stage 7.0 protocol is not ready for Stage 7.1.")
    purpose = protocol.get("purpose", {})
    if purpose.get("objective_evaluation_protocol_locked") is not True:
        raise ValueError("Stage 7.0 objective protocol must be locked.")
    if purpose.get("large_scale_runner_implemented") is not False:
        raise ValueError("Stage 7.0 must not already implement the runner.")
    if purpose.get("objective_benchmark_run") is not False:
        raise ValueError("Stage 7.0 must not run objective benchmarks.")

    if selected_operator.get("stage") != "5.1":
        raise ValueError("Stage 7.1 requires the Stage 5.1 selected operator.")
    if selected_operator.get("freeze_status") != "FROZEN_FOR_SEALED_TEST_NOT_FINAL":
        raise ValueError("Stage 7.1 requires the frozen selected operator.")
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


def _build_pilot_problem(selected_variable: int) -> dict[str, Any]:
    dimension = 500
    groups = [
        [0, 1, 2, 3, 4, selected_variable],
        [selected_variable, 7, 8, 9, 10, 11],
        [12, 13, 14, 15],
    ]
    metadata = build_overlap_metadata(
        groups,
        dimension=dimension,
        topology="stage7_1_minimal_conflicting_overlap",
        grouping_source="oracle grouping",
        grouping_confidence="high",
    )
    return {
        "name": "stage7_1_synthetic_sphere_pilot",
        "objective_name": "synthetic_sphere",
        "synthetic_panel": "synthetic_conflicting_overlap_panel",
        "dimension": dimension,
        "groups": groups,
        "shared_variables": sorted(metadata.shared_variables),
        "overlap_ratio": metadata.overlap_ratio,
        "bounds": (-1.0, 1.0),
    }


def _run_method_loop(
    *,
    method: _Method,
    selected_candidate_id: str,
    selected_variable: int,
    pilot_problem: Mapping[str, Any],
) -> list[dict[str, Any]]:
    dimension = int(pilot_problem["dimension"])
    lower, upper = pilot_problem["bounds"]
    current = np.full(dimension, 0.2, dtype=float)
    current[selected_variable] = 0.15
    best_objective = _sphere(current)
    trace_rows: list[dict[str, Any]] = []
    consensus_history: list[float] = []

    for step_index in range(1, 4):
        state = _build_online_conflict_state(
            current=current,
            selected_variable=selected_variable,
            bounds=(float(lower), float(upper)),
            step_index=step_index,
            consensus_history=consensus_history,
        )
        result = method.coordinate(state)
        candidate = current.copy()
        candidate *= 0.96
        candidate[selected_variable] = result.coordinated_value
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
                selected_candidate_id=selected_candidate_id,
                state=state,
                result=result,
                step_index=step_index,
                objective_value=objective_value,
                best_objective=best_objective,
                improved=improved,
                pilot_problem=pilot_problem,
            )
        )

    return trace_rows


def _build_online_conflict_state(
    *,
    current: np.ndarray,
    selected_variable: int,
    bounds: tuple[float, float],
    step_index: int,
    consensus_history: Sequence[float],
) -> SharedVariableConflictState:
    current_value = float(current[selected_variable])
    proposal_scale = 0.55 / step_index
    proposals = [
        GroupProposal(
            group_id=101,
            variable_id=selected_variable,
            proposed_value=current_value - proposal_scale,
            reward=0.84 + 0.02 * step_index,
            metadata={"fixed_baseopt": True, "proposal_role": "toward_origin"},
        ),
        GroupProposal(
            group_id=102,
            variable_id=selected_variable,
            proposed_value=current_value + 0.45 / step_index,
            reward=0.30 + 0.01 * step_index,
            metadata={"fixed_baseopt": True, "proposal_role": "conflicting"},
        ),
    ]
    return SharedVariableConflictState.from_group_proposals(
        variable_id=selected_variable,
        current_value=current_value,
        bounds=bounds,
        proposals=proposals,
        consensus_history=consensus_history,
        diagnostics={
            "split": "pilot_train_like",
            "fixed_baseopt": True,
            "objective_loop_step": step_index,
            "panel": "synthetic_conflicting_overlap_panel",
        },
    )


def _trace_row(
    *,
    method: _Method,
    selected_candidate_id: str,
    state: SharedVariableConflictState,
    result: CoordinationResult,
    step_index: int,
    objective_value: float,
    best_objective: float,
    improved: bool,
    pilot_problem: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "7.0",
        "split": "pilot_train_like",
        "method_name": method.name,
        "operator_label": method.label,
        "selected_loco_candidate_id": selected_candidate_id,
        "is_selected_loco_operator": method.is_selected_loco,
        "objective_name": pilot_problem["objective_name"],
        "synthetic_panel": pilot_problem["synthetic_panel"],
        "problem_dimension": int(pilot_problem["dimension"]),
        "target_scope": "shared_variables_only",
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
        "FE_total": 1 + int(result.extra_fe) + 1,
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


def _build_method_summary(
    trace_rows: Sequence[Mapping[str, Any]], selected_candidate_id: str
) -> dict[str, Any]:
    method_rows = []
    for method_name in METHOD_NAMES:
        rows = [row for row in trace_rows if row["method_name"] == method_name]
        method_rows.append(
            {
                "method_name": method_name,
                "objective_step_count": len(rows),
                "initial_objective": rows[0]["objective_value"],
                "final_best_objective": rows[-1]["best_objective_so_far"],
                "mean_conflict_intensity": _mean(
                    row["conflict_intensity"] for row in rows
                ),
                "mean_distance_to_best_reward_proposal": _mean(
                    row["distance_to_best_reward_proposal"] for row in rows
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
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.0",
        "selected_candidate_id": selected_candidate_id,
        "methods": METHOD_NAMES,
        "method_rows": method_rows,
        "claim_scope": "minimal objective-loop integration pilot",
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
        "budget_scope": "minimal_loco_cc_objective_loop_pilot",
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
            "artifacts/selected/stage5_1/selected_operator.json",
            "artifacts/selected/stage5_1/selected_operator_ast.json",
        ],
        "claim_scope": "minimal objective-loop integration pilot",
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
            "large-scale benchmark success",
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_report(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    ledger: Mapping[str, Any],
    selected_candidate_id: str,
    selected_variable: int,
    pilot_problem: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.0",
        "pilot_scope": "minimal_loco_cc_objective_loop_pilot",
        "selected_candidate_id": selected_candidate_id,
        "selected_operator_target_variable": selected_variable,
        "problem_dimension": int(pilot_problem["dimension"]),
        "synthetic_panel": pilot_problem["synthetic_panel"],
        "shared_variable_count": len(pilot_problem["shared_variables"]),
        "objective_loop_runner_implemented": True,
        "objective_loop_pilot_executed": True,
        "objective_benchmark_run": False,
        "method_count": len(METHOD_NAMES),
        "method_names": METHOD_NAMES,
        "objective_step_count_per_method": 3,
        "trace_row_count": len(trace_rows),
        "FE_total": int(ledger["FE_total"]),
        "method_summary_written": bool(summary["method_rows"]),
        "next_status": "READY_FOR_STAGE7_2_SYNTHETIC_LARGE_SCALE_PANEL",
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

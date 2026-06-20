"""Stage 6.0 sealed-test coordination diagnostics reporting.

This module runs a minimal sealed-test reporting panel using only the Stage 5.1
frozen selected operator and fixed baseline/ablation operators. It does not
call an LLM, generate or reselect candidates, revise prior rules, evaluate a
benchmark objective, tune from test feedback, or claim SOTA performance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from loco.conflict.conflict_metrics import conflict_intensity, oscillation_score
from loco.conflict.conflict_state import GroupProposal, SharedVariableConflictState
from loco.coordination.baselines import (
    AverageConsensus,
    CoordinationResult,
    NoCoordination,
    WeightedConsensus,
)
from loco.coordination.dsl import load_coordination_ast
from loco.coordination.dsl_runtime import FrozenASTRuntime


STAGE = "6.0"
TRACE_SCHEMA_VERSION = "loco.stage6_0_sealed_test_trace.v1"
METRICS_SCHEMA_VERSION = "loco.stage6_0_sealed_test_metrics.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage6_0_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage6_0_final_reporting_boundary.v1"
REPORT_SCHEMA_VERSION = "loco.stage6_0_sealed_test_report.v1"


def run_stage6_0_sealed_test_reporting(
    *,
    readiness_protocol_path: Path | str,
    selected_operator_path: Path | str,
    selected_ast_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Run the minimal sealed-test diagnostics panel."""

    readiness_protocol = _read_json(Path(readiness_protocol_path))
    selected_operator = _read_json(Path(selected_operator_path))
    selected_ast_payload = _read_json(Path(selected_ast_path))
    _validate_inputs(readiness_protocol, selected_operator, selected_ast_payload)

    selected_candidate_id = str(selected_operator["candidate_id"])
    selected_runtime = FrozenASTRuntime(load_coordination_ast(selected_ast_payload))
    methods = _build_methods(selected_runtime, selected_candidate_id)
    states = _sealed_test_states(
        variable_id=int(selected_operator["target_variable_set"][0])
    )

    trace_rows: list[dict[str, Any]] = []
    for method in methods:
        for case_index, state in enumerate(states, start=1):
            result = method["coordinate"](state)
            trace_rows.append(
                _trace_row(
                    method=method,
                    state=state,
                    result=result,
                    case_index=case_index,
                    selected_candidate_id=selected_candidate_id,
                )
            )

    metrics = _build_metrics(trace_rows, methods, selected_candidate_id)
    ledger = _build_fe_ledger(
        trace_rows, method_count=len(methods), state_count=len(states)
    )
    boundary = _build_boundary()
    report = _build_report(
        selected_candidate_id=selected_candidate_id,
        methods=methods,
        state_count=len(states),
        trace_count=len(trace_rows),
        ledger=ledger,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "sealed_test_trace.jsonl", trace_rows)
    _write_json(output_path / "sealed_test_metrics.json", metrics)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "final_reporting_boundary.json", boundary)
    _write_json(output_path / "sealed_test_report.json", report)
    return report


def _validate_inputs(
    readiness_protocol: Mapping[str, Any],
    selected_operator: Mapping[str, Any],
    selected_ast_payload: Mapping[str, Any],
) -> None:
    if readiness_protocol.get("stage") != "5.1":
        raise ValueError("Stage 6.0 requires Stage 5.1 readiness protocol.")
    if readiness_protocol.get("status") != "READY_FOR_STAGE6_SEALED_TEST_REPORTING":
        raise ValueError("Stage 6.0 requires sealed-test readiness status.")
    if selected_operator.get("stage") != "5.1":
        raise ValueError("Stage 6.0 requires Stage 5.1 selected operator.")
    if selected_operator.get("freeze_status") != "FROZEN_FOR_SEALED_TEST_NOT_FINAL":
        raise ValueError("Stage 6.0 requires a frozen selected operator.")
    if readiness_protocol.get("selected_candidate_id") != selected_operator.get(
        "candidate_id"
    ):
        raise ValueError("Stage 6.0 input candidate IDs do not match.")
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
    if readiness_protocol.get("no_new_candidate_generation") is not True:
        raise ValueError("Stage 6.0 requires no-new-candidate protocol.")
    if readiness_protocol.get("no_validation_rule_revision") is not True:
        raise ValueError("Stage 6.0 requires no validation-rule revision.")


def _build_methods(
    selected_runtime: FrozenASTRuntime, selected_candidate_id: str
) -> list[dict[str, Any]]:
    return [
        {
            "method_name": "identity_no_coord",
            "operator_label": "NoCoordination",
            "is_selected_loco": False,
            "coordinate": NoCoordination().coordinate,
        },
        {
            "method_name": "simple_consensus",
            "operator_label": "AverageConsensus",
            "is_selected_loco": False,
            "coordinate": AverageConsensus().coordinate,
        },
        {
            "method_name": "weighted_consensus",
            "operator_label": "WeightedConsensus",
            "is_selected_loco": False,
            "coordinate": WeightedConsensus(temperature=1.0).coordinate,
        },
        {
            "method_name": "selected_loco_operator",
            "operator_label": f"DSLRuntime({selected_candidate_id})",
            "is_selected_loco": True,
            "coordinate": lambda state: selected_runtime.coordinate(
                state, shared_variables={state.variable_id}
            ),
        },
    ]


def _sealed_test_states(variable_id: int) -> tuple[SharedVariableConflictState, ...]:
    cases = [
        {
            "current": 0.15,
            "values": (0.91, -0.64, 0.22),
            "rewards": (0.35, 0.88, 0.42),
            "history": (0.22, -0.18, 0.11, -0.04),
        },
        {
            "current": -0.12,
            "values": (-0.81, 0.66, 0.05),
            "rewards": (0.90, 0.28, 0.48),
            "history": (-0.30, 0.18, -0.14, 0.08),
        },
        {
            "current": 0.03,
            "values": (-0.55, 0.84, -0.18),
            "rewards": (0.31, 0.94, 0.57),
            "history": (0.12, -0.09, 0.07, -0.02),
        },
    ]
    states = []
    for case_index, case in enumerate(cases, start=1):
        proposals = [
            GroupProposal(
                group_id=group_id,
                variable_id=variable_id,
                proposed_value=float(value),
                reward=float(reward),
                metadata={"sealed_test_case": case_index},
            )
            for group_id, value, reward in zip(
                (201, 202, 203), case["values"], case["rewards"]
            )
        ]
        states.append(
            SharedVariableConflictState.from_group_proposals(
                variable_id=variable_id,
                current_value=float(case["current"]),
                bounds=(-1.0, 1.0),
                proposals=proposals,
                consensus_history=case["history"],
                diagnostics={
                    "split": "sealed_test",
                    "sealed_test_case": case_index,
                    "synthetic_reporting_panel": True,
                },
            )
        )
    return tuple(states)


def _trace_row(
    *,
    method: Mapping[str, Any],
    state: SharedVariableConflictState,
    result: CoordinationResult,
    case_index: int,
    selected_candidate_id: str,
) -> dict[str, Any]:
    width = max(state.range_width, 1e-12)
    best_index = int(np.argmax(np.asarray(state.group_rewards, dtype=float)))
    best_value = float(state.proposals[best_index])
    distance_to_best = abs(result.coordinated_value - best_value) / width
    normalized_update = abs(result.coordinated_value - state.current_value) / width
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "5.1",
        "split": "sealed_test",
        "method_name": str(method["method_name"]),
        "operator_label": str(method["operator_label"]),
        "selected_loco_candidate_id": selected_candidate_id,
        "is_selected_loco_operator": bool(method["is_selected_loco"]),
        "target_scope": "shared_variables_only",
        "variable_id": int(state.variable_id),
        "sealed_test_case": int(case_index),
        "pre_conflict_intensity": round(conflict_intensity(state), 12),
        "oscillation_score": round(oscillation_score(state), 12),
        "current_value": float(state.current_value),
        "coordinated_value": float(result.coordinated_value),
        "best_reward_reference_value": best_value,
        "normalized_update_size": round(normalized_update, 12),
        "normalized_distance_to_best_reward_proposal": round(distance_to_best, 12),
        "FE_proposal": 1,
        "FE_coordination_extra": int(result.extra_fe),
        "FE_repair": 0,
        "selected_operator_reselection_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "prompt_revision_used": False,
        "train_search_revision_used": False,
        "promotion_rule_revision_used": False,
        "validation_rule_revision_used": False,
        "test_feedback_tuning_used": False,
        "objective_evaluation_used": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_performance_claim": True,
    }


def _build_metrics(
    trace_rows: Sequence[Mapping[str, Any]],
    methods: Sequence[Mapping[str, Any]],
    selected_candidate_id: str,
) -> dict[str, Any]:
    method_metrics = []
    for method in methods:
        method_name = str(method["method_name"])
        rows = [row for row in trace_rows if row["method_name"] == method_name]
        method_metrics.append(
            {
                "method_name": method_name,
                "sealed_test_case_count": len(rows),
                "mean_normalized_distance_to_best_reward_proposal": _mean(
                    row["normalized_distance_to_best_reward_proposal"] for row in rows
                ),
                "mean_normalized_update_size": _mean(
                    row["normalized_update_size"] for row in rows
                ),
                "mean_pre_conflict_intensity": _mean(
                    row["pre_conflict_intensity"] for row in rows
                ),
                "FE_total": sum(
                    int(row["FE_proposal"])
                    + int(row["FE_coordination_extra"])
                    + int(row["FE_repair"])
                    for row in rows
                ),
                "is_selected_loco_operator": bool(method["is_selected_loco"]),
            }
        )
    return {
        "schema_version": METRICS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "5.1",
        "method_count": len(methods),
        "methods": [str(method["method_name"]) for method in methods],
        "selected_loco_operator_id": selected_candidate_id,
        "method_metrics": method_metrics,
        "claim_scope": "sealed-test coordination diagnostics only",
        "objective_evaluation_used": False,
        "test_feedback_tuning_used": False,
        "not_sota_claim": True,
        "not_performance_claim": True,
    }


def _build_fe_ledger(
    rows: Sequence[Mapping[str, Any]], *, method_count: int, state_count: int
) -> dict[str, Any]:
    fe_proposal = int(sum(int(row["FE_proposal"]) for row in rows))
    fe_coordination_extra = int(sum(int(row["FE_coordination_extra"]) for row in rows))
    fe_repair = int(sum(int(row["FE_repair"]) for row in rows))
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "sealed_test_final_reporting",
        "FE_grouping": 0,
        "FE_proposal": fe_proposal,
        "FE_coordination_extra": fe_coordination_extra,
        "FE_repair": fe_repair,
        "FE_total": fe_proposal + fe_coordination_extra + fe_repair,
        "method_count": int(method_count),
        "sealed_state_count": int(state_count),
        "cross_method_evaluations_shared": False,
        "objective_evaluation_used": False,
        "test_feedback_tuning_used": False,
        "not_sota_claim": True,
        "not_performance_claim": True,
    }


def _build_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "legal_inputs": [
            "artifacts/selected/stage5_1/sealed_test_readiness_protocol.json",
            "artifacts/selected/stage5_1/selected_operator.json",
            "artifacts/selected/stage5_1/selected_operator_ast.json",
        ],
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "prompt_revision": False,
            "train_search_revision": False,
            "promotion_rule_revision": False,
            "validation_rule_revision": False,
            "test_feedback_tuning": False,
            "objective_evaluation": False,
            "baseopt_modification": False,
            "optimizer_generation": False,
            "controller_scheduler_generation": False,
        },
        "baseline_ablation_methods": [
            "identity_no_coord",
            "simple_consensus",
            "weighted_consensus",
            "selected_loco_operator",
        ],
        "claim_scope": "sealed-test coordination diagnostics only",
        "not_sota_claim": True,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    selected_candidate_id: str,
    methods: Sequence[Mapping[str, Any]],
    state_count: int,
    trace_count: int,
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "5.1",
        "selected_candidate_id": selected_candidate_id,
        "sealed_test_reporting_executed": True,
        "method_count": len(methods),
        "method_names": [str(method["method_name"]) for method in methods],
        "sealed_state_count": int(state_count),
        "trace_row_count": int(trace_count),
        "FE_total": int(ledger["FE_total"]),
        "next_status": "READY_FOR_STAGE6_1_BASELINE_ABLATION_ANALYSIS",
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "prompt_revision_used": False,
        "train_search_revision_used": False,
        "promotion_rule_revision_used": False,
        "validation_rule_revision_used": False,
        "test_feedback_tuning_used": False,
        "objective_evaluation_used": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_performance_claim": True,
    }


def _mean(values: Any) -> float:
    return round(float(np.mean([float(value) for value in values])), 12)


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

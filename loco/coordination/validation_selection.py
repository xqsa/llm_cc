"""Stage 5.0 validation-only selection over promoted frozen AST candidates.

This module selects from Stage 4.1 validation-ready candidates using
deterministic validation conflict diagnostics. It executes already-frozen
typed ASTs on validation conflict states only. It does not call an LLM,
generate candidates, revise train search, evaluate benchmark objectives, touch
sealed test data, or make a performance claim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from loco.conflict.conflict_metrics import conflict_intensity, oscillation_score
from loco.conflict.conflict_state import GroupProposal, SharedVariableConflictState
from loco.coordination.dsl import load_coordination_ast
from loco.coordination.dsl_runtime import FrozenASTRuntime


STAGE = "5.0"
TRACE_SCHEMA_VERSION = "loco.stage5_0_validation_trace.v1"
METRICS_SCHEMA_VERSION = "loco.stage5_0_validation_metrics.v1"
DECISION_SCHEMA_VERSION = "loco.stage5_0_selection_decision.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage5_0_fe_ledger.v1"
REPORT_SCHEMA_VERSION = "loco.stage5_0_validation_report.v1"


def run_stage5_0_validation_selection(
    *,
    promotion_decision_path: Path | str,
    frozen_pool_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Run validation-only selection over Stage 4.1 promoted candidates."""

    promotion_decision = _read_json(Path(promotion_decision_path))
    frozen_rows = _read_jsonl(Path(frozen_pool_path))
    _validate_promotion_decision(promotion_decision)

    ready_candidates = list(promotion_decision["validation_ready_candidates"])
    frozen_by_id = _frozen_rows_by_id(frozen_rows)
    validation_rows: list[dict[str, Any]] = []
    candidate_metrics: list[dict[str, Any]] = []

    for candidate in ready_candidates:
        candidate_id = str(candidate["candidate_id"])
        frozen_row = frozen_by_id[candidate_id]
        ast_payload = frozen_row["llm_candidate_payload"]["ast"]
        ast = load_coordination_ast(ast_payload)
        runtime = FrozenASTRuntime(ast)
        target_variable = int(frozen_row["target_variable_set"][0])
        states = _validation_states_for_variable(target_variable)
        per_candidate_rows = [
            _evaluate_candidate_on_state(
                candidate=candidate,
                frozen_row=frozen_row,
                runtime=runtime,
                state=state,
                case_index=index,
            )
            for index, state in enumerate(states, start=1)
        ]
        validation_rows.extend(per_candidate_rows)
        candidate_metrics.append(
            _aggregate_candidate_metrics(
                candidate=candidate,
                frozen_row=frozen_row,
                rows=per_candidate_rows,
            )
        )

    candidate_metrics.sort(
        key=lambda row: (
            float(row["selection_score"]),
            int(row["FE_total"]),
            int(row["node_count"]),
            str(row["candidate_id"]),
        )
    )
    decision = _build_selection_decision(candidate_metrics)
    ledger = _build_fe_ledger(validation_rows)
    metrics = _build_validation_metrics(candidate_metrics)
    report = _build_report(
        candidate_count=len(ready_candidates),
        selected_candidate_status=str(decision["selection_status"]),
        selected_candidate_id=str(decision["selected_candidate_id"]),
        ledger=ledger,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "validation_trace.jsonl", validation_rows)
    _write_json(output_path / "validation_metrics.json", metrics)
    _write_json(output_path / "selection_decision.json", decision)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "validation_report.json", report)
    return report


def _validate_promotion_decision(decision: Mapping[str, Any]) -> None:
    if decision.get("stage") != "4.1":
        raise ValueError("Stage 5.0 requires a Stage 4.1 promotion decision.")
    if decision.get("status") != "PASS":
        raise ValueError("Stage 5.0 requires a PASS promotion decision.")
    if decision.get("validation_feedback_used") is not False:
        raise ValueError("Stage 5.0 input must not already use validation feedback.")
    if decision.get("test_feedback_used") is not False:
        raise ValueError("Stage 5.0 input must not use test feedback.")
    if decision.get("objective_evaluation_used") is not False:
        raise ValueError("Stage 5.0 input must not use objective evaluation.")

    ready = decision.get("validation_ready_candidates")
    if not isinstance(ready, Sequence) or isinstance(ready, (str, bytes)):
        raise ValueError("Stage 5.0 requires validation_ready_candidates.")
    if not ready:
        raise ValueError("Stage 5.0 requires at least one validation-ready candidate.")
    for row in ready:
        if row.get("promotion_status") != "VALIDATION_READY_TIE_HARDENED_NOT_FINAL":
            raise ValueError("Stage 5.0 only accepts tie-hardened candidates.")
        if (
            row.get("allowed_next_use")
            != "validation selection only after train search"
        ):
            raise ValueError("Stage 5.0 requires validation-only next-use boundary.")
        if row.get("not_performance_claim") is not True:
            raise ValueError("Stage 5.0 requires claim-boundary preservation.")


def _frozen_rows_by_id(
    frozen_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    rows_by_id = {str(row["candidate_id"]): row for row in frozen_rows}
    for candidate_id, row in rows_by_id.items():
        if row.get("frozen") is not True:
            raise ValueError(f"Candidate is not frozen: {candidate_id}")
        if row.get("split") != "train":
            raise ValueError(f"Frozen candidate is not train split: {candidate_id}")
        if row.get("target_scope") != "shared_variables_only":
            raise ValueError(f"Candidate is not shared-variable-only: {candidate_id}")
        if row.get("no_llm_call") is not True:
            raise ValueError(f"Frozen candidate LLM boundary missing: {candidate_id}")
        if row.get("no_objective_evaluation") is not True:
            raise ValueError(
                f"Frozen candidate objective boundary missing: {candidate_id}"
            )
        if row.get("not_performance_claim") is not True:
            raise ValueError(f"Frozen candidate claim boundary missing: {candidate_id}")
    return rows_by_id


def _validation_states_for_variable(
    variable_id: int,
) -> tuple[SharedVariableConflictState, ...]:
    """Build deterministic validation conflict states for one shared variable."""

    base = 0.10 if variable_id == 5 else -0.10
    bounds = (-1.0, 1.0)
    cases = [
        {
            "current": base,
            "values": (0.82, -0.46, 0.35),
            "rewards": (0.20, 0.95, 0.55),
            "history": (0.18, -0.12, 0.16, -0.08),
        },
        {
            "current": -base,
            "values": (-0.72, 0.58, 0.12),
            "rewards": (0.85, 0.25, 0.50),
            "history": (-0.20, 0.10, -0.05, 0.03),
        },
        {
            "current": 0.0,
            "values": (-0.88, 0.78, 0.04),
            "rewards": (0.40, 0.92, 0.35),
            "history": (0.30, -0.25, 0.20, -0.10),
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
                metadata={"validation_case": case_index},
            )
            for group_id, value, reward in zip(
                (101, 102, 103), case["values"], case["rewards"]
            )
        ]
        states.append(
            SharedVariableConflictState.from_group_proposals(
                variable_id=variable_id,
                current_value=float(case["current"]),
                bounds=bounds,
                proposals=proposals,
                consensus_history=case["history"],
                diagnostics={
                    "split": "validation",
                    "validation_case": case_index,
                    "sealed_test": False,
                },
            )
        )
    return tuple(states)


def _evaluate_candidate_on_state(
    *,
    candidate: Mapping[str, Any],
    frozen_row: Mapping[str, Any],
    runtime: FrozenASTRuntime,
    state: SharedVariableConflictState,
    case_index: int,
) -> dict[str, Any]:
    result = runtime.coordinate(state, shared_variables={state.variable_id})
    width = max(state.range_width, 1e-12)
    best_reward_index = int(np.argmax(np.asarray(state.group_rewards, dtype=float)))
    best_reward_value = float(state.proposals[best_reward_index])
    normalized_update = abs(result.coordinated_value - state.current_value) / width
    distance_to_best = abs(result.coordinated_value - best_reward_value) / width
    oscillation = oscillation_score(state)
    score = 0.50 * distance_to_best + 0.35 * normalized_update + 0.15 * oscillation

    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "4.1",
        "split": "validation",
        "selection_scope": "validation_only_after_train_search",
        "candidate_id": str(candidate["candidate_id"]),
        "operator_family": str(candidate["operator_family"]),
        "kind_sequence": str(candidate["kind_sequence"]),
        "node_count": int(frozen_row["node_count"]),
        "target_scope": "shared_variables_only",
        "variable_id": int(state.variable_id),
        "validation_case": int(case_index),
        "pre_conflict_intensity": round(conflict_intensity(state), 12),
        "oscillation_score": round(oscillation, 12),
        "current_value": float(state.current_value),
        "coordinated_value": float(result.coordinated_value),
        "best_reward_reference_value": best_reward_value,
        "normalized_update_size": round(normalized_update, 12),
        "normalized_distance_to_best_reward_proposal": round(distance_to_best, 12),
        "case_selection_score": round(score, 12),
        "FE_proposal": 1,
        "FE_coordination_extra": int(result.extra_fe),
        "FE_repair": 0,
        "ast_execution_used": True,
        "validation_feedback_used": True,
        "test_feedback_used": False,
        "sealed_test_access_used": False,
        "objective_evaluation_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "prompt_revision_used": False,
        "train_search_revision_used": False,
        "promotion_rule_revision_used": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_performance_claim": True,
    }


def _aggregate_candidate_metrics(
    *,
    candidate: Mapping[str, Any],
    frozen_row: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    mean_distance_to_best = _mean(
        row["normalized_distance_to_best_reward_proposal"] for row in rows
    )
    mean_update = _mean(row["normalized_update_size"] for row in rows)
    mean_oscillation = _mean(row["oscillation_score"] for row in rows)
    mean_score = _mean(row["case_selection_score"] for row in rows)
    fe_total = int(
        sum(
            int(row["FE_proposal"])
            + int(row["FE_coordination_extra"])
            + int(row["FE_repair"])
            for row in rows
        )
    )
    return {
        "candidate_id": str(candidate["candidate_id"]),
        "operator_family": str(candidate["operator_family"]),
        "kind_sequence": str(candidate["kind_sequence"]),
        "node_count": int(frozen_row["node_count"]),
        "validation_case_count": len(rows),
        "mean_normalized_distance_to_best_reward_proposal": round(
            mean_distance_to_best, 12
        ),
        "mean_normalized_update_size": round(mean_update, 12),
        "mean_oscillation_score": round(mean_oscillation, 12),
        "selection_score": round(mean_score, 12),
        "FE_total": fe_total,
        "validation_feedback_used": True,
        "test_feedback_used": False,
        "objective_evaluation_used": False,
        "not_performance_claim": True,
    }


def _build_selection_decision(
    candidate_metrics: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selected = candidate_metrics[0]
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "4.1",
        "selection_rule": {
            "primary": "minimize_selection_score",
            "tie_breakers": [
                "lower_FE_total",
                "lower_node_count",
                "lexicographic_candidate_id",
            ],
            "selection_score_formula": (
                "mean(0.50*normalized_distance_to_best_reward_proposal + "
                "0.35*normalized_update_size + 0.15*oscillation_score)"
            ),
        },
        "selected_candidate_id": str(selected["candidate_id"]),
        "selected_operator_family": str(selected["operator_family"]),
        "selected_kind_sequence": str(selected["kind_sequence"]),
        "selected_validation_score": float(selected["selection_score"]),
        "selection_status": "SELECTED_FOR_SEALED_TEST_NOT_FINAL",
        "selection_pool_candidate_ids": [
            str(row["candidate_id"]) for row in candidate_metrics
        ],
        "validation_feedback_used": True,
        "test_feedback_used": False,
        "sealed_test_access_used": False,
        "objective_evaluation_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "prompt_revision_used": False,
        "train_search_revision_used": False,
        "promotion_rule_revision_used": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_performance_claim": True,
    }


def _build_validation_metrics(
    candidate_metrics: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": METRICS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "4.1",
        "candidate_count": len(candidate_metrics),
        "validation_state_count": 3,
        "selection_rule": {
            "primary": "minimize_selection_score",
            "tie_breakers": [
                "lower_FE_total",
                "lower_node_count",
                "lexicographic_candidate_id",
            ],
        },
        "candidate_metrics": list(candidate_metrics),
        "validation_feedback_used": True,
        "test_feedback_used": False,
        "sealed_test_access_used": False,
        "objective_evaluation_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "not_performance_claim": True,
    }


def _build_fe_ledger(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    fe_proposal = int(sum(int(row["FE_proposal"]) for row in rows))
    fe_coordination_extra = int(sum(int(row["FE_coordination_extra"]) for row in rows))
    fe_repair = int(sum(int(row["FE_repair"]) for row in rows))
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "validation_only_selection",
        "FE_grouping": 0,
        "FE_proposal": fe_proposal,
        "FE_coordination_extra": fe_coordination_extra,
        "FE_repair": fe_repair,
        "FE_total": fe_proposal + fe_coordination_extra + fe_repair,
        "validation_trace_row_count": len(rows),
        "validation_feedback_used": True,
        "test_feedback_used": False,
        "sealed_test_access_used": False,
        "objective_evaluation_used": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    candidate_count: int,
    selected_candidate_status: str,
    selected_candidate_id: str,
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "4.1",
        "candidate_count": int(candidate_count),
        "selection_scope": "validation_only_after_train_search",
        "selected_candidate_id": selected_candidate_id,
        "selected_candidate_status": selected_candidate_status,
        "next_status": "READY_FOR_STAGE5_1_SELECTED_OPERATOR_FREEZE",
        "FE_total": int(ledger["FE_total"]),
        "validation_feedback_used": True,
        "test_feedback_used": False,
        "sealed_test_access_used": False,
        "objective_evaluation_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "prompt_revision_used": False,
        "train_search_revision_used": False,
        "promotion_rule_revision_used": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_performance_claim": True,
    }


def _mean(values: Any) -> float:
    return float(np.mean([float(value) for value in values]))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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

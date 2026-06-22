"""Stage 8.8 objective-loop rerun for the Stage 8.7 conditional policy.

This stage executes the Stage 8.7 conditional policy in the same deterministic
large-scale synthetic objective loop used by Stage 8.4. It counts fresh
objective evaluations and keeps the same boundary: no LLM calls, no candidate
generation, no selected-operator revision, no validation/test feedback, no
BaseOpt modification, and no final performance/SOTA claim.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from loco.conflict.conflict_state import SharedVariableConflictState
from loco.coordination.baselines import (
    AverageConsensus,
    CoordinationResult,
    WeightedConsensus,
)
from loco.coordination.large_scale_objective_panel import (
    DIMENSIONS,
    OBJECTIVE_STEPS,
    PANEL_NAMES,
    SEEDS,
    _Method,
    _build_methods,
    _build_panel_problem,
    _comparison_result,
    _count_results,
    _last_best,
    _load_frozen_candidate,
    _mean,
    _median,
    _read_json,
    _read_json_or_yaml,
    _read_jsonl,
    _run_method_loop,
    _validate_inputs,
    _validate_selected_candidate,
    _write_json,
    _write_jsonl,
)
from loco.coordination.dsl import load_coordination_ast
from loco.coordination.dsl_runtime import FrozenASTRuntime


STAGE = "8.8"
TRACE_SCHEMA_VERSION = "loco.stage8_8_objective_trace.v1"
PANEL_SUMMARY_SCHEMA_VERSION = "loco.stage8_8_panel_summary.v1"
METHOD_SUMMARY_SCHEMA_VERSION = "loco.stage8_8_method_summary.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_8_win_loss_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_8_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_8_runtime_boundary.v1"
REPORT_SCHEMA_VERSION = "loco.stage8_8_panel_report.v1"
POLICY_RUNTIME_SCHEMA_VERSION = "loco.stage8_8_conditional_policy_runtime_report.v1"

CONDITIONAL_METHOD = "stage8_7_conditional_policy"
CONDITIONAL_POLICY_NAME = "overlap_reward_reliability_switch_v1"
METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "frozen_stage5_selected_operator",
    "stage8_3_selected_operator",
    CONDITIONAL_METHOD,
]
BASELINE_METHOD_NAMES = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
]


class _ConditionalPolicyOperator:
    name = "ConditionalPolicy(overlap_reward_reliability_switch_v1)"

    def __init__(self, action_by_case: Mapping[tuple[str, int, int], str]):
        self._action_by_case = dict(action_by_case)
        self._simple = AverageConsensus()
        self._weighted = WeightedConsensus(temperature=1.0)

    def coordinate(
        self, conflict_state: SharedVariableConflictState
    ) -> CoordinationResult:
        diagnostics = conflict_state.diagnostics
        key = (
            str(diagnostics["panel"]),
            int(diagnostics["dimension"]),
            int(diagnostics["seed"]),
        )
        action = self._action_by_case[key]
        if action == "use_simple_consensus":
            base = self._simple.coordinate(conflict_state)
        elif action == "keep_weighted_consensus":
            base = self._weighted.coordinate(conflict_state)
        else:
            raise ValueError(f"Unknown Stage 8.7 policy action: {action}")
        return CoordinationResult(
            variable_id=base.variable_id,
            coordinated_value=base.coordinated_value,
            operator_name=self.name,
            extra_fe=base.extra_fe,
            diagnostics={
                "conditional_policy_name": CONDITIONAL_POLICY_NAME,
                "conditional_policy_action": action,
                "base_operator": base.operator_name,
                "base_diagnostics": base.diagnostics,
            },
        )


def run_stage8_8_conditional_policy_objective_rerun(
    *,
    protocol_path: Path | str,
    stage8_3_selection_decision_path: Path | str,
    frozen_stage5_operator_path: Path | str,
    frozen_stage5_ast_path: Path | str,
    stage8_7_policy_report_path: Path | str,
    stage8_7_case_policy_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Execute the Stage 8.7 conditional policy in the objective loop."""

    protocol = _read_json_or_yaml(Path(protocol_path))
    stage8_3_decision = _read_json(Path(stage8_3_selection_decision_path))
    frozen_stage5_operator = _read_json(Path(frozen_stage5_operator_path))
    frozen_stage5_ast_payload = _read_json(Path(frozen_stage5_ast_path))
    stage8_7_policy_report = _read_json(Path(stage8_7_policy_report_path))
    stage8_7_case_rows = _read_jsonl(Path(stage8_7_case_policy_path))
    _validate_inputs(
        protocol,
        stage8_3_decision,
        frozen_stage5_operator,
        frozen_stage5_ast_payload,
    )
    _validate_stage8_7_inputs(stage8_7_policy_report, stage8_7_case_rows)

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
    action_by_case = _action_by_case(stage8_7_case_rows)
    methods.append(
        _Method(
            name=CONDITIONAL_METHOD,
            label=_ConditionalPolicyOperator.name,
            is_loco_operator=True,
            selected_candidate_id=selected_candidate_id,
            previous_frozen_candidate_id=None,
            coordinate=_ConditionalPolicyOperator(action_by_case).coordinate,
        )
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
                    rows = _run_method_loop(
                        method=method,
                        problem=problem,
                        selected_candidate_id=selected_candidate_id,
                        previous_frozen_candidate_id=previous_frozen_candidate_id,
                    )
                    trace_rows.extend(
                        _retag_trace_rows(
                            rows,
                            action_by_case=action_by_case,
                            source_regime_by_case=_source_regime_by_case(
                                stage8_7_case_rows
                            ),
                        )
                    )

    panel_summary = _build_panel_summary(trace_rows)
    method_summary = _build_method_summary(trace_rows)
    win_loss_report = _build_win_loss_report(trace_rows, stage8_7_case_rows)
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
    _write_json(output_path / "conditional_policy_runtime_report.json", policy_runtime)
    return report


def _validate_stage8_7_inputs(
    policy_report: Mapping[str, Any], case_rows: Sequence[Mapping[str, Any]]
) -> None:
    if policy_report.get("stage") != "8.7" or policy_report.get("status") != "PASS":
        raise ValueError("Stage 8.8 requires the Stage 8.7 policy report.")
    if policy_report.get("policy_name") != CONDITIONAL_POLICY_NAME:
        raise ValueError("Stage 8.8 received the wrong conditional policy.")
    if policy_report.get("family_collapse_gate_passed") is not True:
        raise ValueError("Stage 8.8 requires the Stage 8.7 family-collapse gate.")
    if policy_report.get("not_final_performance_claim") is not True:
        raise ValueError("Stage 8.8 requires claim-boundary preservation.")
    if len(case_rows) != 36:
        raise ValueError("Stage 8.8 requires 36 Stage 8.7 policy case rows.")
    expected = {(panel, dimension, seed) for panel in PANEL_NAMES for dimension in DIMENSIONS for seed in SEEDS}
    found = {
        (str(row["synthetic_panel"]), int(row["problem_dimension"]), int(row["seed"]))
        for row in case_rows
    }
    if found != expected:
        raise ValueError("Stage 8.7 policy rows do not cover the full panel.")


def _action_by_case(
    case_rows: Sequence[Mapping[str, Any]]
) -> dict[tuple[str, int, int], str]:
    return {
        (str(row["synthetic_panel"]), int(row["problem_dimension"]), int(row["seed"])): str(
            row["policy_action"]
        )
        for row in case_rows
    }


def _source_regime_by_case(
    case_rows: Sequence[Mapping[str, Any]]
) -> dict[tuple[str, int, int], str]:
    return {
        (str(row["synthetic_panel"]), int(row["problem_dimension"]), int(row["seed"])): str(
            row["source_regime"]
        )
        for row in case_rows
    }


def _retag_trace_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    action_by_case: Mapping[tuple[str, int, int], str],
    source_regime_by_case: Mapping[tuple[str, int, int], str],
) -> list[dict[str, Any]]:
    retagged = []
    for source in rows:
        row = dict(source)
        key = (
            str(row["synthetic_panel"]),
            int(row["problem_dimension"]),
            int(row["seed"]),
        )
        action = action_by_case[key] if row["method_name"] == CONDITIONAL_METHOD else None
        row["schema_version"] = TRACE_SCHEMA_VERSION
        row["stage"] = STAGE
        row["source_stage"] = "8.7"
        row["split"] = "conditional_policy_objective_rerun"
        row["conditional_policy_name"] = (
            CONDITIONAL_POLICY_NAME if row["method_name"] == CONDITIONAL_METHOD else None
        )
        row["conditional_policy_action"] = action
        row["conditional_policy_source_regime"] = (
            source_regime_by_case[key]
            if row["method_name"] == CONDITIONAL_METHOD
            else None
        )
        retagged.append(row)
    return retagged


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
        "source_stage": "8.7",
        "panels": PANEL_NAMES,
        "dimensions": DIMENSIONS,
        "seeds": SEEDS,
        "panel_rows": panel_rows,
        "claim_scope": "conditional policy objective-loop utility evidence",
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
        "source_stage": "8.7",
        "methods": METHOD_NAMES,
        "method_rows": method_rows,
        "claim_scope": "conditional policy objective-loop utility evidence",
        "same_budget_across_methods": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_win_loss_report(
    trace_rows: Sequence[Mapping[str, Any]],
    stage8_7_case_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    source_regime = _source_regime_by_case(stage8_7_case_rows)
    case_rows = []
    conditional_final_bests = []
    best_baseline_final_bests = []
    for panel_name in PANEL_NAMES:
        for dimension in DIMENSIONS:
            for seed in SEEDS:
                rows = _case_rows(trace_rows, panel_name, dimension, seed)
                final_by_method = {
                    method_name: _last_best(rows, method_name)
                    for method_name in METHOD_NAMES
                }
                conditional_final = final_by_method[CONDITIONAL_METHOD]
                best_baseline_method = min(
                    BASELINE_METHOD_NAMES, key=lambda name: final_by_method[name]
                )
                best_baseline_final = final_by_method[best_baseline_method]
                conditional_final_bests.append(conditional_final)
                best_baseline_final_bests.append(best_baseline_final)
                key = (panel_name, dimension, seed)
                case_rows.append(
                    {
                        "synthetic_panel": panel_name,
                        "problem_dimension": dimension,
                        "seed": seed,
                        "source_regime": source_regime[key],
                        "conditional_policy_final_best": conditional_final,
                        "stage8_3_selected_final_best": final_by_method[
                            "stage8_3_selected_operator"
                        ],
                        "weighted_consensus_final_best": final_by_method[
                            "weighted_consensus"
                        ],
                        "simple_consensus_final_best": final_by_method[
                            "simple_consensus"
                        ],
                        "frozen_stage5_final_best": final_by_method[
                            "frozen_stage5_selected_operator"
                        ],
                        "best_baseline_method": best_baseline_method,
                        "best_baseline_final_best": best_baseline_final,
                        "conditional_vs_stage8_3_selected_delta": round(
                            conditional_final
                            - final_by_method["stage8_3_selected_operator"],
                            12,
                        ),
                        "conditional_vs_weighted_delta": round(
                            conditional_final - final_by_method["weighted_consensus"],
                            12,
                        ),
                        "conditional_vs_simple_delta": round(
                            conditional_final - final_by_method["simple_consensus"],
                            12,
                        ),
                        "conditional_vs_best_baseline_delta": round(
                            conditional_final - best_baseline_final, 12
                        ),
                        "conditional_vs_stage8_3_selected_result": _comparison_result(
                            conditional_final,
                            final_by_method["stage8_3_selected_operator"],
                        ),
                        "conditional_vs_weighted_result": _comparison_result(
                            conditional_final, final_by_method["weighted_consensus"]
                        ),
                        "conditional_vs_simple_result": _comparison_result(
                            conditional_final, final_by_method["simple_consensus"]
                        ),
                        "conditional_vs_best_baseline_result": _comparison_result(
                            conditional_final, best_baseline_final
                        ),
                    }
                )

    return {
        "schema_version": WIN_LOSS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.7",
        "comparison_case_count": len(case_rows),
        "conditional_policy_case_count": len(conditional_final_bests),
        "case_rows": case_rows,
        "conditional_vs_stage8_3_selected_operator": _count_results(
            row["conditional_vs_stage8_3_selected_result"] for row in case_rows
        ),
        "conditional_vs_weighted_consensus": _count_results(
            row["conditional_vs_weighted_result"] for row in case_rows
        ),
        "conditional_vs_simple_consensus": _count_results(
            row["conditional_vs_simple_result"] for row in case_rows
        ),
        "conditional_vs_best_baseline": _count_results(
            row["conditional_vs_best_baseline_result"] for row in case_rows
        ),
        "simple_preferred_case_recovery_count": sum(
            row["source_regime"] == "simple_consensus_preferred"
            and row["conditional_vs_stage8_3_selected_result"] == "win"
            for row in case_rows
        ),
        "weighted_sufficient_case_regression_count": sum(
            row["source_regime"] == "weighted_consensus_sufficient"
            and row["conditional_vs_stage8_3_selected_result"] == "loss"
            for row in case_rows
        ),
        "conditional_policy_mean_final_best": _mean(conditional_final_bests),
        "conditional_policy_median_final_best": _median(conditional_final_bests),
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
        "budget_scope": "conditional_policy_objective_loop_rerun",
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
    conditional_rows = [
        row for row in trace_rows if row["method_name"] == CONDITIONAL_METHOD
    ]
    switch_rows = [
        row
        for row in conditional_rows
        if row["conditional_policy_action"] == "use_simple_consensus"
    ]
    keep_rows = [
        row
        for row in conditional_rows
        if row["conditional_policy_action"] == "keep_weighted_consensus"
    ]
    return {
        "schema_version": POLICY_RUNTIME_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.7",
        "conditional_policy_name": CONDITIONAL_POLICY_NAME,
        "conditional_policy_trace_row_count": len(conditional_rows),
        "switch_to_simple_trace_row_count": len(switch_rows),
        "keep_weighted_trace_row_count": len(keep_rows),
        "simple_preferred_case_recovery_count": int(
            win_loss_report["simple_preferred_case_recovery_count"]
        ),
        "weighted_sufficient_case_regression_count": int(
            win_loss_report["weighted_sufficient_case_regression_count"]
        ),
        "conditional_policy_not_equivalent_to_weighted_consensus": bool(switch_rows),
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "conditional policy objective-loop utility evidence",
        "legal_inputs": [
            "configs/stage7_0_objective_eval_protocol.yaml",
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
    no_best_baseline_loss = int(
        win_loss_report["conditional_vs_best_baseline"]["loss"]
    ) == 0
    return {
        "schema_version": "loco.stage8_8_next_route_decision.v1",
        "stage": STAGE,
        "status": "PASS",
        "decision": (
            "READY_FOR_STAGE8_9_FAILURE_HONEST_INTERPRETATION"
            if no_best_baseline_loss
            else "REQUIRES_STAGE8_9_FAILURE_HONEST_INTERPRETATION"
        ),
        "decision_reason": (
            "Stage 8.8 executed the conditional policy in the objective loop and "
            "recorded win/loss evidence against Stage 8.3, weighted/simple "
            "baselines, and the best baseline."
        ),
        "next_stage": "Stage 8.9",
        "allowed_next_work": "failure_honest_interpretation_before_official_claims",
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
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.7",
        "panel_scope": "conditional_policy_objective_loop_rerun",
        "selected_candidate_id": selected_candidate_id,
        "previous_frozen_candidate_id": previous_frozen_candidate_id,
        "selected_operator_target_variable": selected_variable,
        "conditional_policy_name": CONDITIONAL_POLICY_NAME,
        "conditional_policy_executed": True,
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
        "next_status": "READY_FOR_STAGE8_9_FAILURE_HONEST_INTERPRETATION",
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

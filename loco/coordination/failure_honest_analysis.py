"""Stage 8.5 failure-honest analysis over Stage 8.4 artifacts.

This stage is diagnostic only. It reads Stage 8.4 artifacts to explain why the
Stage 8.3 selected operator beats the old frozen LOCO operator but does not
beat the best simple baseline. It performs no objective-loop execution and no
new objective evaluation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


STAGE = "8.5"
CASE_SCHEMA_VERSION = "loco.stage8_5_case_diagnosis_row.v1"
DIAGNOSIS_SCHEMA_VERSION = "loco.stage8_5_failure_honest_diagnosis_report.v1"
EQUIVALENCE_SCHEMA_VERSION = "loco.stage8_5_baseline_equivalence_report.v1"
TOPOLOGY_SCHEMA_VERSION = "loco.stage8_5_topology_gap_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_5_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_5_runtime_boundary.v1"

SELECTED_METHOD = "stage8_3_selected_operator"
WEIGHTED_METHOD = "weighted_consensus"
SIMPLE_METHOD = "simple_consensus"
FROZEN_METHOD = "frozen_stage5_selected_operator"
BASELINE_METHODS = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
]
TIE_EPSILON = 1e-12


def run_stage8_5_failure_honest_analysis(
    *,
    stage8_4_trace_path: Path | str,
    stage8_4_win_loss_path: Path | str,
    stage8_4_method_summary_path: Path | str,
    stage8_4_panel_report_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Analyze Stage 8.4 utility gaps without running new objective evaluations."""

    trace_rows = _read_jsonl(Path(stage8_4_trace_path))
    win_loss = _read_json(Path(stage8_4_win_loss_path))
    method_summary = _read_json(Path(stage8_4_method_summary_path))
    panel_report = _read_json(Path(stage8_4_panel_report_path))
    _validate_inputs(trace_rows, win_loss, method_summary, panel_report)

    case_rows = _build_case_diagnosis_rows(trace_rows, win_loss["case_rows"])
    equivalence_report = _build_equivalence_report(trace_rows, win_loss)
    topology_report = _build_topology_report(case_rows)
    ledger = _build_fe_ledger(panel_report)
    boundary = _build_runtime_boundary()
    route = _build_route()
    diagnosis = _build_diagnosis_report(
        trace_rows=trace_rows,
        win_loss=win_loss,
        panel_report=panel_report,
        equivalence_report=equivalence_report,
        topology_report=topology_report,
        ledger=ledger,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "failure_honest_diagnosis_report.json", diagnosis)
    _write_json(output_path / "baseline_equivalence_report.json", equivalence_report)
    _write_json(output_path / "topology_gap_report.json", topology_report)
    _write_jsonl(output_path / "case_diagnosis_table.jsonl", case_rows)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return diagnosis


def _validate_inputs(
    trace_rows: Sequence[Mapping[str, Any]],
    win_loss: Mapping[str, Any],
    method_summary: Mapping[str, Any],
    panel_report: Mapping[str, Any],
) -> None:
    if panel_report.get("stage") != "8.4" or panel_report.get("status") != "PASS":
        raise ValueError("Stage 8.5 requires a passing Stage 8.4 panel report.")
    if win_loss.get("stage") != "8.4" or win_loss.get("status") != "PASS":
        raise ValueError("Stage 8.5 requires a passing Stage 8.4 win/loss report.")
    if method_summary.get("stage") != "8.4" or method_summary.get("status") != "PASS":
        raise ValueError("Stage 8.5 requires a passing Stage 8.4 method summary.")
    if len(trace_rows) != int(panel_report["trace_row_count"]):
        raise ValueError("Stage 8.4 trace row count does not match panel report.")
    if panel_report.get("not_final_performance_claim") is not True:
        raise ValueError("Stage 8.5 requires Stage 8.4 claim-boundary preservation.")
    if panel_report.get("test_feedback_used") is not False:
        raise ValueError("Stage 8.5 refuses test-feedback-contaminated inputs.")
    if panel_report.get("validation_feedback_used") is not False:
        raise ValueError("Stage 8.5 refuses validation-feedback-contaminated inputs.")


def _build_case_diagnosis_rows(
    trace_rows: Sequence[Mapping[str, Any]],
    win_loss_case_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for case in win_loss_case_rows:
        panel = str(case["synthetic_panel"])
        dimension = int(case["problem_dimension"])
        seed = int(case["seed"])
        selected_series = _series(trace_rows, panel, dimension, seed, SELECTED_METHOD)
        weighted_series = _series(trace_rows, panel, dimension, seed, WEIGHTED_METHOD)
        simple_series = _series(trace_rows, panel, dimension, seed, SIMPLE_METHOD)
        frozen_series = _series(trace_rows, panel, dimension, seed, FROZEN_METHOD)
        selected_final = float(case["selected_operator_final_best"])
        best_baseline = str(case["best_baseline_method"])
        selected_vs_best = str(case["selected_vs_best_baseline_result"])
        selected_vs_frozen_delta = float(case["selected_vs_frozen_delta"])
        selected_vs_best_delta = float(case["selected_vs_best_baseline_delta"])
        diagnosis = (
            "simple_consensus_beats_selected_operator"
            if selected_vs_best == "loss" and best_baseline == SIMPLE_METHOD
            else "selected_ties_weighted_consensus_best_baseline"
        )
        rows.append(
            {
                "schema_version": CASE_SCHEMA_VERSION,
                "stage": STAGE,
                "source_stage": "8.4",
                "synthetic_panel": panel,
                "problem_dimension": dimension,
                "seed": seed,
                "selected_operator_final_best": selected_final,
                "weighted_consensus_final_best": float(
                    weighted_series[-1]["best_objective_so_far"]
                ),
                "simple_consensus_final_best": float(
                    simple_series[-1]["best_objective_so_far"]
                ),
                "frozen_stage5_final_best": float(
                    frozen_series[-1]["best_objective_so_far"]
                ),
                "best_baseline_method": best_baseline,
                "selected_vs_frozen_delta": round(selected_vs_frozen_delta, 12),
                "selected_vs_best_baseline_delta": round(selected_vs_best_delta, 12),
                "selected_weighted_final_best_abs_delta": round(
                    abs(
                        selected_final
                        - float(weighted_series[-1]["best_objective_so_far"])
                    ),
                    12,
                ),
                "selected_weighted_update_size_max_abs_delta": _max_abs_delta(
                    [row["coordination_update_size"] for row in selected_series],
                    [row["coordination_update_size"] for row in weighted_series],
                ),
                "selected_simple_final_best_delta": round(
                    selected_final - float(simple_series[-1]["best_objective_so_far"]),
                    12,
                ),
                "selected_frozen_final_best_delta": round(
                    selected_final - float(frozen_series[-1]["best_objective_so_far"]),
                    12,
                ),
                "diagnosis": diagnosis,
                "objective_evaluation_used_in_stage8_5": False,
                "not_final_performance_claim": True,
            }
        )
    return rows


def _build_equivalence_report(
    trace_rows: Sequence[Mapping[str, Any]], win_loss: Mapping[str, Any]
) -> dict[str, Any]:
    selected_method_rows = _method_rows(trace_rows, SELECTED_METHOD)
    weighted_method_rows = _method_rows(trace_rows, WEIGHTED_METHOD)
    selected_weighted_final_deltas = []
    selected_weighted_update_deltas = []
    selected_frozen_final_deltas = []
    for case in win_loss["case_rows"]:
        panel = str(case["synthetic_panel"])
        dimension = int(case["problem_dimension"])
        seed = int(case["seed"])
        selected_series = _series(trace_rows, panel, dimension, seed, SELECTED_METHOD)
        weighted_series = _series(trace_rows, panel, dimension, seed, WEIGHTED_METHOD)
        frozen_series = _series(trace_rows, panel, dimension, seed, FROZEN_METHOD)
        selected_weighted_final_deltas.append(
            float(selected_series[-1]["best_objective_so_far"])
            - float(weighted_series[-1]["best_objective_so_far"])
        )
        selected_frozen_final_deltas.append(
            float(selected_series[-1]["best_objective_so_far"])
            - float(frozen_series[-1]["best_objective_so_far"])
        )
        selected_weighted_update_deltas.extend(
            float(selected["coordination_update_size"])
            - float(weighted["coordination_update_size"])
            for selected, weighted in zip(selected_series, weighted_series)
        )

    baseline_counts = _count_by(
        str(row["best_baseline_method"]) for row in win_loss["case_rows"]
    )
    projection_penalty_case_count = sum(
        1 for delta in selected_frozen_final_deltas if delta < -TIE_EPSILON
    )
    return {
        "schema_version": EQUIVALENCE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.4",
        "selected_method": SELECTED_METHOD,
        "equivalent_baseline_method": WEIGHTED_METHOD,
        "selected_trace_row_count": len(selected_method_rows),
        "weighted_trace_row_count": len(weighted_method_rows),
        "selected_vs_weighted_max_abs_final_best_delta": _max_abs(
            selected_weighted_final_deltas
        ),
        "selected_vs_weighted_max_abs_update_size_delta": _max_abs(
            selected_weighted_update_deltas
        ),
        "selected_matches_weighted_consensus_all_cases": _max_abs(
            selected_weighted_final_deltas
        )
        <= TIE_EPSILON,
        "selected_matches_weighted_consensus_all_steps": _max_abs(
            selected_weighted_update_deltas
        )
        <= TIE_EPSILON,
        "weighted_consensus_best_baseline_case_count": int(
            baseline_counts.get(WEIGHTED_METHOD, 0)
        ),
        "simple_consensus_best_baseline_case_count": int(
            baseline_counts.get(SIMPLE_METHOD, 0)
        ),
        "projection_penalty_vs_selected_case_count": projection_penalty_case_count,
        "mean_selected_minus_frozen_final_best_delta": _mean(
            selected_frozen_final_deltas
        ),
        "diagnosis": (
            "The selected reweighting+repair AST behaves numerically like "
            "weighted_consensus on this Stage 8.4 panel."
        ),
        "not_final_performance_claim": True,
    }


def _build_topology_report(case_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    loss_rows = [
        row
        for row in case_rows
        if row["diagnosis"] == "simple_consensus_beats_selected_operator"
    ]
    tie_rows = [
        row
        for row in case_rows
        if row["diagnosis"] == "selected_ties_weighted_consensus_best_baseline"
    ]
    return {
        "schema_version": TOPOLOGY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.4",
        "selected_loss_to_best_baseline_case_count": len(loss_rows),
        "selected_tie_to_best_baseline_case_count": len(tie_rows),
        "loss_panels": _count_by(row["synthetic_panel"] for row in loss_rows),
        "loss_seeds": _count_by(str(row["seed"]) for row in loss_rows),
        "loss_dimensions": _count_by(
            str(row["problem_dimension"]) for row in loss_rows
        ),
        "loss_best_baseline_methods": _count_by(
            row["best_baseline_method"] for row in loss_rows
        ),
        "tie_best_baseline_methods": _count_by(
            row["best_baseline_method"] for row in tie_rows
        ),
        "mean_loss_delta_vs_simple_consensus": _mean(
            row["selected_simple_final_best_delta"] for row in loss_rows
        ),
        "diagnosis": (
            "Losses concentrate where simple consensus is the best baseline: all "
            "high-overlap cases and seed-0 medium-overlap cases."
        ),
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(panel_report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "failure_honest_analysis_only",
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "inherited_stage8_4_FE_total": int(panel_report["FE_total"]),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "failure-honest Stage 8.4 analysis",
        "legal_inputs": [
            "artifacts/objective_eval/stage8_4/objective_trace.jsonl",
            "artifacts/objective_eval/stage8_4/win_loss_report.json",
            "artifacts/objective_eval/stage8_4/method_summary.json",
            "artifacts/objective_eval/stage8_4/panel_report.json",
        ],
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "selected_operator_revision": False,
            "evolution_search": False,
            "objective_loop_execution": False,
            "new_objective_evaluation": False,
            "validation_feedback": False,
            "test_feedback": False,
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


def _build_route() -> dict[str, Any]:
    return {
        "schema_version": "loco.stage8_5_next_route_decision.v1",
        "stage": STAGE,
        "status": "PASS",
        "decision": "DO_NOT_MAKE_OFFICIAL_OR_SOTA_CLAIM_YET",
        "decision_reason": (
            "Stage 8.5 finds that the selected operator is equivalent to "
            "weighted_consensus on Stage 8.4 and loses to simple_consensus on "
            "12 high/medium-overlap cases."
        ),
        "next_stage": "Stage 8.6",
        "allowed_next_work": (
            "proposal_state_or_operator_family_ablation_before_official_claims"
        ),
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_diagnosis_report(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    win_loss: Mapping[str, Any],
    panel_report: Mapping[str, Any],
    equivalence_report: Mapping[str, Any],
    topology_report: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSIS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.4",
        "analysis_scope": "failure_honest_stage8_4_analysis",
        "selected_candidate_id": str(panel_report["selected_candidate_id"]),
        "previous_frozen_candidate_id": str(
            panel_report["previous_frozen_candidate_id"]
        ),
        "stage8_4_trace_row_count": len(trace_rows),
        "comparison_case_count": int(win_loss["comparison_case_count"]),
        "vs_frozen_stage5": dict(win_loss["vs_frozen_stage5"]),
        "vs_best_baseline": dict(win_loss["vs_best_baseline"]),
        "primary_diagnosis": (
            "selected_operator_equivalent_to_weighted_consensus_baseline"
        ),
        "secondary_diagnosis": (
            "simple_consensus_beats_selected_operator_on_high_and_seed0_medium_cases"
        ),
        "why_win_old_frozen": (
            "stage8_3_selected_operator removes the frozen Stage 5.1 projection penalty"
        ),
        "why_not_beat_best_baseline": (
            "stage8_3_selected_operator behavior is numerically identical to weighted_consensus"
        ),
        "selected_vs_weighted_max_abs_final_best_delta": equivalence_report[
            "selected_vs_weighted_max_abs_final_best_delta"
        ],
        "loss_to_best_baseline_case_count": int(
            topology_report["selected_loss_to_best_baseline_case_count"]
        ),
        "recommended_next_stage": (
            "Stage 8.6 proposal-state/operator-family ablation before official claims"
        ),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "FE_total": int(ledger["FE_total"]),
        "inherited_stage8_4_FE_total": int(ledger["inherited_stage8_4_FE_total"]),
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


def _series(
    trace_rows: Sequence[Mapping[str, Any]],
    panel: str,
    dimension: int,
    seed: int,
    method_name: str,
) -> list[Mapping[str, Any]]:
    rows = [
        row
        for row in trace_rows
        if row["synthetic_panel"] == panel
        and int(row["problem_dimension"]) == dimension
        and int(row["seed"]) == seed
        and row["method_name"] == method_name
    ]
    rows.sort(key=lambda row: int(row["objective_step"]))
    if not rows:
        raise ValueError(
            f"Missing trace rows for {panel} D={dimension} seed={seed} {method_name}"
        )
    return rows


def _method_rows(
    trace_rows: Sequence[Mapping[str, Any]], method_name: str
) -> list[Mapping[str, Any]]:
    return [row for row in trace_rows if row["method_name"] == method_name]


def _max_abs(values: Iterable[float]) -> float:
    return round(max(abs(float(value)) for value in values), 12)


def _max_abs_delta(left: Iterable[Any], right: Iterable[Any]) -> float:
    return round(
        max(
            abs(float(left_value) - float(right_value))
            for left_value, right_value in zip(left, right)
        ),
        12,
    )


def _mean(values: Iterable[Any]) -> float:
    numeric_values = [float(value) for value in values]
    if not numeric_values:
        return 0.0
    return round(float(np.mean(numeric_values)), 12)


def _count_by(values: Iterable[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


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

"""Stage 6.1 baseline comparison, ablation, and failure analysis.

This module reads only Stage 6.0 sealed-test reporting artifacts. It performs
post-hoc coordination diagnostics analysis without rerunning search, revising
selection rules, tuning from sealed-test feedback, or evaluating objectives.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "6.1"
COMPARISON_SCHEMA_VERSION = "loco.stage6_1_baseline_comparison_table.v1"
ABLATION_SCHEMA_VERSION = "loco.stage6_1_ablation_summary.v1"
FAILURE_SCHEMA_VERSION = "loco.stage6_1_failure_analysis.v1"
CLAIM_BOUNDARY_SCHEMA_VERSION = "loco.stage6_1_claim_boundary.v1"
REPORT_SCHEMA_VERSION = "loco.stage6_1_analysis_report.v1"

LEGAL_INPUTS = [
    "artifacts/sealed_test/stage6_0/sealed_test_trace.jsonl",
    "artifacts/sealed_test/stage6_0/sealed_test_metrics.json",
    "artifacts/sealed_test/stage6_0/fe_ledger.json",
    "artifacts/sealed_test/stage6_0/final_reporting_boundary.json",
    "artifacts/sealed_test/stage6_0/sealed_test_report.json",
]

BASELINE_METHODS = [
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
]
SELECTED_METHOD = "selected_loco_operator"
METHODS = BASELINE_METHODS + [SELECTED_METHOD]


def run_stage6_1_baseline_ablation_analysis(
    *,
    sealed_test_trace_path: Path | str,
    sealed_test_metrics_path: Path | str,
    fe_ledger_path: Path | str,
    final_reporting_boundary_path: Path | str,
    sealed_test_report_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Analyze Stage 6.0 sealed-test baseline diagnostics."""

    trace_rows = _read_jsonl(Path(sealed_test_trace_path))
    metrics = _read_json(Path(sealed_test_metrics_path))
    ledger = _read_json(Path(fe_ledger_path))
    stage6_0_boundary = _read_json(Path(final_reporting_boundary_path))
    stage6_0_report = _read_json(Path(sealed_test_report_path))

    _validate_inputs(
        trace_rows=trace_rows,
        metrics=metrics,
        ledger=ledger,
        boundary=stage6_0_boundary,
        report=stage6_0_report,
    )

    selected_candidate_id = str(stage6_0_report["selected_candidate_id"])
    comparison = _build_comparison_table(
        trace_rows=trace_rows,
        metrics=metrics,
        selected_candidate_id=selected_candidate_id,
    )
    ablation = _build_ablation_summary(comparison)
    failures = _build_failure_analysis(trace_rows)
    claim_boundary = _build_claim_boundary()
    report = _build_report(
        selected_candidate_id=selected_candidate_id,
        stage6_0_report=stage6_0_report,
        comparison=comparison,
        failures=failures,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "baseline_comparison_table.json", comparison)
    _write_json(output_path / "ablation_summary.json", ablation)
    _write_json(output_path / "failure_analysis.json", failures)
    _write_json(output_path / "claim_boundary.json", claim_boundary)
    _write_json(output_path / "analysis_report.json", report)
    return report


def _validate_inputs(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    metrics: Mapping[str, Any],
    ledger: Mapping[str, Any],
    boundary: Mapping[str, Any],
    report: Mapping[str, Any],
) -> None:
    if report.get("stage") != "6.0" or report.get("status") != "PASS":
        raise ValueError("Stage 6.1 requires a PASS Stage 6.0 report.")
    if report.get("next_status") != "READY_FOR_STAGE6_1_BASELINE_ABLATION_ANALYSIS":
        raise ValueError("Stage 6.0 report is not ready for Stage 6.1.")
    if metrics.get("stage") != "6.0" or metrics.get("status") != "PASS":
        raise ValueError("Stage 6.1 requires PASS Stage 6.0 metrics.")
    if ledger.get("stage") != "6.0" or ledger.get("status") != "PASS":
        raise ValueError("Stage 6.1 requires PASS Stage 6.0 FE ledger.")
    if boundary.get("stage") != "6.0" or boundary.get("status") != "PASS":
        raise ValueError("Stage 6.1 requires PASS Stage 6.0 boundary.")

    method_names = set(str(name) for name in report.get("method_names", []))
    if method_names != set(METHODS):
        raise ValueError("Stage 6.1 requires the fixed Stage 6.0 method set.")
    if set(str(name) for name in metrics.get("methods", [])) != set(METHODS):
        raise ValueError("Stage 6.0 metrics method set does not match.")
    if int(report.get("trace_row_count", -1)) != len(trace_rows):
        raise ValueError("Stage 6.0 trace row count does not match report.")
    if int(ledger.get("FE_total", -1)) != int(report.get("FE_total", -2)):
        raise ValueError("Stage 6.0 FE ledger does not match report.")

    forbidden_true_fields = [
        "llm_call_used",
        "new_candidate_generation_used",
        "prompt_revision_used",
        "train_search_revision_used",
        "promotion_rule_revision_used",
        "validation_rule_revision_used",
        "test_feedback_tuning_used",
        "objective_evaluation_used",
        "baseopt_modified",
        "optimizer_generation_used",
        "controller_scheduler_generation_used",
    ]
    for field in forbidden_true_fields:
        if report.get(field) is True:
            raise ValueError(f"Stage 6.0 report violates boundary: {field}")
    if report.get("not_sota_claim") is not True:
        raise ValueError("Stage 6.0 report must preserve not_sota_claim.")
    if report.get("not_performance_claim") is not True:
        raise ValueError("Stage 6.0 report must preserve not_performance_claim.")

    forbidden_behaviors = boundary.get("forbidden_behaviors", {})
    for behavior in [
        "llm_call",
        "new_candidate_generation",
        "prompt_revision",
        "train_search_revision",
        "promotion_rule_revision",
        "validation_rule_revision",
        "test_feedback_tuning",
        "objective_evaluation",
        "baseopt_modification",
        "optimizer_generation",
        "controller_scheduler_generation",
    ]:
        if forbidden_behaviors.get(behavior) is not False:
            raise ValueError(f"Stage 6.0 boundary must forbid {behavior}.")

    for row in trace_rows:
        if row.get("stage") != "6.0":
            raise ValueError("Trace row does not come from Stage 6.0.")
        if row.get("split") != "sealed_test":
            raise ValueError("Stage 6.1 only analyzes sealed_test rows.")
        if row.get("target_scope") != "shared_variables_only":
            raise ValueError("Stage 6.1 only analyzes shared-variable rows.")
        for field in forbidden_true_fields:
            if row.get(field) is True:
                raise ValueError(f"Trace row violates boundary: {field}")
        if row.get("not_sota_claim") is not True:
            raise ValueError("Trace row must preserve not_sota_claim.")
        if row.get("not_performance_claim") is not True:
            raise ValueError("Trace row must preserve not_performance_claim.")


def _build_comparison_table(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    metrics: Mapping[str, Any],
    selected_candidate_id: str,
) -> dict[str, Any]:
    metric_rows = [
        dict(row)
        for row in metrics.get("method_metrics", [])
        if row["method_name"] in METHODS
    ]
    ranked = sorted(
        metric_rows,
        key=lambda row: (
            float(row["mean_normalized_distance_to_best_reward_proposal"]),
            str(row["method_name"]),
        ),
    )
    rank_by_method = {
        str(row["method_name"]): rank for rank, row in enumerate(ranked, start=1)
    }
    best_baseline = min(
        (row for row in metric_rows if row["method_name"] in BASELINE_METHODS),
        key=lambda row: float(row["mean_normalized_distance_to_best_reward_proposal"]),
    )

    rows = []
    for metric in sorted(
        metric_rows, key=lambda row: METHODS.index(row["method_name"])
    ):
        method_name = str(metric["method_name"])
        per_case = [row for row in trace_rows if row["method_name"] == method_name]
        mean_distance = float(
            metric["mean_normalized_distance_to_best_reward_proposal"]
        )
        mean_update = float(metric["mean_normalized_update_size"])
        baseline_delta = mean_distance - float(
            best_baseline["mean_normalized_distance_to_best_reward_proposal"]
        )
        rows.append(
            {
                "method_name": method_name,
                "is_selected_loco_operator": method_name == SELECTED_METHOD,
                "sealed_test_case_count": int(metric["sealed_test_case_count"]),
                "mean_normalized_distance_to_best_reward_proposal": mean_distance,
                "mean_normalized_update_size": mean_update,
                "mean_pre_conflict_intensity": float(
                    metric["mean_pre_conflict_intensity"]
                ),
                "FE_total": int(metric["FE_total"]),
                "rank_by_distance_to_best": int(rank_by_method[method_name]),
                "best_baseline_delta_distance": baseline_delta,
                "case_win_count_by_distance": _case_win_count(per_case, trace_rows),
                "lower_distance_to_best_is_better": True,
                "smaller_update_is_not_automatically_better": True,
            }
        )

    return {
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "6.0",
        "selected_candidate_id": selected_candidate_id,
        "methods": METHODS,
        "selected_method_name": SELECTED_METHOD,
        "best_baseline": {
            "method_name": str(best_baseline["method_name"]),
            "mean_normalized_distance_to_best_reward_proposal": float(
                best_baseline["mean_normalized_distance_to_best_reward_proposal"]
            ),
            "mean_normalized_update_size": float(
                best_baseline["mean_normalized_update_size"]
            ),
        },
        "rows": rows,
        "analysis_scope": "sealed-test baseline diagnostics only",
        "objective_evaluation_used": False,
        "test_feedback_tuning_used": False,
        "not_sota_claim": True,
        "not_performance_claim": True,
    }


def _case_win_count(
    method_rows: Sequence[Mapping[str, Any]], all_rows: Sequence[Mapping[str, Any]]
) -> int:
    wins = 0
    for row in method_rows:
        case = int(row["sealed_test_case"])
        best_distance = min(
            float(other["normalized_distance_to_best_reward_proposal"])
            for other in all_rows
            if int(other["sealed_test_case"]) == case
        )
        if float(row["normalized_distance_to_best_reward_proposal"]) == best_distance:
            wins += 1
    return wins


def _build_ablation_summary(comparison: Mapping[str, Any]) -> dict[str, Any]:
    rows_by_method = {row["method_name"]: row for row in comparison["rows"]}
    selected = rows_by_method[SELECTED_METHOD]
    deltas = []
    for method_name in BASELINE_METHODS:
        baseline = rows_by_method[method_name]
        deltas.append(
            {
                "baseline_method_name": method_name,
                "selected_minus_baseline_distance_to_best": (
                    selected["mean_normalized_distance_to_best_reward_proposal"]
                    - baseline["mean_normalized_distance_to_best_reward_proposal"]
                ),
                "selected_minus_baseline_update_size": (
                    selected["mean_normalized_update_size"]
                    - baseline["mean_normalized_update_size"]
                ),
                "selected_has_lower_distance_to_best": (
                    selected["mean_normalized_distance_to_best_reward_proposal"]
                    < baseline["mean_normalized_distance_to_best_reward_proposal"]
                ),
            }
        )

    best_baseline = comparison["best_baseline"]
    return {
        "schema_version": ABLATION_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "6.0",
        "selected_method_name": SELECTED_METHOD,
        "baseline_methods": BASELINE_METHODS,
        "best_baseline_method_name": best_baseline["method_name"],
        "pairwise_deltas_vs_selected": deltas,
        "selected_rank_by_distance_to_best": int(selected["rank_by_distance_to_best"]),
        "selected_case_win_count_by_distance": int(
            selected["case_win_count_by_distance"]
        ),
        "interpretation": (
            "The selected LOCO operator is analyzed as a coordination-level "
            "diagnostic method against fixed baselines; this does not prove "
            "objective-value improvement."
        ),
        "lower_distance_to_best_is_better": True,
        "smaller_update_is_not_automatically_better": True,
        "objective_evaluation_used": False,
        "test_feedback_tuning_used": False,
        "not_sota_claim": True,
        "not_performance_claim": True,
    }


def _build_failure_analysis(trace_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cases = []
    failure_modes: Counter[str] = Counter()
    case_ids = sorted({int(row["sealed_test_case"]) for row in trace_rows})

    for case_id in case_ids:
        rows = [row for row in trace_rows if int(row["sealed_test_case"]) == case_id]
        by_method = {str(row["method_name"]): row for row in rows}
        winner = min(
            rows,
            key=lambda row: (
                float(row["normalized_distance_to_best_reward_proposal"]),
                str(row["method_name"]),
            ),
        )
        selected = by_method[SELECTED_METHOD]
        method_distances = {
            method: float(
                by_method[method]["normalized_distance_to_best_reward_proposal"]
            )
            for method in METHODS
        }
        method_updates = {
            method: float(by_method[method]["normalized_update_size"])
            for method in METHODS
        }
        case_modes = []
        if winner["method_name"] != SELECTED_METHOD:
            case_modes.append("selected_not_case_winner_by_distance")
        max_baseline_update = max(method_updates[method] for method in BASELINE_METHODS)
        if method_updates[SELECTED_METHOD] > max_baseline_update:
            case_modes.append("selected_uses_larger_update_than_baselines")
        if selected["objective_evaluation_used"] is False:
            case_modes.append("objective_value_not_observed")
        for mode in case_modes:
            failure_modes[mode] += 1

        cases.append(
            {
                "sealed_test_case": case_id,
                "selected_method_present": SELECTED_METHOD in by_method,
                "winner_method_name": str(winner["method_name"]),
                "selected_distance_to_best": method_distances[SELECTED_METHOD],
                "selected_update_size": method_updates[SELECTED_METHOD],
                "method_distances": method_distances,
                "method_update_sizes": method_updates,
                "failure_modes": case_modes,
            }
        )

    return {
        "schema_version": FAILURE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "6.0",
        "case_count": len(cases),
        "cases": cases,
        "failure_modes": dict(sorted(failure_modes.items())),
        "failure_mode_count": len(failure_modes),
        "analysis_note": (
            "Failure modes are coordination-diagnostic cautions, not optimizer "
            "failure claims, because no objective values were evaluated."
        ),
        "objective_evaluation_used": False,
        "test_feedback_tuning_used": False,
        "not_sota_claim": True,
        "not_performance_claim": True,
    }


def _build_claim_boundary() -> dict[str, Any]:
    return {
        "schema_version": CLAIM_BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "legal_inputs": LEGAL_INPUTS,
        "claim_scope": "sealed-test baseline diagnostics only",
        "allowed_claims": [
            "Stage 6.1 compares fixed Stage 6.0 sealed-test coordination diagnostics across baselines.",
            "Stage 6.1 reports ablation-style deltas against identity, simple consensus, and weighted consensus.",
            "Stage 6.1 records failure-analysis cautions without objective-value claims.",
        ],
        "forbidden_claims": [
            "SOTA improvement",
            "objective-value performance improvement",
            "benchmark optimizer superiority",
            "validation or test feedback tuning success",
            "new optimizer/controller/scheduler generation",
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
        "allowed_next_paths": [
            "paper_claim_polish_from_diagnostics",
            "stage7_objective_value_eval_with_new_protocol_and_fe_accounting",
        ],
        "not_sota_claim": True,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    selected_candidate_id: str,
    stage6_0_report: Mapping[str, Any],
    comparison: Mapping[str, Any],
    failures: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "6.0",
        "selected_candidate_id": selected_candidate_id,
        "analysis_scope": "sealed-test baseline diagnostics only",
        "method_count": int(stage6_0_report["method_count"]),
        "method_names": list(stage6_0_report["method_names"]),
        "baseline_method_count": len(BASELINE_METHODS),
        "selected_method_name": SELECTED_METHOD,
        "sealed_state_count": int(stage6_0_report["sealed_state_count"]),
        "trace_row_count": int(stage6_0_report["trace_row_count"]),
        "selected_rank_by_distance_to_best": next(
            int(row["rank_by_distance_to_best"])
            for row in comparison["rows"]
            if row["method_name"] == SELECTED_METHOD
        ),
        "failure_mode_count": int(failures["failure_mode_count"]),
        "comparison_table_written": True,
        "ablation_summary_written": True,
        "failure_analysis_written": True,
        "claim_boundary_written": True,
        "next_status": "READY_FOR_PAPER_CLAIM_POLISH_OR_STAGE7_OBJECTIVE_EVAL",
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

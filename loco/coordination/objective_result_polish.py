"""Stage 7.3 paper-ready objective result tables.

This module reads Stage 7.2 synthetic objective-loop artifacts and formats the
existing results into paper-facing tables, curve data, ranking summaries, and
claim boundaries. It does not run a new objective evaluation.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


STAGE = "7.3"
REPORT_SCHEMA_VERSION = "loco.stage7_3_paper_tables_report.v1"
RANKING_SCHEMA_VERSION = "loco.stage7_3_method_ranking.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage7_3_claim_boundary.v1"

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

OBJECTIVE_TABLE_COLUMNS = [
    "stage",
    "source_stage",
    "synthetic_panel",
    "problem_dimension",
    "seed",
    "objective_name",
    "method_name",
    "final_best_objective",
    "identity_final_best_objective",
    "delta_vs_identity",
    "relative_delta_vs_identity",
    "rank_in_panel_dimension",
    "FE_global_objective",
    "FE_total",
    "same_budget_across_methods",
    "lower_is_better",
    "new_objective_evaluation_used",
    "not_final_performance_claim",
]

CURVE_TABLE_COLUMNS = [
    "stage",
    "source_stage",
    "synthetic_panel",
    "problem_dimension",
    "seed",
    "objective_name",
    "method_name",
    "objective_step",
    "best_objective_so_far",
    "FE_global_objective_cumulative",
    "FE_total_cumulative",
    "same_budget_across_methods",
    "new_objective_evaluation_used",
    "not_final_performance_claim",
]


def run_stage7_3_objective_result_polish(
    *,
    source_dir: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Build paper-ready Stage 7.3 tables from Stage 7.2 artifacts only."""

    source_path = Path(source_dir)
    output_path = Path(output_dir)
    trace_rows = _read_jsonl(source_path / "objective_trace.jsonl")
    panel_report = _read_json(source_path / "panel_report.json")
    panel_summary = _read_json(source_path / "panel_summary.json")
    method_summary = _read_json(source_path / "method_summary.json")
    fe_ledger = _read_json(source_path / "fe_ledger.json")
    _validate_stage7_2_inputs(
        trace_rows=trace_rows,
        panel_report=panel_report,
        panel_summary=panel_summary,
        method_summary=method_summary,
        fe_ledger=fe_ledger,
    )

    objective_rows = _build_objective_table(trace_rows)
    curve_rows = _build_curve_table(trace_rows)
    ranking = _build_method_ranking(objective_rows)
    claim_boundary = _build_claim_boundary(ranking)
    report = _build_report(
        trace_rows=trace_rows,
        objective_rows=objective_rows,
        curve_rows=curve_rows,
        ranking=ranking,
        claim_boundary=claim_boundary,
    )

    output_path.mkdir(parents=True, exist_ok=True)
    _write_csv(output_path / "paper_objective_table.csv", objective_rows)
    _write_csv(output_path / "objective_curve_table.csv", curve_rows)
    _write_json(output_path / "method_ranking.json", ranking)
    _write_json(output_path / "claim_boundary.json", claim_boundary)
    _write_json(output_path / "paper_tables_report.json", report)
    return report


def _validate_stage7_2_inputs(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    panel_report: Mapping[str, Any],
    panel_summary: Mapping[str, Any],
    method_summary: Mapping[str, Any],
    fe_ledger: Mapping[str, Any],
) -> None:
    if panel_report.get("stage") != "7.2" or panel_report.get("status") != "PASS":
        raise ValueError("Stage 7.3 requires a PASS Stage 7.2 panel report.")
    if panel_report.get("next_status") != "READY_FOR_STAGE7_3_OBJECTIVE_RESULT_POLISH":
        raise ValueError("Stage 7.2 report is not ready for Stage 7.3.")
    if panel_summary.get("stage") != "7.2" or method_summary.get("stage") != "7.2":
        raise ValueError("Stage 7.3 requires Stage 7.2 summaries.")
    if fe_ledger.get("stage") != "7.2" or fe_ledger.get("FE_global_objective") != 120:
        raise ValueError("Stage 7.2 FE ledger is missing expected objective FEs.")
    if len(trace_rows) != int(panel_report["trace_row_count"]):
        raise ValueError("Trace row count does not match Stage 7.2 report.")
    if {row["method_name"] for row in trace_rows} != set(METHOD_NAMES):
        raise ValueError("Trace methods do not match locked Stage 7 method set.")
    if {row["synthetic_panel"] for row in trace_rows} != set(PANEL_NAMES):
        raise ValueError("Trace panels do not match locked Stage 7 panels.")
    forbidden_flags = [
        "llm_call_used",
        "new_candidate_generation_used",
        "selected_operator_revision_used",
        "evolution_search_used",
        "test_feedback_tuning_used",
        "baseopt_modified",
        "optimizer_generation_used",
        "controller_scheduler_generation_used",
    ]
    for field in forbidden_flags:
        if panel_report.get(field) is True:
            raise ValueError(f"Stage 7.2 report violates boundary: {field}")


def _build_objective_table(
    trace_rows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    rows_by_case: dict[tuple[str, int, int], list[Mapping[str, Any]]] = defaultdict(
        list
    )
    for row in trace_rows:
        case = (
            str(row["synthetic_panel"]),
            int(row["problem_dimension"]),
            int(row["seed"]),
        )
        rows_by_case[case].append(row)

    table: list[dict[str, Any]] = []
    for case in sorted(rows_by_case):
        case_rows = rows_by_case[case]
        final_by_method = {
            method: _final_row(case_rows, method) for method in METHOD_NAMES
        }
        identity_value = float(
            final_by_method["identity_no_coord"]["best_objective_so_far"]
        )
        ranks = _rank_methods(final_by_method)
        for method_name in METHOD_NAMES:
            final_row = final_by_method[method_name]
            final_value = float(final_row["best_objective_so_far"])
            delta = final_value - identity_value
            table.append(
                {
                    "stage": STAGE,
                    "source_stage": "7.2",
                    "synthetic_panel": final_row["synthetic_panel"],
                    "problem_dimension": int(final_row["problem_dimension"]),
                    "seed": int(final_row["seed"]),
                    "objective_name": final_row["objective_name"],
                    "method_name": method_name,
                    "final_best_objective": _round(final_value),
                    "identity_final_best_objective": _round(identity_value),
                    "delta_vs_identity": _round(delta),
                    "relative_delta_vs_identity": _round(
                        delta / max(abs(identity_value), 1e-12)
                    ),
                    "rank_in_panel_dimension": ranks[method_name],
                    "FE_global_objective": 3,
                    "FE_total": 6,
                    "same_budget_across_methods": True,
                    "lower_is_better": True,
                    "new_objective_evaluation_used": False,
                    "not_final_performance_claim": True,
                }
            )
    return table


def _build_curve_table(trace_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        trace_rows,
        key=lambda row: (
            str(row["synthetic_panel"]),
            int(row["problem_dimension"]),
            int(row["seed"]),
            METHOD_NAMES.index(str(row["method_name"])),
            int(row["objective_step"]),
        ),
    )
    table = []
    for row in sorted_rows:
        objective_step = int(row["objective_step"])
        table.append(
            {
                "stage": STAGE,
                "source_stage": "7.2",
                "synthetic_panel": row["synthetic_panel"],
                "problem_dimension": int(row["problem_dimension"]),
                "seed": int(row["seed"]),
                "objective_name": row["objective_name"],
                "method_name": row["method_name"],
                "objective_step": objective_step,
                "best_objective_so_far": _round(float(row["best_objective_so_far"])),
                "FE_global_objective_cumulative": objective_step,
                "FE_total_cumulative": objective_step * 2,
                "same_budget_across_methods": True,
                "new_objective_evaluation_used": False,
                "not_final_performance_claim": True,
            }
        )
    return table


def _build_method_ranking(
    objective_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    rows_by_method = {
        method: [row for row in objective_rows if row["method_name"] == method]
        for method in METHOD_NAMES
    }
    method_rows = []
    for method_name in METHOD_NAMES:
        rows = rows_by_method[method_name]
        final_values = [float(row["final_best_objective"]) for row in rows]
        ranks = [int(row["rank_in_panel_dimension"]) for row in rows]
        method_rows.append(
            {
                "method_name": method_name,
                "case_count": len(rows),
                "mean_final_best_objective": _round(float(np.mean(final_values))),
                "mean_rank": _round(float(np.mean(ranks))),
                "best_panel_dimension_count": sum(rank == 1 for rank in ranks),
                "mean_delta_vs_identity": _round(
                    float(np.mean([float(row["delta_vs_identity"]) for row in rows]))
                ),
            }
        )

    ordered = sorted(
        method_rows,
        key=lambda row: (
            float(row["mean_final_best_objective"]),
            METHOD_NAMES.index(str(row["method_name"])),
        ),
    )
    for index, row in enumerate(ordered, start=1):
        row["overall_rank"] = index

    selected = next(
        row for row in ordered if row["method_name"] == "selected_loco_operator"
    )
    return {
        "schema_version": RANKING_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.2",
        "ranking_metric": "mean_final_best_objective",
        "lower_is_better": True,
        "same_budget_across_methods": True,
        "best_overall_method": ordered[0]["method_name"],
        "selected_loco_operator_rank_overall": int(selected["overall_rank"]),
        "selected_loco_operator_best_panel_dimension_count": int(
            selected["best_panel_dimension_count"]
        ),
        "method_rows": ordered,
        "not_final_performance_claim": True,
        "not_sota_claim": True,
    }


def _build_claim_boundary(ranking: Mapping[str, Any]) -> dict[str, Any]:
    selected_rank = int(ranking["selected_loco_operator_rank_overall"])
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.2",
        "claim_scope": "paper-ready tables from synthetic Stage 7.2 traces",
        "allowed_claims": [
            "Stage 7.3 converts Stage 7.2 synthetic objective-loop traces into paper-ready tables and curve data.",
            "The Stage 7.2 synthetic panel ran under the same FE budget across locked methods.",
            "Current synthetic evidence is mixed and does not support a final performance or SOTA claim.",
        ],
        "forbidden_claims": [
            "final objective-value performance superiority",
            "SOTA improvement",
            "official CEC2013 benchmark success",
            "BaseOpt improvement",
            "optimizer generation",
        ],
        "selected_loco_not_best_overall": selected_rank != 1,
        "requires_optional_cec2013_decision": True,
        "new_objective_evaluation_used": False,
        "test_feedback_tuning_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "selected_operator_revision_used": False,
        "not_final_performance_claim": True,
        "not_sota_claim": True,
    }


def _build_report(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    objective_rows: Sequence[Mapping[str, Any]],
    curve_rows: Sequence[Mapping[str, Any]],
    ranking: Mapping[str, Any],
    claim_boundary: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.2",
        "polish_scope": "paper_ready_objective_tables",
        "source_trace_row_count": len(trace_rows),
        "paper_objective_row_count": len(objective_rows),
        "objective_curve_row_count": len(curve_rows),
        "method_count": len({row["method_name"] for row in objective_rows}),
        "panel_count": len({row["synthetic_panel"] for row in objective_rows}),
        "dimension_count": len({row["problem_dimension"] for row in objective_rows}),
        "best_overall_method": ranking["best_overall_method"],
        "selected_loco_operator_rank_overall": ranking[
            "selected_loco_operator_rank_overall"
        ],
        "claim_boundary_written": claim_boundary["status"] == "PASS",
        "new_objective_evaluation_used": False,
        "stage7_2_artifacts_modified": False,
        "not_final_performance_claim": True,
        "not_sota_claim": True,
        "next_status": "READY_FOR_OPTIONAL_CEC2013_OR_PAPER_DRAFT",
    }


def _rank_methods(final_by_method: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    ordered = sorted(
        METHOD_NAMES,
        key=lambda method: (
            float(final_by_method[method]["best_objective_so_far"]),
            METHOD_NAMES.index(method),
        ),
    )
    ranks: dict[str, int] = {}
    last_value: float | None = None
    last_rank = 0
    for index, method_name in enumerate(ordered, start=1):
        value = float(final_by_method[method_name]["best_objective_so_far"])
        if last_value is None or abs(value - last_value) > 1e-12:
            last_rank = index
            last_value = value
        ranks[method_name] = last_rank
    return ranks


def _final_row(
    rows: Sequence[Mapping[str, Any]], method_name: str
) -> Mapping[str, Any]:
    method_rows = [row for row in rows if row["method_name"] == method_name]
    if not method_rows:
        raise ValueError(f"Missing method rows: {method_name}")
    return sorted(method_rows, key=lambda row: int(row["objective_step"]))[-1]


def _round(value: float) -> float:
    return round(float(value), 12)


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


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    fieldnames = _fieldnames_for_rows(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(_csv_row(row, fieldnames))


def _fieldnames_for_rows(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    keys = list(rows[0].keys())
    if keys == OBJECTIVE_TABLE_COLUMNS or keys == CURVE_TABLE_COLUMNS:
        return keys
    return keys


def _csv_row(row: Mapping[str, Any], fieldnames: Iterable[str]) -> dict[str, Any]:
    output = {}
    for field in fieldnames:
        value = row[field]
        if isinstance(value, bool):
            output[field] = str(value).lower()
        else:
            output[field] = value
    return output

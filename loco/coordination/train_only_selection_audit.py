"""Stage 8.1 train-only selection audit.

This module audits the Stage 8.0 improvement trace and hardens selection when
the top-k cutoff cuts through a tie group. It does not use validation/test
feedback, run objectives or benchmarks, call LLMs, or generate new candidates.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "8.1"
AUDIT_SCHEMA_VERSION = "loco.stage8_1_train_only_selection_audit_report.v1"
TIE_SCHEMA_VERSION = "loco.stage8_1_tie_audit.v1"
RULE_SCHEMA_VERSION = "loco.stage8_1_hardened_selection_rule.v1"
DECISION_SCHEMA_VERSION = "loco.stage8_1_selection_decision.v1"


def run_stage8_1_train_only_selection_audit(
    *,
    improvement_trace_path: Path | str,
    improvement_candidates_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    trace_rows = _read_jsonl(Path(improvement_trace_path))
    improvements = _read_json(Path(improvement_candidates_path))
    _validate_inputs(trace_rows, improvements)

    original_top_k = int(improvements["improvement_top_k"])
    tie_audit = _build_tie_audit(trace_rows, original_top_k)
    hardened_rule = _build_hardened_rule(tie_audit, original_top_k)
    decision = _build_selection_decision(trace_rows, tie_audit)
    ledger = _build_fe_ledger(candidate_count=len(trace_rows))
    report = _build_audit_report(
        trace_rows=trace_rows,
        original_top_k=original_top_k,
        tie_audit=tie_audit,
        decision=decision,
        ledger=ledger,
    )
    route = _build_route()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "tie_audit.json", tie_audit)
    _write_json(output_path / "hardened_selection_rule.json", hardened_rule)
    _write_json(output_path / "selection_decision.json", decision)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "selection_audit_report.json", report)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    trace_rows: Sequence[Mapping[str, Any]], improvements: Mapping[str, Any]
) -> None:
    if improvements.get("stage") != "8.0":
        raise ValueError("Stage 8.1 requires Stage 8.0 improvement candidates.")
    if improvements.get("status") != "PASS":
        raise ValueError("Stage 8.1 requires Stage 8.0 improvement PASS.")
    if not trace_rows:
        raise ValueError("Stage 8.1 requires a non-empty improvement trace.")
    for row in trace_rows:
        if row.get("stage") != "8.0":
            raise ValueError("Stage 8.1 only audits Stage 8.0 trace rows.")
        if row.get("split") != "train":
            raise ValueError("Stage 8.1 only audits train-split trace rows.")
        if row.get("validation_feedback_used") is not False:
            raise ValueError("Stage 8.1 forbids validation feedback.")
        if row.get("test_feedback_used") is not False:
            raise ValueError("Stage 8.1 forbids test feedback.")
        if row.get("objective_evaluation_used") is not False:
            raise ValueError("Stage 8.1 forbids objective evaluation.")
        if row.get("benchmark_execution_used") is not False:
            raise ValueError("Stage 8.1 forbids benchmark execution.")
        if row.get("reported_results_used_as_runtime_feedback") is not False:
            raise ValueError("Stage 8.1 forbids reported-results feedback.")
        if row.get("not_performance_claim") is not True:
            raise ValueError("Stage 8.1 requires claim-boundary preservation.")


def _build_tie_audit(
    trace_rows: Sequence[Mapping[str, Any]], original_top_k: int
) -> dict[str, Any]:
    cutoff_row = trace_rows[original_top_k - 1]
    cutoff_score = float(cutoff_row["improvement_score"])
    tied_rows = [
        row for row in trace_rows if float(row["improvement_score"]) == cutoff_score
    ]
    tied_candidate_ids = [str(row["candidate_id"]) for row in tied_rows]
    included = {
        str(row["candidate_id"])
        for row in trace_rows[:original_top_k]
        if float(row["improvement_score"]) == cutoff_score
    }
    dropped = [
        candidate_id
        for candidate_id in tied_candidate_ids
        if candidate_id not in included
    ]
    boundary_tie_detected = bool(dropped)
    return {
        "schema_version": TIE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "cutoff_rank": int(original_top_k),
        "cutoff_score": cutoff_score,
        "boundary_tie_detected": boundary_tie_detected,
        "tie_group_size_at_cutoff": len(tied_rows),
        "tie_group_candidate_ids": tied_candidate_ids,
        "dropped_by_original_top_k": dropped,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "objective_evaluation_used": False,
        "benchmark_execution_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "not_performance_claim": True,
    }


def _build_hardened_rule(
    tie_audit: Mapping[str, Any], original_top_k: int
) -> dict[str, Any]:
    return {
        "schema_version": RULE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "rule_name": "include_all_candidates_tied_at_selection_cutoff",
        "original_top_k": int(original_top_k),
        "cutoff_score": float(tie_audit["cutoff_score"]),
        "boundary_tie_detected": bool(tie_audit["boundary_tie_detected"]),
        "hardened_candidate_count": len(tie_audit["tie_group_candidate_ids"]),
        "validation_usage": "selection only after train improvement",
        "test_usage": "sealed final reporting only",
        "not_performance_claim": True,
    }


def _build_selection_decision(
    trace_rows: Sequence[Mapping[str, Any]], tie_audit: Mapping[str, Any]
) -> dict[str, Any]:
    selection_ready_ids = set(tie_audit["tie_group_candidate_ids"])
    rows_by_id = {str(row["candidate_id"]): row for row in trace_rows}
    selection_ready = [
        {
            "candidate_id": candidate_id,
            "rank": int(rows_by_id[candidate_id]["rank"]),
            "operator_family": str(rows_by_id[candidate_id]["operator_family"]),
            "kind_sequence": str(rows_by_id[candidate_id]["kind_sequence"]),
            "improvement_score": float(rows_by_id[candidate_id]["improvement_score"]),
            "selection_status": "TRAIN_ONLY_SELECTION_READY_NOT_FINAL",
            "allowed_next_use": "validation selection only after train improvement",
            "not_performance_claim": True,
        }
        for candidate_id in tie_audit["tie_group_candidate_ids"]
        if candidate_id in selection_ready_ids
    ]
    selection_ready.sort(key=lambda row: (row["rank"], row["candidate_id"]))
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "selection_ready_candidates": selection_ready,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "objective_evaluation_used": False,
        "benchmark_execution_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "not_performance_claim": True,
    }


def _build_fe_ledger(candidate_count: int) -> dict[str, Any]:
    return {
        "schema_version": "loco.stage8_1_fe_ledger.v1",
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "train_only_selection_audit",
        "FE_grouping": 0,
        "FE_proposal": int(candidate_count),
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_total": int(candidate_count),
        "candidate_count": int(candidate_count),
        "cross_candidate_evaluations_shared": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "not_performance_claim": True,
    }


def _build_audit_report(
    *,
    trace_rows: Sequence[Mapping[str, Any]],
    original_top_k: int,
    tie_audit: Mapping[str, Any],
    decision: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.0",
        "candidate_count": len(trace_rows),
        "original_selection_top_k": int(original_top_k),
        "top_score_tie_count": len(tie_audit["tie_group_candidate_ids"]),
        "boundary_tie_detected": bool(tie_audit["boundary_tie_detected"]),
        "selection_rule_hardened": True,
        "hardened_selection_candidate_count": len(
            decision["selection_ready_candidates"]
        ),
        "FE_total": int(ledger["FE_total"]),
        "next_status": "READY_FOR_STAGE8_2_TRAIN_ONLY_BOUNDARY_LOCK",
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "objective_evaluation_used": False,
        "benchmark_execution_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "not_performance_claim": True,
    }


def _build_route() -> dict[str, Any]:
    return {
        "schema_version": "loco.stage8_1_next_route_decision.v1",
        "stage": STAGE,
        "status": "PASS",
        "decision": "LOCK_TRAIN_ONLY_SELECTION_AUDIT",
        "decision_reason": (
            "Stage 8.0 improvement trace was audited under a tie-hardened "
            "train-only selection cutoff."
        ),
        "next_stage": "Stage 8.2",
        "allowed_next_work": "train_only_boundary_lock_or_audit",
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
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

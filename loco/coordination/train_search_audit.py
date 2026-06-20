"""Stage 4.1 train-search audit and promotion-rule hardening.

This module audits Stage 4.0 train-only search artifacts. It hardens promotion
when the top-k cutoff cuts through an equal-score tie group. It does not use
validation/test feedback, execute ASTs, evaluate objectives, or make
performance claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "4.1"
AUDIT_SCHEMA_VERSION = "loco.stage4_1_train_search_audit_report.v1"
TIE_SCHEMA_VERSION = "loco.stage4_1_tie_audit.v1"
RULE_SCHEMA_VERSION = "loco.stage4_1_hardened_promotion_rule.v1"
DECISION_SCHEMA_VERSION = "loco.stage4_1_promotion_decision.v1"


def run_stage4_1_train_search_audit(
    *,
    search_trace_path: Path | str,
    promotion_candidates_path: Path | str,
    fe_ledger_path: Path | str,
    search_report_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    trace_rows = _read_jsonl(Path(search_trace_path))
    promotions = _read_json(Path(promotion_candidates_path))
    ledger = _read_json(Path(fe_ledger_path))
    search_report = _read_json(Path(search_report_path))
    _validate_stage4_0_inputs(trace_rows, promotions, ledger, search_report)

    original_top_k = int(promotions["promotion_top_k"])
    tie_audit = _build_tie_audit(trace_rows, original_top_k)
    hardened_rule = _build_hardened_rule(tie_audit, original_top_k)
    decision = _build_promotion_decision(trace_rows, tie_audit)
    report = _build_audit_report(
        trace_rows=trace_rows,
        original_top_k=original_top_k,
        tie_audit=tie_audit,
        decision=decision,
        ledger=ledger,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "tie_audit.json", tie_audit)
    _write_json(output_path / "hardened_promotion_rule.json", hardened_rule)
    _write_json(output_path / "promotion_decision.json", decision)
    _write_json(output_path / "train_search_audit_report.json", report)
    return report


def _validate_stage4_0_inputs(
    trace_rows: Sequence[Mapping[str, Any]],
    promotions: Mapping[str, Any],
    ledger: Mapping[str, Any],
    search_report: Mapping[str, Any],
) -> None:
    if search_report.get("status") != "PASS":
        raise ValueError("Stage 4.1 requires Stage 4.0 search_report PASS.")
    if search_report.get("stage") != "4.0":
        raise ValueError("Stage 4.1 requires Stage 4.0 search_report.")
    if promotions.get("stage") != "4.0":
        raise ValueError("Stage 4.1 requires Stage 4.0 promotion candidates.")
    if ledger.get("FE_total") != (
        ledger.get("FE_grouping", 0)
        + ledger.get("FE_proposal", 0)
        + ledger.get("FE_coordination_extra", 0)
        + ledger.get("FE_repair", 0)
    ):
        raise ValueError("Stage 4.0 FE ledger identity is invalid.")
    if not trace_rows:
        raise ValueError("Stage 4.1 requires non-empty search trace.")
    for row in trace_rows:
        if row.get("split") != "train":
            raise ValueError("Stage 4.1 only audits train-split trace rows.")
        if row.get("validation_feedback_used") is not False:
            raise ValueError("Stage 4.1 forbids validation feedback.")
        if row.get("test_feedback_used") is not False:
            raise ValueError("Stage 4.1 forbids test feedback.")
        if row.get("objective_evaluation_used") is not False:
            raise ValueError("Stage 4.1 forbids objective evaluation.")
        if row.get("not_performance_claim") is not True:
            raise ValueError("Stage 4.1 requires claim-boundary preservation.")


def _build_tie_audit(
    trace_rows: Sequence[Mapping[str, Any]], original_top_k: int
) -> dict[str, Any]:
    cutoff_row = trace_rows[original_top_k - 1]
    cutoff_score = float(cutoff_row["train_proxy_score"])
    tied_rows = [
        row for row in trace_rows if float(row["train_proxy_score"]) == cutoff_score
    ]
    tied_candidate_ids = [str(row["candidate_id"]) for row in tied_rows]
    included = {
        str(row["candidate_id"])
        for row in trace_rows[:original_top_k]
        if float(row["train_proxy_score"]) == cutoff_score
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
        "not_performance_claim": True,
    }


def _build_hardened_rule(
    tie_audit: Mapping[str, Any], original_top_k: int
) -> dict[str, Any]:
    return {
        "schema_version": RULE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "rule_name": "include_all_candidates_tied_at_cutoff",
        "original_top_k": int(original_top_k),
        "cutoff_score": float(tie_audit["cutoff_score"]),
        "boundary_tie_detected": bool(tie_audit["boundary_tie_detected"]),
        "hardened_candidate_count": len(tie_audit["tie_group_candidate_ids"]),
        "validation_usage": "selection only after train search",
        "test_usage": "sealed final reporting only",
        "not_performance_claim": True,
    }


def _build_promotion_decision(
    trace_rows: Sequence[Mapping[str, Any]], tie_audit: Mapping[str, Any]
) -> dict[str, Any]:
    validation_ready_ids = set(tie_audit["tie_group_candidate_ids"])
    rows_by_id = {str(row["candidate_id"]): row for row in trace_rows}
    validation_ready = [
        {
            "candidate_id": candidate_id,
            "rank": int(rows_by_id[candidate_id]["rank"]),
            "operator_family": str(rows_by_id[candidate_id]["operator_family"]),
            "kind_sequence": str(rows_by_id[candidate_id]["kind_sequence"]),
            "train_proxy_score": float(rows_by_id[candidate_id]["train_proxy_score"]),
            "promotion_status": "VALIDATION_READY_TIE_HARDENED_NOT_FINAL",
            "allowed_next_use": "validation selection only after train search",
            "not_performance_claim": True,
        }
        for candidate_id in tie_audit["tie_group_candidate_ids"]
        if candidate_id in validation_ready_ids
    ]
    validation_ready.sort(key=lambda row: (row["rank"], row["candidate_id"]))
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "validation_ready_candidates": validation_ready,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "objective_evaluation_used": False,
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
        "source_stage": "4.0",
        "candidate_count": len(trace_rows),
        "original_promotion_top_k": int(original_top_k),
        "top_score_tie_count": len(tie_audit["tie_group_candidate_ids"]),
        "boundary_tie_detected": bool(tie_audit["boundary_tie_detected"]),
        "promotion_rule_hardened": True,
        "hardened_promotion_candidate_count": len(
            decision["validation_ready_candidates"]
        ),
        "FE_total": int(ledger["FE_total"]),
        "next_status": "READY_FOR_STAGE5_VALIDATION_SELECTION",
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "objective_evaluation_used": False,
        "ast_execution_used": False,
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

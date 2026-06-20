"""Candidate artifact logging and replay verification for Stage 2.6.

This module records typed AST candidate preflight decisions as auditable JSONL
artifacts. It does not generate candidates, call LLMs, run evolution, execute
operators, or evaluate objectives.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from loco.coordination.dsl import stage3_preflight_check


CANDIDATE_LOG_SCHEMA_VERSION = "loco.candidate_log.v1"
STAGE = "2.6"
SPLIT = "pre_stage3_schema_only"
DEFAULT_STAGE2_6_LOG_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "candidates" / "stage2_6"
)


@dataclass(frozen=True)
class CandidateLoggingResult:
    total_count: int
    accepted_count: int
    rejected_count: int
    accepted_log_path: Path
    rejected_log_path: Path
    replay_report_path: Path


def log_candidate_preflight(
    candidate_payloads: Sequence[Mapping[str, Any]],
    shared_variables: set[int] | frozenset[int],
    output_dir: Path | str = DEFAULT_STAGE2_6_LOG_DIR,
    source_stage: str = "stage2_6_rejection_corpus",
) -> CandidateLoggingResult:
    output_path = Path(output_dir)
    accepted_log_path = output_path / "accepted_candidates.jsonl"
    rejected_log_path = output_path / "rejected_candidates.jsonl"
    replay_report_path = output_path / "replay_report.json"
    output_path.mkdir(parents=True, exist_ok=True)

    preflight = stage3_preflight_check(candidate_payloads, shared_variables)
    payload_by_id = {
        _candidate_id_from_payload(payload, index): dict(payload)
        for index, payload in enumerate(candidate_payloads)
    }

    accepted_rows = []
    for accepted in preflight.accepted:
        payload = payload_by_id[accepted.candidate_id]
        accepted_rows.append(
            _base_row(
                candidate_id=accepted.candidate_id,
                decision="accepted",
                ast_payload=payload,
                source_stage=source_stage,
            )
            | {
                "serialized_ast": accepted.serialized_ast,
                "ast_fingerprint_sha256": accepted.fingerprint_sha256,
            }
        )

    rejected_rows = []
    for rejected in preflight.rejected:
        payload = payload_by_id[rejected.candidate_id]
        rejected_rows.append(
            _base_row(
                candidate_id=rejected.candidate_id,
                decision="rejected",
                ast_payload=payload,
                source_stage=source_stage,
            )
            | {
                "reject_reason": rejected.reject_reason,
                "reject_reason_category": categorize_reject_reason(
                    rejected.reject_reason
                ),
            }
        )

    _write_jsonl(accepted_log_path, accepted_rows)
    _write_jsonl(rejected_log_path, rejected_rows)
    replay_candidate_logs(
        accepted_log_path=accepted_log_path,
        rejected_log_path=rejected_log_path,
        shared_variables=shared_variables,
        report_path=replay_report_path,
    )
    return CandidateLoggingResult(
        total_count=preflight.total_count,
        accepted_count=preflight.accepted_count,
        rejected_count=preflight.rejected_count,
        accepted_log_path=accepted_log_path,
        rejected_log_path=rejected_log_path,
        replay_report_path=replay_report_path,
    )


def replay_candidate_logs(
    accepted_log_path: Path | str,
    rejected_log_path: Path | str,
    shared_variables: set[int] | frozenset[int],
    report_path: Path | str,
) -> dict[str, Any]:
    accepted_path = Path(accepted_log_path)
    rejected_path = Path(rejected_log_path)
    if not accepted_path.is_file():
        raise FileNotFoundError(accepted_path)
    if not rejected_path.is_file():
        raise FileNotFoundError(rejected_path)

    accepted_rows = _read_jsonl(accepted_path)
    rejected_rows = _read_jsonl(rejected_path)
    fingerprint_mismatch_count = 0
    decision_mismatch_count = 0
    category_mismatch_count = 0

    for row in accepted_rows:
        report = stage3_preflight_check([row["ast_payload"]], shared_variables)
        if report.accepted_count != 1:
            decision_mismatch_count += 1
            continue
        fingerprint = report.accepted[0].fingerprint_sha256
        if fingerprint != row.get("ast_fingerprint_sha256"):
            fingerprint_mismatch_count += 1

    for row in rejected_rows:
        report = stage3_preflight_check([row["ast_payload"]], shared_variables)
        if report.rejected_count != 1:
            decision_mismatch_count += 1
            continue
        category = categorize_reject_reason(report.rejected[0].reject_reason)
        if category != row.get("reject_reason_category"):
            category_mismatch_count += 1

    status = (
        "PASS"
        if fingerprint_mismatch_count == 0
        and decision_mismatch_count == 0
        and category_mismatch_count == 0
        else "FAIL"
    )
    result = {
        "schema_version": "loco.candidate_replay_report.v1",
        "stage": STAGE,
        "status": status,
        "total_count": len(accepted_rows) + len(rejected_rows),
        "accepted_count": len(accepted_rows),
        "rejected_count": len(rejected_rows),
        "fingerprint_mismatch_count": fingerprint_mismatch_count,
        "decision_mismatch_count": decision_mismatch_count,
        "category_mismatch_count": category_mismatch_count,
        "reject_reason_categories": sorted(
            {str(row.get("reject_reason_category")) for row in rejected_rows}
        ),
        "no_llm": True,
        "no_evolution": True,
        "no_test_feedback": True,
        "claim": "candidate artifact logging schema replay verifier",
    }
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def replay_rejection_corpus(
    corpus_path: Path | str,
    shared_variables: set[int] | frozenset[int],
    report_path: Path | str,
) -> dict[str, Any]:
    path = Path(corpus_path)
    rows = _read_jsonl(path)
    log_candidate_preflight(
        [row["ast_payload"] for row in rows],
        shared_variables=shared_variables,
        output_dir=path.parent,
        source_stage="stage2_6_rejection_corpus",
    )
    return replay_candidate_logs(
        accepted_log_path=path.parent / "accepted_candidates.jsonl",
        rejected_log_path=path.parent / "rejected_candidates.jsonl",
        shared_variables=shared_variables,
        report_path=report_path,
    )


def categorize_reject_reason(reason: str) -> str:
    text = reason.lower()
    if "non-shared variables" in text:
        return "non_shared_target"
    if "forbidden dsl node kind" in text or "optimizer" in text or "controller" in text:
        return "forbidden_optimizer_or_controller"
    if "executable code" in text:
        return "executable_code"
    if "forbidden metadata" in text:
        return "forbidden_metadata"
    if "schema_version" in text or "unknown top-level fields" in text:
        return "invalid_schema"
    return "schema_or_validation"


def _base_row(
    candidate_id: str,
    decision: str,
    ast_payload: Mapping[str, Any],
    source_stage: str,
) -> dict[str, Any]:
    return {
        "log_schema_version": CANDIDATE_LOG_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": source_stage,
        "candidate_id": candidate_id,
        "decision": decision,
        "split": SPLIT,
        "ast_payload": dict(ast_payload),
        "candidate_payload_sha256": _fingerprint_payload(ast_payload),
        "no_llm": True,
        "no_evolution": True,
        "no_optimizer": True,
        "no_test_feedback": True,
        "no_objective_evaluation": True,
    }


def _candidate_id_from_payload(payload: Mapping[str, Any], index: int) -> str:
    candidate_id = payload.get("operator_id")
    if isinstance(candidate_id, str) and candidate_id:
        return candidate_id
    return f"candidate_{index}"


def _fingerprint_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

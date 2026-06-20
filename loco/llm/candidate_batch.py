"""Stage 3.1 train-only LLM candidate batch logging.

This module parses already captured small-batch LLM candidate output and writes
auditable train-only accepted/rejected logs. It does not call LLMs, run
evolution, execute ASTs, evaluate objectives, or implement optimizers.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from loco.coordination.candidate_logging import categorize_reject_reason
from loco.llm.ast_candidate_schema import (
    load_llm_candidate_payload,
    validate_llm_candidate_payload,
)


RAW_BATCH_SCHEMA_VERSION = "loco.stage3_1_raw_llm_batch.v1"
STAGE3_1_REPLAY_SCHEMA_VERSION = "loco.stage3_1_candidate_replay.v1"
STAGE = "3.1"
SPLIT = "train"
REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_stage3_1_raw_batch(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the Stage 3.1 raw batch envelope without validating each AST."""

    if not isinstance(payload, Mapping):
        raise ValueError("Stage 3.1 raw batch must be a mapping.")
    if payload.get("schema_version") != RAW_BATCH_SCHEMA_VERSION:
        raise ValueError("unsupported Stage 3.1 raw batch schema_version")
    if payload.get("stage") != STAGE:
        raise ValueError("Stage 3.1 raw batch stage must be 3.1")
    if payload.get("split") != SPLIT:
        raise ValueError("Stage 3.1 raw batch split must be train")
    candidates = payload.get("candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise ValueError("Stage 3.1 raw batch candidates must be a list.")
    if not candidates:
        raise ValueError("Stage 3.1 raw batch must contain candidates.")
    return dict(payload)


def process_stage3_1_candidate_batch(
    *,
    raw_output_path: Path | str,
    output_dir: Path | str,
    shared_variables: set[int] | frozenset[int],
    protocol_report_path: Path | str,
) -> dict[str, Any]:
    """Process captured candidate output into train-only audit logs."""

    _require_stage3_0_protocol_pass(Path(protocol_report_path))
    raw_path = Path(raw_output_path)
    raw_payload = parse_stage3_1_raw_batch(
        json.loads(raw_path.read_text(encoding="utf-8"))
    )
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    accepted_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    for index, candidate_payload in enumerate(raw_payload["candidates"]):
        if not isinstance(candidate_payload, Mapping):
            rejected_rows.append(
                _rejected_row(
                    candidate_id=f"candidate_{index}",
                    candidate_payload={"invalid_payload": str(candidate_payload)},
                    reject_reason="LLM candidate payload must be a mapping.",
                    raw_output_path=raw_path,
                )
            )
            continue

        candidate_id = _candidate_id_from_payload(candidate_payload, index)
        try:
            candidate = load_llm_candidate_payload(candidate_payload)
            validation = validate_llm_candidate_payload(
                candidate,
                shared_variables=shared_variables,
            )
        except ValueError as exc:
            rejected_rows.append(
                _rejected_row(
                    candidate_id=candidate_id,
                    candidate_payload=candidate_payload,
                    reject_reason=str(exc),
                    raw_output_path=raw_path,
                )
            )
            continue

        accepted_rows.append(
            _base_row(
                candidate_id=candidate_id,
                decision="accepted",
                candidate_payload=candidate_payload,
                raw_output_path=raw_path,
            )
            | {
                "ast_operator_id": validation.ast_operator_id,
                "target_scope": validation.target_scope,
                "ast_fingerprint_sha256": validation.ast_fingerprint_sha256,
            }
        )

    accepted_log_path = output_path / "accepted_candidates.jsonl"
    rejected_log_path = output_path / "rejected_candidates.jsonl"
    replay_report_path = output_path / "replay_report.json"
    _write_jsonl(accepted_log_path, accepted_rows)
    _write_jsonl(rejected_log_path, rejected_rows)
    replay = replay_stage3_1_candidate_logs(
        accepted_log_path=accepted_log_path,
        rejected_log_path=rejected_log_path,
        report_path=replay_report_path,
    )
    return {
        "schema_version": "loco.stage3_1_candidate_batch_result.v1",
        "stage": STAGE,
        "status": replay["status"],
        "split": SPLIT,
        "raw_output_path": _display_path(raw_path),
        "accepted_count": replay["accepted_count"],
        "rejected_count": replay["rejected_count"],
        "accepted_log_path": _display_path(accepted_log_path),
        "rejected_log_path": _display_path(rejected_log_path),
        "replay_report_path": _display_path(replay_report_path),
        "no_llm_call_by_module": True,
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }


def replay_stage3_1_candidate_logs(
    *,
    accepted_log_path: Path | str,
    rejected_log_path: Path | str,
    report_path: Path | str,
) -> dict[str, Any]:
    accepted_rows = _read_jsonl(Path(accepted_log_path))
    rejected_rows = _read_jsonl(Path(rejected_log_path))
    all_rows = accepted_rows + rejected_rows

    split_violations = [
        row["candidate_id"] for row in all_rows if row.get("split") != SPLIT
    ]
    test_feedback_violations = [
        row["candidate_id"]
        for row in all_rows
        if row.get("no_test_feedback") is not True
        or row.get("test_feedback_used") is True
        or row.get("tuned_on_test") is True
    ]
    execution_violations = [
        row["candidate_id"]
        for row in all_rows
        if row.get("no_evolution") is not True
        or row.get("no_objective_evaluation") is not True
        or row.get("no_optimizer") is not True
    ]
    fingerprint_mismatch_count = sum(
        1
        for row in all_rows
        if row.get("candidate_payload_sha256")
        != _fingerprint_payload(row.get("llm_candidate_payload", {}))
    )
    status = (
        "PASS"
        if not split_violations
        and not test_feedback_violations
        and not execution_violations
        and fingerprint_mismatch_count == 0
        else "FAIL"
    )
    report = {
        "schema_version": STAGE3_1_REPLAY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": status,
        "split": SPLIT,
        "accepted_count": len(accepted_rows),
        "rejected_count": len(rejected_rows),
        "split_violation_count": len(split_violations),
        "test_feedback_violation_count": len(test_feedback_violations),
        "execution_violation_count": len(execution_violations),
        "fingerprint_mismatch_count": fingerprint_mismatch_count,
        "reject_reason_categories": sorted(
            {str(row.get("reject_reason_category")) for row in rejected_rows}
        ),
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def _require_stage3_0_protocol_pass(path: Path) -> None:
    report = json.loads(_resolve_path(path).read_text(encoding="utf-8"))
    if report.get("schema_version") != "loco.stage3_protocol_lock.v1":
        raise ValueError("Stage 3.0 protocol lock report has unsupported schema.")
    if report.get("status") != "PASS":
        raise ValueError("Stage 3.0 protocol lock must be PASS before Stage 3.1.")
    if report.get("stage3_allowed") is not True:
        raise ValueError("Stage 3.0 protocol lock must allow Stage 3.")


def _rejected_row(
    *,
    candidate_id: str,
    candidate_payload: Mapping[str, Any],
    reject_reason: str,
    raw_output_path: Path,
) -> dict[str, Any]:
    return _base_row(
        candidate_id=candidate_id,
        decision="rejected",
        candidate_payload=candidate_payload,
        raw_output_path=raw_output_path,
    ) | {
        "reject_reason": reject_reason,
        "reject_reason_category": categorize_reject_reason(reject_reason),
    }


def _base_row(
    *,
    candidate_id: str,
    decision: str,
    candidate_payload: Mapping[str, Any],
    raw_output_path: Path,
) -> dict[str, Any]:
    return {
        "log_schema_version": "loco.stage3_1_candidate_log.v1",
        "stage": STAGE,
        "split": SPLIT,
        "source_stage": "stage3_1_small_batch_llm_candidate_generation",
        "candidate_id": candidate_id,
        "decision": decision,
        "llm_candidate_payload": dict(candidate_payload),
        "candidate_payload_sha256": _fingerprint_payload(candidate_payload),
        "raw_output_path": _display_path(raw_output_path),
        "no_llm_call_by_module": True,
        "llm_output_captured": True,
        "no_evolution": True,
        "no_optimizer": True,
        "no_objective_evaluation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }


def _candidate_id_from_payload(payload: Mapping[str, Any], index: int) -> str:
    candidate_id = payload.get("candidate_id")
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


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _display_path(path: Path) -> str:
    resolved = _resolve_path(path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()

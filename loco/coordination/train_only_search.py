"""Stage 4.0 train-only search over frozen coordination candidates.

This module ranks already-frozen Stage 3.6 candidates using deterministic
train-only proxy signals. It does not call an LLM, generate new candidates,
execute ASTs, evaluate objectives, or use validation/test feedback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "4.0"
TRACE_SCHEMA_VERSION = "loco.stage4_0_search_trace.v1"
PROMOTION_SCHEMA_VERSION = "loco.stage4_0_promotion_candidates.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage4_0_fe_ledger.v1"
REPORT_SCHEMA_VERSION = "loco.stage4_0_search_report.v1"


def run_stage4_0_train_only_search(
    *,
    frozen_pool_path: Path | str,
    family_space_config_path: Path | str,
    output_dir: Path | str,
    promotion_top_k: int = 3,
) -> dict[str, Any]:
    """Run deterministic train-only candidate ranking over the frozen pool."""

    frozen_rows = _read_jsonl(Path(frozen_pool_path))
    family_lock = _read_family_lock(Path(family_space_config_path))
    _validate_inputs(frozen_rows, family_lock)

    trace_rows = sorted(
        (_score_candidate(row, family_lock) for row in frozen_rows),
        key=lambda row: (-float(row["train_proxy_score"]), str(row["candidate_id"])),
    )
    ranked_trace = [row | {"rank": index + 1} for index, row in enumerate(trace_rows)]
    promotion_rows = [
        _promotion_row(row) for row in ranked_trace[: int(promotion_top_k)]
    ]
    ledger = _build_fe_ledger(candidate_count=len(ranked_trace))
    promotions = _build_promotions(promotion_rows, promotion_top_k)
    report = _build_report(
        candidate_count=len(ranked_trace),
        promotion_count=len(promotion_rows),
        family_lock=family_lock,
        ledger=ledger,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "search_trace.jsonl", ranked_trace)
    _write_json(output_path / "promotion_candidates.json", promotions)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "search_report.json", report)
    return report


def _validate_inputs(
    frozen_rows: Sequence[Mapping[str, Any]], family_lock: Mapping[str, Any]
) -> None:
    if family_lock["stage"] != "3.7":
        raise ValueError("Stage 4.0 requires the Stage 3.7 family lock.")
    if family_lock["allowed_split"] != "train":
        raise ValueError("Stage 4.0 requires train-only split.")
    if not frozen_rows:
        raise ValueError("Stage 4.0 requires a non-empty frozen pool.")

    for row in frozen_rows:
        if row.get("frozen") is not True:
            raise ValueError("Stage 4.0 only accepts frozen candidates.")
        if row.get("split") != "train":
            raise ValueError("Stage 4.0 only accepts train-split candidates.")
        if row.get("target_scope") != "shared_variables_only":
            raise ValueError("Stage 4.0 only accepts shared-variable candidates.")
        if row.get("not_performance_claim") is not True:
            raise ValueError("Frozen candidates must preserve claim boundary.")


def _score_candidate(
    row: Mapping[str, Any], family_lock: Mapping[str, Any]
) -> dict[str, Any]:
    kinds = str(row["kind_sequence"]).split("->")
    unique_kinds = len(set(kinds))
    node_count = int(row["node_count"])
    target_count = len(row.get("target_variable_set", []))
    family_name = _family_name_for_kinds(kinds, family_lock)

    family_bonus = 0.10 if family_name is not None else 0.0
    diversity_score = unique_kinds / max(node_count, 1)
    compactness_score = 1.0 / (1.0 + max(node_count - 2, 0))
    shared_scope_score = 1.0 if row["target_scope"] == "shared_variables_only" else 0.0
    train_proxy_score = round(
        0.45 * diversity_score
        + 0.25 * compactness_score
        + 0.20 * shared_scope_score
        + family_bonus,
        6,
    )

    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "3.6",
        "candidate_id": str(row["candidate_id"]),
        "operator_family": str(row["operator_family"]),
        "matched_family_lock_name": family_name,
        "kind_sequence": str(row["kind_sequence"]),
        "node_count": node_count,
        "unique_kind_count": unique_kinds,
        "target_variable_count": target_count,
        "target_scope": str(row["target_scope"]),
        "split": "train",
        "train_proxy_score": train_proxy_score,
        "score_components": {
            "diversity_score": round(diversity_score, 6),
            "compactness_score": round(compactness_score, 6),
            "shared_scope_score": shared_scope_score,
            "family_lock_bonus": family_bonus,
        },
        "selection_metric": "deterministic_train_proxy_score",
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "ast_execution_used": False,
        "objective_evaluation_used": False,
        "not_performance_claim": True,
    }


def _family_name_for_kinds(
    kinds: Sequence[str], family_lock: Mapping[str, Any]
) -> str | None:
    primitive_to_family = family_lock["primitive_to_family"]
    matches = [
        primitive_to_family[kind] for kind in kinds if kind in primitive_to_family
    ]
    if not matches:
        return None
    return sorted(set(matches))[0]


def _promotion_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "rank": int(row["rank"]),
        "candidate_id": str(row["candidate_id"]),
        "operator_family": str(row["operator_family"]),
        "kind_sequence": str(row["kind_sequence"]),
        "train_proxy_score": float(row["train_proxy_score"]),
        "promotion_status": "VALIDATION_READY_NOT_SELECTED_FINAL",
        "allowed_next_use": "validation selection only after train search",
        "not_performance_claim": True,
    }


def _build_promotions(
    promotion_rows: Sequence[Mapping[str, Any]], promotion_top_k: int
) -> dict[str, Any]:
    return {
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "promotion_top_k": int(promotion_top_k),
        "promotion_candidates": list(promotion_rows),
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "not_performance_claim": True,
    }


def _build_fe_ledger(candidate_count: int) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "train_only_candidate_search",
        "FE_grouping": 0,
        "FE_proposal": int(candidate_count),
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_total": int(candidate_count),
        "candidate_count": int(candidate_count),
        "cross_candidate_evaluations_shared": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    candidate_count: int,
    promotion_count: int,
    family_lock: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "3.6",
        "family_lock_stage": family_lock["stage"],
        "candidate_count": int(candidate_count),
        "promotion_candidate_count": int(promotion_count),
        "candidate_pool_frozen": True,
        "allowed_split": "train",
        "train_only_search_executed": True,
        "next_status": "READY_FOR_STAGE4_1_TRAIN_SEARCH_AUDIT",
        "FE_total": int(ledger["FE_total"]),
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "ast_execution_used": False,
        "objective_evaluation_used": False,
        "optimizer_generation_used": False,
        "baseopt_modified": False,
        "not_performance_claim": True,
    }


def _read_family_lock(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stage = _extract_quoted_value(text, "stage")
    allowed_split = _extract_quoted_value(text, "allowed_split")
    primitive_to_family: dict[str, str] = {}
    current_family: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("name: "):
            current_family = line.split('"', 2)[1]
        if line.startswith("allowed_primitives: [") and current_family is not None:
            primitive_text = line.split("[", 1)[1].split("]", 1)[0]
            for item in primitive_text.split(","):
                primitive = item.strip().strip('"')
                if primitive:
                    primitive_to_family.setdefault(primitive, current_family)
    return {
        "stage": stage,
        "allowed_split": allowed_split,
        "primitive_to_family": primitive_to_family,
    }


def _extract_quoted_value(text: str, key: str) -> str:
    prefix = f"{key}: "
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith(prefix):
            return line.split('"', 2)[1]
    raise ValueError(f"Missing config key: {key}")


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

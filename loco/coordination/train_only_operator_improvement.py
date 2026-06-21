"""Stage 8.0 train-only operator improvement.

This module improves the frozen Stage 3.6 coordination candidate pool using
deterministic train-only signals and the locked Stage 7.6 comparator contract.
It does not call LLMs, generate new candidates, execute ASTs, evaluate
objectives, run benchmarks, or use validation/test feedback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "8.0"
TRACE_SCHEMA_VERSION = "loco.stage8_0_improvement_trace.v1"
CANDIDATES_SCHEMA_VERSION = "loco.stage8_0_improvement_candidates.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_0_fe_ledger.v1"
REPORT_SCHEMA_VERSION = "loco.stage8_0_improvement_report.v1"
ROUTE_SCHEMA_VERSION = "loco.stage8_0_next_route_decision.v1"


def run_stage8_0_train_only_operator_improvement(
    *,
    frozen_pool_path: Path | str,
    family_space_config_path: Path | str,
    output_dir: Path | str,
    improvement_top_k: int = 4,
    comparator_contract_path: Path | str | None = None,
    comparator_audit_report_path: Path | str | None = None,
) -> dict[str, Any]:
    """Run deterministic train-only improvement over the frozen pool."""

    frozen_rows = _read_jsonl(Path(frozen_pool_path))
    family_lock = _read_family_lock(Path(family_space_config_path))
    comparator_contract = _read_comparator_contract(
        Path(comparator_contract_path)
        if comparator_contract_path is not None
        else Path(__file__).resolve().parents[2]
        / "configs"
        / "stage7_6_reported_results_comparator_audit.yaml"
    )
    comparator_audit = _read_comparator_audit_report(
        Path(comparator_audit_report_path)
        if comparator_audit_report_path is not None
        else Path(__file__).resolve().parents[2]
        / "artifacts"
        / "objective_eval"
        / "stage7_6"
        / "reported_results_comparator_audit_report.json"
    )
    _validate_inputs(frozen_rows, family_lock, comparator_contract, comparator_audit)

    trace_rows = sorted(
        (_score_candidate(row, family_lock, comparator_audit) for row in frozen_rows),
        key=lambda row: (-float(row["improvement_score"]), str(row["candidate_id"])),
    )
    ranked_trace = [row | {"rank": index + 1} for index, row in enumerate(trace_rows)]
    improvement_rows = [
        _improvement_row(row) for row in ranked_trace[: int(improvement_top_k)]
    ]
    ledger = _build_fe_ledger(candidate_count=len(ranked_trace))
    improvements = _build_improvements(improvement_rows, improvement_top_k)
    report = _build_report(
        candidate_count=len(ranked_trace),
        improvement_count=len(improvement_rows),
        family_lock=family_lock,
        comparator_contract=comparator_contract,
        comparator_audit=comparator_audit,
        ledger=ledger,
    )
    route = _build_route()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "improvement_trace.jsonl", ranked_trace)
    _write_json(output_path / "improvement_candidates.json", improvements)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "improvement_report.json", report)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    frozen_rows: Sequence[Mapping[str, Any]],
    family_lock: Mapping[str, Any],
    comparator_contract: Mapping[str, Any],
    comparator_audit: Mapping[str, Any],
) -> None:
    if family_lock["stage"] != "3.7":
        raise ValueError("Stage 8.0 requires the Stage 3.7 family lock.")
    if family_lock["allowed_split"] != "train":
        raise ValueError("Stage 8.0 requires train-only split.")
    if comparator_contract["stage"] != "7.6":
        raise ValueError("Stage 8.0 requires the Stage 7.6 comparator contract.")
    if comparator_audit.get("status") != "PASS":
        raise ValueError("Stage 8.0 requires Stage 7.6 comparator audit PASS.")
    if comparator_audit.get("stage") != "7.6":
        raise ValueError("Stage 8.0 requires the Stage 7.6 comparator audit.")
    if not frozen_rows:
        raise ValueError("Stage 8.0 requires a non-empty frozen pool.")

    for row in frozen_rows:
        if row.get("stage") != "3.6":
            raise ValueError("Stage 8.0 only accepts Stage 3.6 frozen candidates.")
        if row.get("frozen") is not True:
            raise ValueError("Stage 8.0 only accepts frozen candidates.")
        if row.get("split") != "train":
            raise ValueError("Stage 8.0 only accepts train-split candidates.")
        if row.get("target_scope") != "shared_variables_only":
            raise ValueError("Stage 8.0 only accepts shared-variable candidates.")
        if row.get("not_performance_claim") is not True:
            raise ValueError("Stage 8.0 requires claim-boundary preservation.")


def _score_candidate(
    row: Mapping[str, Any],
    family_lock: Mapping[str, Any],
    comparator_audit: Mapping[str, Any],
) -> dict[str, Any]:
    kinds = str(row["kind_sequence"]).split("->")
    node_count = int(row["node_count"])
    unique_kinds = len(set(kinds))
    target_count = len(row.get("target_variable_set", []))
    family_names = _family_names_for_kinds(kinds, family_lock)
    family_coverage_count = len(family_names)

    shared_scope_score = 1.0 if row["target_scope"] == "shared_variables_only" else 0.0
    comparator_boundary_score = 1.0 if comparator_audit.get("status") == "PASS" else 0.0
    family_coverage_score = min(family_coverage_count / 3.0, 1.0)
    diversity_score = unique_kinds / max(node_count, 1)
    compactness_score = 1.0 / float(max(node_count, 1))
    improvement_score = round(
        0.45 * family_coverage_score
        + 0.20 * diversity_score
        + 0.15 * compactness_score
        + 0.10 * shared_scope_score
        + 0.10 * comparator_boundary_score,
        6,
    )

    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "7.6",
        "candidate_pool_source_stage": "3.6",
        "candidate_id": str(row["candidate_id"]),
        "operator_family": str(row["operator_family"]),
        "kind_sequence": str(row["kind_sequence"]),
        "node_count": node_count,
        "unique_kind_count": unique_kinds,
        "target_variable_count": target_count,
        "target_scope": str(row["target_scope"]),
        "split": "train",
        "family_names": family_names,
        "family_coverage_count": family_coverage_count,
        "improvement_score": improvement_score,
        "score_components": {
            "family_coverage_score": round(family_coverage_score, 6),
            "diversity_score": round(diversity_score, 6),
            "compactness_score": round(compactness_score, 6),
            "shared_scope_score": shared_scope_score,
            "comparator_boundary_score": comparator_boundary_score,
        },
        "selection_metric": "deterministic_train_only_improvement_score",
        "comparator_contract_used": True,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "ast_execution_used": False,
        "objective_evaluation_used": False,
        "benchmark_execution_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "not_performance_claim": True,
    }


def _family_names_for_kinds(
    kinds: Sequence[str], family_lock: Mapping[str, Any]
) -> list[str]:
    primitive_to_family = family_lock["primitive_to_family"]
    family_names = {
        primitive_to_family[kind] for kind in kinds if kind in primitive_to_family
    }
    return sorted(family_names)


def _improvement_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "rank": int(row["rank"]),
        "candidate_id": str(row["candidate_id"]),
        "operator_family": str(row["operator_family"]),
        "kind_sequence": str(row["kind_sequence"]),
        "improvement_score": float(row["improvement_score"]),
        "improvement_status": "TRAIN_ONLY_RECORDED",
        "allowed_next_use": "train-only selection or audit after improvement",
        "not_performance_claim": True,
    }


def _build_improvements(
    improvement_rows: Sequence[Mapping[str, Any]], improvement_top_k: int
) -> dict[str, Any]:
    return {
        "schema_version": CANDIDATES_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "improvement_top_k": int(improvement_top_k),
        "improvement_candidates": list(improvement_rows),
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "not_performance_claim": True,
    }


def _build_fe_ledger(candidate_count: int) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "train_only_operator_improvement",
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


def _build_report(
    *,
    candidate_count: int,
    improvement_count: int,
    family_lock: Mapping[str, Any],
    comparator_contract: Mapping[str, Any],
    comparator_audit: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.6",
        "candidate_pool_source_stage": "3.6",
        "candidate_count": int(candidate_count),
        "improvement_candidate_count": int(improvement_count),
        "candidate_pool_frozen": True,
        "frozen_candidate_pool_used": True,
        "comparator_contract_used": True,
        "comparator_contract_stage": comparator_contract["stage"],
        "comparator_contract_status": "LOCKED",
        "comparator_audit_status": comparator_audit["status"],
        "comparator_audit_source_stage": comparator_audit["source_stage"],
        "comparator_registry_size": int(comparator_audit["registry_size"]),
        "direct_comparator_count": int(comparator_audit["direct_comparator_count"]),
        "background_only_count": int(comparator_audit["background_only_count"]),
        "not_admissible_count": int(comparator_audit["not_admissible_count"]),
        "allowed_split": family_lock["allowed_split"],
        "train_only_improvement_executed": True,
        "next_status": "READY_FOR_STAGE8_1_TRAIN_ONLY_SELECTION_AUDIT",
        "FE_total": int(ledger["FE_total"]),
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "ast_execution_used": False,
        "objective_evaluation_used": False,
        "benchmark_execution_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "optimizer_generation_used": False,
        "controller_generation_used": False,
        "scheduler_generation_used": False,
        "baseopt_modified": False,
        "not_performance_claim": True,
    }


def _build_route() -> dict[str, Any]:
    return {
        "schema_version": ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": "LOCK_TRAIN_ONLY_OPERATOR_IMPROVEMENT",
        "decision_reason": (
            "Frozen Stage 3.6 candidates were improved only under train-only signals "
            "and the Stage 7.6 comparator contract."
        ),
        "next_stage": "Stage 8.1",
        "allowed_next_work": "train_only_selection_or_audit",
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _read_family_lock(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stage = _extract_quoted_value(text, "stage")
    allowed_split = _extract_quoted_value(text, "allowed_split")
    primitive_to_family: dict[str, str] = {}
    families: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_family_block = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("- id: "):
            if current is not None:
                families.append(current)
            current = {
                "id": _quoted_after_colon(line),
                "name": None,
                "allowed_primitives": [],
            }
            in_family_block = True
            continue
        if not in_family_block or current is None:
            continue
        if line.startswith("name: ") and current["name"] is None:
            current["name"] = _quoted_after_colon(line)
            continue
        if line.startswith("allowed_primitives: ["):
            primitive_text = line.split("[", 1)[1].split("]", 1)[0]
            primitives = [
                item.strip().strip('"')
                for item in primitive_text.split(",")
                if item.strip()
            ]
            current["allowed_primitives"] = primitives
            family_name = str(current["name"] or current["id"])
            for primitive in primitives:
                primitive_to_family.setdefault(primitive, family_name)

    if current is not None:
        families.append(current)

    return {
        "stage": stage,
        "allowed_split": allowed_split,
        "primitive_to_family": primitive_to_family,
        "families": families,
    }


def _read_comparator_contract(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {
        "stage": _extract_quoted_value(text, "stage"),
        "next_status": _extract_optional_quoted_value(text, "next_status"),
        "not_performance_claim": _extract_optional_bool_value(
            text, "not_performance_claim"
        ),
    }


def _read_comparator_audit_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_quoted_value(text: str, key: str) -> str:
    prefix = f"{key}: "
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith(prefix):
            return line.split('"', 2)[1]
    raise ValueError(f"Missing config key: {key}")


def _extract_optional_quoted_value(text: str, key: str) -> str:
    prefix = f"{key}: "
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith(prefix):
            return line.split('"', 2)[1]
    return ""


def _extract_optional_bool_value(text: str, key: str) -> bool:
    prefix = f"{key}: "
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith(prefix):
            return line.rsplit(" ", 1)[-1].lower() == "true"
    return False


def _quoted_after_colon(line: str) -> str:
    return line.split('"', 2)[1]


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

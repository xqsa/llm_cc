"""Stage 3.6 frozen candidate pool and train-only search protocol.

This module freezes quality-pass Stage 3.5 candidates as immutable inputs for
future train-only search. It does not call an LLM, execute ASTs, run evolution,
evaluate objectives, or make performance claims.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "3.6"
FROZEN_ROW_SCHEMA_VERSION = "loco.stage3_6_frozen_candidate.v1"
MANIFEST_SCHEMA_VERSION = "loco.stage3_6_frozen_pool_manifest.v1"
FAMILY_SCHEMA_VERSION = "loco.stage3_6_family_descriptors.v1"
PROTOCOL_SCHEMA_VERSION = "loco.stage3_6_train_only_search_protocol.v1"
REPORT_SCHEMA_VERSION = "loco.stage3_6_freeze_report.v1"


def freeze_stage3_6_candidate_pool(
    *,
    accepted_log_path: Path | str,
    quality_report_path: Path | str,
    diversity_report_path: Path | str,
    coverage_report_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    accepted_rows = _read_jsonl(Path(accepted_log_path))
    quality_report = _read_json(Path(quality_report_path))
    diversity_report = _read_json(Path(diversity_report_path))
    coverage_report = _read_json(Path(coverage_report_path))

    quality_pass_ids = {
        row["candidate_id"]
        for row in quality_report.get("quality_rows", [])
        if row.get("decision") == "pass"
    }
    if coverage_report.get("status") != "PASS":
        raise ValueError("Stage 3.6 requires Stage 3.5 coverage gate PASS.")

    feature_by_candidate_id = {
        item["candidate_id"]: item
        for item in diversity_report.get("candidate_features", [])
        if isinstance(item, Mapping)
    }
    frozen_rows = [
        _freeze_row(
            accepted_row=row,
            feature=feature_by_candidate_id[str(row["candidate_id"])],
        )
        for row in accepted_rows
        if row.get("candidate_id") in quality_pass_ids
    ]

    if len(frozen_rows) != len(quality_pass_ids):
        raise ValueError("Frozen pool does not match quality-pass candidate set.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "frozen_candidate_pool.jsonl", frozen_rows)

    descriptors = _build_family_descriptors(frozen_rows)
    manifest = _build_manifest(
        frozen_rows=frozen_rows,
        quality_report=quality_report,
        diversity_report=diversity_report,
        coverage_report=coverage_report,
        pool_fingerprint=_fingerprint_payload(frozen_rows),
    )
    protocol = _build_train_only_protocol(manifest)
    report = _build_freeze_report(manifest, descriptors, protocol)

    _write_json(output_path / "candidate_family_descriptors.json", descriptors)
    _write_json(output_path / "frozen_pool_manifest.json", manifest)
    _write_json(output_path / "train_only_search_protocol.json", protocol)
    _write_json(output_path / "freeze_report.json", report)
    return report


def _freeze_row(
    *, accepted_row: Mapping[str, Any], feature: Mapping[str, Any]
) -> dict[str, Any]:
    candidate_id = str(accepted_row["candidate_id"])
    payload = accepted_row["llm_candidate_payload"]
    row = {
        "schema_version": FROZEN_ROW_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "3.5",
        "candidate_id": candidate_id,
        "frozen": True,
        "split": "train",
        "target_scope": "shared_variables_only",
        "ast_fingerprint_sha256": str(accepted_row["ast_fingerprint_sha256"]),
        "candidate_payload_sha256": str(accepted_row["candidate_payload_sha256"]),
        "operator_family": str(feature["operator_family"]),
        "kind_sequence": str(feature["kind_sequence_signature"]),
        "node_count": int(feature["node_count"]),
        "target_variable_set": list(feature["target_variable_set"]),
        "llm_candidate_payload": payload,
        "no_llm_call": True,
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "no_scheduler_controller_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }
    return row | {"freeze_fingerprint_sha256": _fingerprint_payload(row)}


def _build_manifest(
    *,
    frozen_rows: Sequence[Mapping[str, Any]],
    quality_report: Mapping[str, Any],
    diversity_report: Mapping[str, Any],
    coverage_report: Mapping[str, Any],
    pool_fingerprint: str,
) -> dict[str, Any]:
    families = sorted({str(row["operator_family"]) for row in frozen_rows})
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "3.5",
        "source_quality_pass_count": int(quality_report["quality_pass_count"]),
        "source_quality_reject_count": int(quality_report["quality_reject_count"]),
        "coverage_gate_status": str(coverage_report["status"]),
        "coverage_gate_checks": dict(coverage_report["checks"]),
        "frozen_candidate_count": len(frozen_rows),
        "quality_pass_only": True,
        "unique_family_count": len(families),
        "families": families,
        "unique_kind_sequence_count": int(
            diversity_report["unique_kind_sequence_count"]
        ),
        "dominant_kind_sequence": diversity_report["dominant_kind_sequence"],
        "dominant_kind_sequence_count": int(
            diversity_report["dominant_kind_sequence_count"]
        ),
        "pool_fingerprint_sha256": pool_fingerprint,
        "no_llm_call": True,
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "no_scheduler_controller_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }


def _build_family_descriptors(
    frozen_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows_by_family: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in frozen_rows:
        rows_by_family[str(row["operator_family"])].append(row)
    descriptors = {
        family: {
            "candidate_count": len(rows),
            "candidate_ids": [str(row["candidate_id"]) for row in rows],
            "kind_sequences": sorted({str(row["kind_sequence"]) for row in rows}),
            "node_counts": dict(
                sorted(Counter(str(row["node_count"]) for row in rows).items())
            ),
        }
        for family, rows in sorted(rows_by_family.items())
    }
    return {
        "schema_version": FAMILY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "family_count": len(descriptors),
        "families": descriptors,
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }


def _build_train_only_protocol(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "READY_FOR_STAGE4_TRAIN_ONLY_SEARCH",
        "candidate_pool_frozen": True,
        "frozen_candidate_count": int(manifest["frozen_candidate_count"]),
        "allowed_split": "train",
        "train_usage": "evolution/search may use train-only evaluation in Stage 4",
        "validation_usage": "selection only after train search",
        "test_usage": "sealed final reporting only",
        "base_optimizer_policy": "BaseOpt must remain fixed across LOCO and baselines",
        "fe_accounting_policy": "all extra function evaluations must be counted",
        "oracle_detected_grouping_policy": (
            "oracle grouping and detected grouping must be reported separately"
        ),
        "no_llm_call_in_stage3_6": True,
        "no_evolution_executed_in_stage3_6": True,
        "no_objective_evaluation_in_stage3_6": True,
        "no_optimizer_generation": True,
        "no_scheduler_controller_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }


def _build_freeze_report(
    manifest: Mapping[str, Any],
    descriptors: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "3.5",
        "frozen_candidate_count": int(manifest["frozen_candidate_count"]),
        "quality_pass_only": bool(manifest["quality_pass_only"]),
        "family_count": int(descriptors["family_count"]),
        "train_only_search_protocol_prepared": (
            protocol["status"] == "READY_FOR_STAGE4_TRAIN_ONLY_SEARCH"
        ),
        "candidate_pool_frozen": True,
        "no_llm_call": True,
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "no_scheduler_controller_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }


def _fingerprint_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="\n")

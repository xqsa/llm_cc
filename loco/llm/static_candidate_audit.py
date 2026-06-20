"""Stage 3.4 static candidate quality and diversity audit.

The audit reads accepted Stage 3 candidate logs and computes static AST
features only. It does not execute operators, run evolution, evaluate
objectives, call an LLM, or make performance claims.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "3.4"
QUALITY_SCHEMA_VERSION = "loco.stage3_4_quality_filter_report.v1"
DIVERSITY_SCHEMA_VERSION = "loco.stage3_4_static_diversity_audit.v1"
SUMMARY_SCHEMA_VERSION = "loco.stage3_4_summary.v1"


def run_stage3_4_static_audit(
    *,
    accepted_log_path: Path | str,
    output_dir: Path | str,
    low_diversity_unique_kind_sequence_threshold: int = 3,
) -> dict[str, Any]:
    """Audit candidate quality and static diversity from accepted logs."""

    accepted_rows = _read_jsonl(Path(accepted_log_path))
    features = [_extract_candidate_features(row) for row in accepted_rows]
    quality_report = _build_quality_report(features)
    diversity_report = _build_diversity_report(
        features,
        low_diversity_unique_kind_sequence_threshold=(
            low_diversity_unique_kind_sequence_threshold
        ),
    )
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": (
            "PASS"
            if quality_report["status"] == "PASS"
            and diversity_report["status"] == "PASS"
            else "FAIL"
        ),
        "source_accepted_log": str(accepted_log_path),
        "candidate_count": len(features),
        "quality_pass_count": quality_report["quality_pass_count"],
        "quality_reject_count": quality_report["quality_reject_count"],
        "unique_kind_sequence_count": diversity_report["unique_kind_sequence_count"],
        "dominant_kind_sequence": diversity_report["dominant_kind_sequence"],
        "dominant_kind_sequence_count": diversity_report[
            "dominant_kind_sequence_count"
        ],
        "low_diversity_warning": diversity_report["low_diversity_warning"],
        "quality_filter_report_path": "quality_filter_report.json",
        "static_diversity_audit_path": "static_diversity_audit.json",
        "no_llm_call": True,
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "no_scheduler_controller_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "quality_filter_report.json", quality_report)
    _write_json(output_path / "static_diversity_audit.json", diversity_report)
    _write_json(output_path / "stage3_4_summary.json", summary)
    return summary


def _extract_candidate_features(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = row.get("llm_candidate_payload")
    if not isinstance(payload, Mapping):
        raise ValueError("accepted candidate row missing llm_candidate_payload")
    ast = payload.get("ast")
    if not isinstance(ast, Mapping):
        raise ValueError("accepted candidate payload missing ast")
    nodes = ast.get("nodes")
    if not isinstance(nodes, Sequence) or isinstance(nodes, (str, bytes)):
        raise ValueError("accepted candidate ast.nodes must be a list")

    kind_sequence: list[str] = []
    target_variables: list[int] = []
    input_keys: set[str] = set()
    for node in nodes:
        if not isinstance(node, Mapping):
            raise ValueError("accepted candidate ast node must be a mapping")
        kind = node.get("kind")
        if not isinstance(kind, str) or not kind:
            raise ValueError("accepted candidate ast node kind must be a string")
        kind_sequence.append(kind)
        target = node.get("target")
        if isinstance(target, Mapping) and isinstance(target.get("variable_id"), int):
            target_variables.append(int(target["variable_id"]))
        inputs = node.get("inputs", {})
        if isinstance(inputs, Mapping):
            input_keys.update(str(key) for key in inputs)

    node_count = len(kind_sequence)
    family = "+".join(kind_sequence)
    return {
        "candidate_id": str(row.get("candidate_id")),
        "ast_fingerprint_sha256": str(row.get("ast_fingerprint_sha256", "")),
        "kind_sequence": kind_sequence,
        "kind_sequence_signature": "->".join(kind_sequence),
        "operator_family": family,
        "node_count": node_count,
        "target_variables": target_variables,
        "target_variable_set": sorted(set(target_variables)),
        "input_keys": sorted(input_keys),
        "has_transform_after_consensus": _has_transform_after_consensus(kind_sequence),
        "is_single_node": node_count == 1,
    }


def _build_quality_report(features: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for item in features:
        issues = _quality_issues(item)
        rows.append(
            {
                "candidate_id": item["candidate_id"],
                "decision": "pass" if not issues else "reject",
                "quality_issues": issues,
                "node_count": item["node_count"],
                "kind_sequence": item["kind_sequence_signature"],
                "operator_family": item["operator_family"],
                "target_variable_set": item["target_variable_set"],
                "is_single_node": item["is_single_node"],
                "has_transform_after_consensus": item["has_transform_after_consensus"],
            }
        )
    issue_counts = Counter(issue for row in rows for issue in row["quality_issues"])
    pass_count = sum(1 for row in rows if row["decision"] == "pass")
    reject_count = len(rows) - pass_count
    return {
        "schema_version": QUALITY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "candidate_count": len(rows),
        "quality_pass_count": pass_count,
        "quality_reject_count": reject_count,
        "issue_counts": dict(sorted(issue_counts.items())),
        "quality_rows": rows,
        "no_llm_call": True,
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "no_scheduler_controller_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }


def _build_diversity_report(
    features: Sequence[Mapping[str, Any]],
    *,
    low_diversity_unique_kind_sequence_threshold: int,
) -> dict[str, Any]:
    kind_sequence_counts = Counter(
        str(item["kind_sequence_signature"]) for item in features
    )
    operator_family_counts = Counter(str(item["operator_family"]) for item in features)
    node_kind_counts = Counter(
        kind for item in features for kind in item["kind_sequence"]
    )
    target_variable_counts = Counter(
        str(variable) for item in features for variable in item["target_variables"]
    )
    node_count_counts = Counter(str(item["node_count"]) for item in features)
    dominant_kind_sequence, dominant_count = _dominant(kind_sequence_counts)
    unique_kind_sequence_count = len(kind_sequence_counts)
    low_diversity_warning = (
        unique_kind_sequence_count < low_diversity_unique_kind_sequence_threshold
    )
    return {
        "schema_version": DIVERSITY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "candidate_count": len(features),
        "unique_ast_fingerprint_count": len(
            {str(item["ast_fingerprint_sha256"]) for item in features}
        ),
        "unique_kind_sequence_count": unique_kind_sequence_count,
        "low_diversity_unique_kind_sequence_threshold": (
            low_diversity_unique_kind_sequence_threshold
        ),
        "low_diversity_warning": low_diversity_warning,
        "dominant_kind_sequence": dominant_kind_sequence,
        "dominant_kind_sequence_count": dominant_count,
        "kind_sequence_counts": dict(sorted(kind_sequence_counts.items())),
        "operator_family_counts": dict(sorted(operator_family_counts.items())),
        "node_kind_counts": dict(sorted(node_kind_counts.items())),
        "target_variable_counts": dict(sorted(target_variable_counts.items())),
        "node_count_counts": dict(sorted(node_count_counts.items())),
        "candidate_features": list(features),
        "interpretation": _diversity_interpretation(
            dominant_kind_sequence=dominant_kind_sequence,
            dominant_count=dominant_count,
            candidate_count=len(features),
            low_diversity_warning=low_diversity_warning,
        ),
        "no_llm_call": True,
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "no_scheduler_controller_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }


def _quality_issues(item: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if int(item["node_count"]) < 1:
        issues.append("empty_ast")
    if not item["target_variable_set"]:
        issues.append("missing_target_variable")
    if item["operator_family"] in {"weighted_consensus", "consensus"}:
        issues.append("single_consensus_only")
    return issues


def _has_transform_after_consensus(kind_sequence: Sequence[str]) -> bool:
    consensus_kinds = {"consensus", "weighted_consensus", "best_reward_select"}
    transform_kinds = {"clip", "projection", "dampening", "reweighting", "repair"}
    seen_consensus = False
    for kind in kind_sequence:
        if kind in consensus_kinds:
            seen_consensus = True
        elif seen_consensus and kind in transform_kinds:
            return True
    return False


def _dominant(counter: Counter[str]) -> tuple[str, int]:
    if not counter:
        return "", 0
    key, value = counter.most_common(1)[0]
    return key, int(value)


def _diversity_interpretation(
    *,
    dominant_kind_sequence: str,
    dominant_count: int,
    candidate_count: int,
    low_diversity_warning: bool,
) -> str:
    if candidate_count == 0:
        return "No accepted candidates were available for static audit."
    if low_diversity_warning:
        return (
            "Static structure diversity is low: the accepted corpus is dominated "
            f"by {dominant_kind_sequence} ({dominant_count}/{candidate_count})."
        )
    return (
        "Static structure diversity is not low under the configured kind-sequence "
        f"threshold; dominant sequence is {dominant_kind_sequence} "
        f"({dominant_count}/{candidate_count})."
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
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

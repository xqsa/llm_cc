"""Stage 7.6 reported-results comparator audit.

This stage audits published reported results under the Stage 7.5 same-setting
comparator contract. It only classifies paper comparators and writes a frozen
registry; it does not run objectives, search, or any optimizer logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


STAGE = "7.6"
REPORT_SCHEMA_VERSION = "loco.stage7_6_reported_results_comparator_audit.v1"
REGISTRY_SCHEMA_VERSION = "loco.stage7_6_reported_results_comparator_registry.v1"
ROUTE_SCHEMA_VERSION = "loco.stage7_6_next_route_decision.v1"


def run_stage7_6_reported_results_comparator_audit(
    *,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Write Stage 7.6 reported-results comparator audit artifacts."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    registry = _build_registry()
    report = _build_report(registry)
    route = _build_route()

    _write_json(output_path / "reported_results_comparator_registry.json", registry)
    _write_json(output_path / "reported_results_comparator_audit_report.json", report)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _build_registry() -> dict[str, Any]:
    entries = [
        {
            "source_name": "HCC",
            "paper_title": (
                "A Novel Two-Phase Cooperative Co-evolution Framework for "
                "Large-Scale Global Optimization with Complex Overlapping"
            ),
            "source_url": "https://arxiv.org/abs/2503.21797",
            "source_kind": "paper_reported_results",
            "benchmark_suite": "CEC2013_LSGO",
            "function_ids": ["F11", "F13"],
            "max_fe": 3_000_000,
            "run_count": 25,
            "statistic": "reported_table_statistic",
            "same_setting": True,
            "admissibility": "direct_comparator",
            "reason": "same_cec2013_lsgo_setting_with_explicit_reported_results",
            "reported_result_notes": (
                "Reported results are audit-only comparators under the Stage 7.5 same-setting contract."
            ),
        },
        {
            "source_name": "OEDG",
            "paper_title": (
                "An Enhanced Differential Grouping Method for Large-Scale "
                "Overlapping Problems"
            ),
            "source_url": "https://arxiv.org/abs/2404.10515",
            "source_kind": "paper_reported_results",
            "benchmark_suite": "custom_overlapping_benchmark",
            "function_ids": [],
            "max_fe": None,
            "run_count": None,
            "statistic": "reported_table_statistic",
            "same_setting": False,
            "admissibility": "background_only",
            "reason": "non_cec2013_custom_benchmark",
            "reported_result_notes": (
                "Table results are relevant background for overlapping grouping, but not same-setting CEC2013 comparators."
            ),
        },
    ]
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.5",
        "locked_rules_source": "Stage 7.5 same-setting comparator contract",
        "registry_type": "reported_results_comparator_registry",
        "entries": entries,
        "count_by_admissibility": {
            "direct_comparator": 1,
            "background_only": 1,
            "not_admissible": 0,
        },
        "forbidden_use": [
            "runtime_feedback",
            "prompt_generation",
            "candidate_generation",
            "train_search_scores",
            "validation_selection",
            "promotion_rule_design",
            "performance_claim",
            "sota_claim",
        ],
        "not_sota_claim": True,
        "no_objective_evaluation": True,
        "no_llm_call": True,
        "no_evolution_run": True,
        "no_ast_execution": True,
    }


def _build_report(registry: Mapping[str, Any]) -> dict[str, Any]:
    counts = registry["count_by_admissibility"]
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "7.5",
        "registry_size": len(registry["entries"]),
        "direct_comparator_count": counts["direct_comparator"],
        "background_only_count": counts["background_only"],
        "not_admissible_count": counts["not_admissible"],
        "direct_comparator_sources": [
            entry["source_name"]
            for entry in registry["entries"]
            if entry["admissibility"] == "direct_comparator"
        ],
        "background_only_sources": [
            entry["source_name"]
            for entry in registry["entries"]
            if entry["admissibility"] == "background_only"
        ],
        "source_contract": registry["locked_rules_source"],
        "next_status": "READY_FOR_STAGE8_0_TRAIN_ONLY_OPERATOR_IMPROVEMENT",
        "not_sota_claim": True,
        "reported_results_are_audit_only": True,
    }


def _build_route() -> dict[str, Any]:
    return {
        "schema_version": ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": "LOCK_REPORTED_RESULTS_COMPARATOR_AUDIT",
        "decision_reason": (
            "Reported results are now classified under the Stage 7.5 same-setting contract."
        ),
        "next_stage": "Stage 8.0",
        "allowed_next_work": "train_only_operator_improvement",
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_sota_claim": True,
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

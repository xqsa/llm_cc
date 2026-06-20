"""Stage 3.5 prompt-space hardening for coordination family coverage.

This module performs train-only multi-batch LLM candidate generation with a
family-coverage prompt, then reuses Stage 3.1 replay and Stage 3.4 static audit.
It does not execute candidates, run evolution, evaluate objectives, or make
performance claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from loco.llm.multibatch_candidate_generator import (
    _require_train_batch,
)
from loco.llm.api_candidate_generator import _parse_json_object
from loco.llm.candidate_batch import process_stage3_1_candidate_batch
from loco.llm.operator_prompt_contract import build_operator_prompt_contract
from loco.llm.provider_client import (
    call_chat_completion,
    load_llm_config_from_env,
)
from loco.llm.static_candidate_audit import run_stage3_4_static_audit


STAGE = "3.5"
RAW_BATCH_SCHEMA_VERSION = "loco.stage3_1_raw_llm_batch.v1"
SUMMARY_SCHEMA_VERSION = "loco.stage3_5_summary.v1"
COVERAGE_SCHEMA_VERSION = "loco.stage3_5_coverage_gate.v1"

REQUIRED_NODE_KINDS = (
    "projection",
    "dampening",
    "reweighting",
    "repair",
    "best_reward_select",
)
DEFAULT_THRESHOLDS = {
    "api_call_count": 3,
    "raw_candidate_count": 12,
    "accepted_count": 8,
    "quality_pass_count": 8,
    "unique_kind_sequence_count": 5,
    "operator_family_count": 5,
    "max_dominant_ratio": 0.5,
}


def run_stage3_5_prompt_space_hardening(
    *,
    env_path: Path | str,
    output_dir: Path | str,
    shared_variables: set[int] | frozenset[int],
    protocol_report_path: Path | str,
    batch_count: int = 3,
    candidates_per_batch: int = 4,
    temperature: float = 0.45,
) -> dict[str, Any]:
    if batch_count < DEFAULT_THRESHOLDS["api_call_count"]:
        raise ValueError("Stage 3.5 requires at least three API calls.")
    if batch_count * candidates_per_batch < DEFAULT_THRESHOLDS["raw_candidate_count"]:
        raise ValueError("Stage 3.5 requires at least 12 requested candidates.")

    output_path = Path(output_dir)
    raw_batch_path = output_path / "raw_batches"
    raw_batch_path.mkdir(parents=True, exist_ok=True)

    config = load_llm_config_from_env(Path(env_path))
    contract = build_operator_prompt_contract()
    merged_candidates: list[dict[str, Any]] = []
    raw_response_paths: list[str] = []
    raw_output_paths: list[str] = []
    provenance_rows: list[dict[str, Any]] = []

    for batch_index in range(batch_count):
        result = call_chat_completion(
            config,
            messages=[
                {
                    "role": "system",
                    "content": "\n".join(
                        [
                            *contract.system_rules,
                            *contract.output_rules,
                            "Return JSON only.",
                            "Every returned candidate must use split=train.",
                            "The output must cover distinct coordination families.",
                        ]
                    ),
                },
                {
                    "role": "user",
                    "content": _stage3_5_user_prompt(
                        batch_index=batch_index,
                        candidate_count=candidates_per_batch,
                    ),
                },
            ],
            temperature=temperature,
        )
        raw_response_file = raw_batch_path / f"raw_response_{batch_index:03d}.json"
        raw_output_file = raw_batch_path / f"raw_llm_output_{batch_index:03d}.json"
        raw_response_file.write_text(
            json.dumps(result.to_artifact_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        raw_batch = _parse_json_object(result.content)
        _require_train_batch(raw_batch, batch_index)
        raw_output_file.write_text(
            json.dumps(raw_batch, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        merged_candidates.extend(
            dict(candidate) for candidate in raw_batch["candidates"]
        )
        raw_response_paths.append(_display_path(raw_response_file, output_path))
        raw_output_paths.append(_display_path(raw_output_file, output_path))
        provenance_rows.append(
            {
                "batch_index": batch_index,
                "base_url_host": result.provenance.get("base_url_host"),
                "model": result.provenance.get("model"),
                "wire_api": result.provenance.get("wire_api"),
                "reasoning_effort": result.provenance.get("reasoning_effort"),
                "raw_response_path": _display_path(raw_response_file, output_path),
                "raw_output_path": _display_path(raw_output_file, output_path),
            }
        )

    merged_batch = {
        "schema_version": RAW_BATCH_SCHEMA_VERSION,
        "stage": "3.1",
        "split": "train",
        "prompt_contract_version": contract.schema_version,
        "source": {
            "provider": (
                "deepseek"
                if provenance_rows[0].get("base_url_host") == "api.deepseek.com"
                else "custom"
            ),
            "model": provenance_rows[0].get("model"),
            "captured_by": "Stage 3.5 prompt-space hardening",
            "batch_count": batch_count,
        },
        "candidates": merged_candidates,
    }
    merged_path = output_path / "merged_raw_llm_output.json"
    merged_path.write_text(
        json.dumps(merged_batch, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    batch_result = process_stage3_1_candidate_batch(
        raw_output_path=merged_path,
        output_dir=output_path,
        shared_variables=shared_variables,
        protocol_report_path=protocol_report_path,
    )
    static_summary = run_stage3_4_static_audit(
        accepted_log_path=output_path / "accepted_candidates.jsonl",
        output_dir=output_path,
        low_diversity_unique_kind_sequence_threshold=(
            DEFAULT_THRESHOLDS["unique_kind_sequence_count"]
        ),
    )
    diversity_report = _read_json(output_path / "static_diversity_audit.json")
    coverage_report = _build_coverage_report(
        api_call_count=batch_count,
        raw_candidate_count=len(merged_candidates),
        accepted_count=int(batch_result["accepted_count"]),
        quality_pass_count=int(static_summary["quality_pass_count"]),
        diversity_report=diversity_report,
    )
    _write_json(output_path / "coverage_gate_report.json", coverage_report)
    summary = _build_summary(
        batch_result=batch_result,
        static_summary=static_summary,
        coverage_report=coverage_report,
        raw_candidate_count=len(merged_candidates),
        raw_response_paths=raw_response_paths,
        raw_output_paths=raw_output_paths,
        provenance_rows=provenance_rows,
        provider=merged_batch["source"]["provider"],
    )
    _write_json(output_path / "stage3_5_summary.json", summary)
    _write_json(output_path / "multi_batch_report.json", summary)
    return summary


def _stage3_5_user_prompt(*, batch_index: int, candidate_count: int) -> str:
    return (
        "Generate a train-only batch of "
        f"{candidate_count} LOCO-LSGO coordination operator candidates for "
        f"Stage 3.5 batch {batch_index}. Return JSON only, with no markdown "
        "and no explanation. The output MUST match the Stage 3.1 raw batch "
        "schema shape and field names. Use only shared variable ids 5 and 6. "
        "Do not add fields. Do not use validation or test feedback. Do not "
        "generate optimizer, scheduler, controller, optimizer selection, BaseOpt "
        "modification, or arbitrary executable code.\n\n"
        "Allowed DSL node kinds are exactly: consensus, weighted_consensus, "
        "best_reward_select, projection, dampening, reweighting, clip, repair. "
        "Allowed node input keys are exactly: source, sources, temperature, "
        "damping_strength, weights, lower, upper, projection, mode, reward_key. "
        "Do not use alpha, method, strategy, lower_bound, upper_bound, selection, "
        "strength, repair_strategy, reweighting, or any other input key. "
        "If an input source is used, it must equal the id of an earlier node in "
        "the same AST. Never use source='raw'. "
        "Across this batch, avoid repeating the same weighted_consensus->clip "
        "template. Prefer distinct kind sequences. Use these family targets:\n"
        "- projection / feasibility coordination\n"
        "- dampening / trust-region-like coordination\n"
        "- adaptive reweighting before consensus or repair\n"
        "- repair / conflict-safe fallback\n"
        "- best_reward_select reward-aware proposal selection\n"
        "- combinations such as projection->dampening, reweighting->repair, "
        "best_reward_select->dampening->clip\n\n"
        "Return this envelope shape. The example is valid and uses only legal "
        "fields and legal input keys:\n"
        "{\n"
        '  "schema_version": "loco.stage3_1_raw_llm_batch.v1",\n'
        '  "stage": "3.1",\n'
        '  "split": "train",\n'
        '  "prompt_contract_version": "loco.operator_prompt_contract.v1",\n'
        '  "source": {\n'
        '    "provider": "deepseek",\n'
        '    "model": "deepseek-v4-pro",\n'
        f'    "captured_by": "Stage 3.5 batch {batch_index}"\n'
        "  },\n"
        '  "candidates": [\n'
        "    {\n"
        '      "schema_version": "loco.llm_candidate.v1",\n'
        f'      "candidate_id": "stage3_5_batch_{batch_index}_projection_dampening",\n'
        '      "generator": {\n'
        '        "type": "llm",\n'
        '        "provider": "deepseek",\n'
        '        "model": "deepseek-v4-pro",\n'
        '        "prompt_contract_version": "loco.operator_prompt_contract.v1"\n'
        "      },\n"
        '      "ast": {\n'
        '        "schema_version": "loco.dsl.v1",\n'
        f'        "operator_id": "stage3_5_batch_{batch_index}_projection_dampening",\n'
        '        "nodes": [\n'
        '          {"id": "project", "kind": "projection", '
        '"target": {"variable_id": 5}, '
        '"inputs": {"projection": "box"}},\n'
        '          {"id": "dampen", "kind": "dampening", '
        '"target": {"variable_id": 5}, '
        '"inputs": {"source": "project", "damping_strength": 0.3}}\n'
        "        ],\n"
        '        "output": {"source": "dampen"}\n'
        "      },\n"
        '      "declared_scope": {\n'
        '        "target": "shared_variables_only",\n'
        '        "not_optimizer": true,\n'
        '        "not_controller": true,\n'
        '        "not_scheduler": true,\n'
        '        "not_optimizer_selection": true,\n'
        '        "not_benchmark_specific": true,\n'
        '        "no_test_feedback": true\n'
        "      }\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "\n"
        "For this batch, include four different valid candidates selected from "
        "these legal templates, without copying one template four times:\n"
        "1. projection -> dampening using inputs projection and damping_strength.\n"
        "2. reweighting -> repair using inputs weights and mode.\n"
        "3. best_reward_select -> dampening -> clip using reward_key, "
        "damping_strength, lower, upper.\n"
        "4. weighted_consensus -> projection using temperature and projection.\n"
        "5. reweighting -> weighted_consensus -> clip using weights, source, "
        "temperature, lower, upper.\n"
        "6. consensus -> repair -> clip using mode, lower, upper.\n"
    )


def _build_coverage_report(
    *,
    api_call_count: int,
    raw_candidate_count: int,
    accepted_count: int,
    quality_pass_count: int,
    diversity_report: Mapping[str, Any],
) -> dict[str, Any]:
    node_kind_counts = diversity_report.get("node_kind_counts", {})
    operator_family_counts = diversity_report.get("operator_family_counts", {})
    dominant_count = int(diversity_report.get("dominant_kind_sequence_count", 0))
    dominant_ratio = dominant_count / quality_pass_count if quality_pass_count else 1.0
    required_present = {
        kind: int(node_kind_counts.get(kind, 0)) > 0 for kind in REQUIRED_NODE_KINDS
    }
    checks = {
        "api_call_count": api_call_count >= DEFAULT_THRESHOLDS["api_call_count"],
        "raw_candidate_count": raw_candidate_count
        >= DEFAULT_THRESHOLDS["raw_candidate_count"],
        "accepted_count": accepted_count >= DEFAULT_THRESHOLDS["accepted_count"],
        "quality_pass_count": quality_pass_count
        >= DEFAULT_THRESHOLDS["quality_pass_count"],
        "unique_kind_sequence_count": int(
            diversity_report.get("unique_kind_sequence_count", 0)
        )
        >= DEFAULT_THRESHOLDS["unique_kind_sequence_count"],
        "operator_family_count": len(operator_family_counts)
        >= DEFAULT_THRESHOLDS["operator_family_count"],
        "dominant_ratio": dominant_ratio <= DEFAULT_THRESHOLDS["max_dominant_ratio"],
        **{
            f"must_include_{kind}": present
            for kind, present in required_present.items()
        },
    }
    return {
        "schema_version": COVERAGE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "thresholds": dict(DEFAULT_THRESHOLDS),
        "required_node_kinds_present": required_present,
        "api_call_count": api_call_count,
        "raw_candidate_count": raw_candidate_count,
        "accepted_count": accepted_count,
        "quality_pass_count": quality_pass_count,
        "unique_kind_sequence_count": int(
            diversity_report.get("unique_kind_sequence_count", 0)
        ),
        "operator_family_count": len(operator_family_counts),
        "dominant_kind_sequence": diversity_report.get("dominant_kind_sequence"),
        "dominant_kind_sequence_count": dominant_count,
        "dominant_ratio": dominant_ratio,
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "no_scheduler_controller_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }


def _build_summary(
    *,
    batch_result: Mapping[str, Any],
    static_summary: Mapping[str, Any],
    coverage_report: Mapping[str, Any],
    raw_candidate_count: int,
    raw_response_paths: list[str],
    raw_output_paths: list[str],
    provenance_rows: list[dict[str, Any]],
    provider: object,
) -> dict[str, Any]:
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": coverage_report["status"],
        "provider": provider,
        "api_called": True,
        "api_call_count": coverage_report["api_call_count"],
        "split": "train",
        "raw_candidate_count": raw_candidate_count,
        "accepted_count": batch_result["accepted_count"],
        "rejected_count": batch_result["rejected_count"],
        "quality_pass_count": static_summary["quality_pass_count"],
        "quality_reject_count": static_summary["quality_reject_count"],
        "unique_kind_sequence_count": coverage_report["unique_kind_sequence_count"],
        "operator_family_count": coverage_report["operator_family_count"],
        "dominant_kind_sequence": coverage_report["dominant_kind_sequence"],
        "dominant_kind_sequence_count": coverage_report["dominant_kind_sequence_count"],
        "dominant_ratio": coverage_report["dominant_ratio"],
        "must_include_projection": coverage_report["required_node_kinds_present"][
            "projection"
        ],
        "must_include_dampening": coverage_report["required_node_kinds_present"][
            "dampening"
        ],
        "must_include_reweighting": coverage_report["required_node_kinds_present"][
            "reweighting"
        ],
        "must_include_repair": coverage_report["required_node_kinds_present"]["repair"],
        "must_include_best_reward_select": coverage_report[
            "required_node_kinds_present"
        ]["best_reward_select"],
        "raw_response_paths": raw_response_paths,
        "raw_output_paths": raw_output_paths,
        "coverage_gate_report_path": "coverage_gate_report.json",
        "quality_filter_report_path": "quality_filter_report.json",
        "static_diversity_audit_path": "static_diversity_audit.json",
        "provenance": provenance_rows,
        "secret_redacted": True,
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "no_scheduler_controller_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _display_path(path: Path, output_path: Path) -> str:
    try:
        return path.resolve().relative_to(output_path.resolve()).as_posix()
    except ValueError:
        return path.as_posix()

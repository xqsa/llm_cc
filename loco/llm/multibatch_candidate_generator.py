"""Stage 3.3 train-only multi-batch LLM candidate generation.

This module calls a configured chat API multiple times, stores sanitized
per-batch artifacts, merges train-only candidate batches, and reuses the Stage
3.1 audit chain. It does not run evolution, execute ASTs, evaluate objectives,
or claim performance.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from loco.llm.api_candidate_generator import _parse_json_object
from loco.llm.candidate_batch import process_stage3_1_candidate_batch
from loco.llm.operator_prompt_contract import build_operator_prompt_contract
from loco.llm.provider_client import (
    call_chat_completion,
    load_llm_config_from_env,
)


STAGE = "3.3"
RAW_BATCH_SCHEMA_VERSION = "loco.stage3_1_raw_llm_batch.v1"
MULTI_BATCH_REPORT_SCHEMA_VERSION = "loco.stage3_3_multi_batch_report.v1"
DEDUP_REPORT_SCHEMA_VERSION = "loco.stage3_3_dedup_report.v1"
REJECTION_TAXONOMY_SCHEMA_VERSION = "loco.stage3_3_rejection_taxonomy.v1"


def run_stage3_3_multi_batch(
    *,
    env_path: Path | str,
    output_dir: Path | str,
    shared_variables: set[int] | frozenset[int],
    protocol_report_path: Path | str,
    batch_count: int = 3,
    candidates_per_batch: int = 3,
    temperature: float = 0.35,
) -> dict[str, Any]:
    """Generate multiple train-only candidate batches and harden the corpus."""

    if batch_count < 2:
        raise ValueError("Stage 3.3 requires at least two batches.")
    if candidates_per_batch < 1:
        raise ValueError("candidates_per_batch must be positive.")

    output_path = Path(output_dir)
    raw_batch_path = output_path / "raw_batches"
    raw_batch_path.mkdir(parents=True, exist_ok=True)

    config = load_llm_config_from_env(Path(env_path))
    contract = build_operator_prompt_contract()
    merged_candidates: list[dict[str, Any]] = []
    raw_output_paths: list[str] = []
    raw_response_paths: list[str] = []
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
                        ]
                    ),
                },
                {
                    "role": "user",
                    "content": _stage3_3_user_prompt(
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
            "captured_by": "Stage 3.3 train-only multi-batch LLM generation",
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
    accepted_rows = _read_jsonl(output_path / "accepted_candidates.jsonl")
    rejected_rows = _read_jsonl(output_path / "rejected_candidates.jsonl")
    dedup_report = _write_dedup_report(
        accepted_rows=accepted_rows,
        output_path=output_path / "dedup_report.json",
    )
    taxonomy = _write_rejection_taxonomy(
        rejected_rows=rejected_rows,
        output_path=output_path / "rejection_taxonomy.json",
    )
    status = (
        "PASS"
        if batch_result["status"] == "PASS"
        and dedup_report["status"] == "PASS"
        and taxonomy["status"] == "PASS"
        else "FAIL"
    )
    report = {
        "schema_version": MULTI_BATCH_REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": status,
        "api_called": True,
        "api_call_count": batch_count,
        "provider": merged_batch["source"]["provider"],
        "base_url_host": provenance_rows[0].get("base_url_host"),
        "model": provenance_rows[0].get("model"),
        "wire_api": provenance_rows[0].get("wire_api"),
        "reasoning_effort": provenance_rows[0].get("reasoning_effort"),
        "split": "train",
        "raw_candidate_count": len(merged_candidates),
        "accepted_count": batch_result["accepted_count"],
        "unique_accepted_count": dedup_report["unique_accepted_count"],
        "duplicate_accepted_count": dedup_report["duplicate_accepted_count"],
        "rejected_count": batch_result["rejected_count"],
        "rejection_categories": taxonomy["categories"],
        "raw_response_paths": raw_response_paths,
        "raw_output_paths": raw_output_paths,
        "merged_raw_output_path": "merged_raw_llm_output.json",
        "accepted_log_path": "accepted_candidates.jsonl",
        "rejected_log_path": "rejected_candidates.jsonl",
        "dedup_report_path": "dedup_report.json",
        "rejection_taxonomy_path": "rejection_taxonomy.json",
        "provenance": provenance_rows,
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "no_scheduler_controller_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
        "secret_redacted": True,
    }
    (output_path / "multi_batch_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def _stage3_3_user_prompt(*, batch_index: int, candidate_count: int) -> str:
    return (
        "Generate a train-only batch of "
        f"{candidate_count} LOCO-LSGO coordination operator candidates for "
        f"Stage 3.3 batch {batch_index}. Return JSON only, with no markdown "
        "and no explanation. The output MUST match the Stage 3.1 raw batch "
        "schema shape and field names. Use only shared variable ids 5 and 6. "
        "Do not add fields. Do not use validation or test feedback. Do not "
        "generate optimizer, scheduler, controller, optimizer selection, or "
        "arbitrary executable code.\n\n"
        "{\n"
        '  "schema_version": "loco.stage3_1_raw_llm_batch.v1",\n'
        '  "stage": "3.1",\n'
        '  "split": "train",\n'
        '  "prompt_contract_version": "loco.operator_prompt_contract.v1",\n'
        '  "source": {\n'
        '    "provider": "deepseek",\n'
        '    "model": "deepseek-v4-pro",\n'
        f'    "captured_by": "Stage 3.3 batch {batch_index}"\n'
        "  },\n"
        '  "candidates": [\n'
        "    {\n"
        '      "schema_version": "loco.llm_candidate.v1",\n'
        f'      "candidate_id": "stage3_3_batch_{batch_index}_weighted_clip_shared_5",\n'
        '      "generator": {\n'
        '        "type": "llm",\n'
        '        "provider": "deepseek",\n'
        '        "model": "deepseek-v4-pro",\n'
        '        "prompt_contract_version": "loco.operator_prompt_contract.v1"\n'
        "      },\n"
        '      "ast": {\n'
        '        "schema_version": "loco.dsl.v1",\n'
        f'        "operator_id": "stage3_3_batch_{batch_index}_weighted_clip_shared_5",\n'
        '        "nodes": [\n'
        "          {\n"
        '            "id": "weighted",\n'
        '            "kind": "weighted_consensus",\n'
        '            "target": {"variable_id": 5},\n'
        '            "inputs": {"temperature": 1.0}\n'
        "          },\n"
        "          {\n"
        '            "id": "bounded",\n'
        '            "kind": "clip",\n'
        '            "target": {"variable_id": 5},\n'
        '            "inputs": {"source": "weighted", "lower": -1.0, "upper": 1.0}\n'
        "          }\n"
        "        ],\n"
        '        "output": {"source": "bounded"}\n'
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
        "}\n\n"
        "Allowed AST node kinds include weighted_consensus and clip. The only "
        "target variable_id values allowed are 5 and 6."
    )


def _require_train_batch(payload: Mapping[str, Any], batch_index: int) -> None:
    if payload.get("schema_version") != RAW_BATCH_SCHEMA_VERSION:
        raise ValueError(f"batch {batch_index} has unsupported schema_version")
    if payload.get("stage") != "3.1":
        raise ValueError(f"batch {batch_index} stage must be 3.1")
    if payload.get("split") != "train":
        raise ValueError(f"batch {batch_index} split must be train")
    candidates = payload.get("candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise ValueError(f"batch {batch_index} candidates must be a list")
    if not candidates:
        raise ValueError(f"batch {batch_index} must contain candidates")
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError(f"batch {batch_index} candidate must be a mapping")


def _write_dedup_report(
    *, accepted_rows: Sequence[Mapping[str, Any]], output_path: Path
) -> dict[str, Any]:
    by_fingerprint: dict[str, list[str]] = defaultdict(list)
    for row in accepted_rows:
        fingerprint = str(row.get("ast_fingerprint_sha256"))
        by_fingerprint[fingerprint].append(str(row.get("candidate_id")))

    duplicate_groups = [
        {"ast_fingerprint_sha256": fingerprint, "candidate_ids": candidate_ids}
        for fingerprint, candidate_ids in sorted(by_fingerprint.items())
        if len(candidate_ids) > 1
    ]
    duplicate_count = sum(len(group["candidate_ids"]) - 1 for group in duplicate_groups)
    report = {
        "schema_version": DEDUP_REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "split": "train",
        "accepted_count": len(accepted_rows),
        "unique_accepted_count": len(by_fingerprint),
        "duplicate_accepted_count": duplicate_count,
        "duplicate_groups": duplicate_groups,
        "dedup_key": "ast_fingerprint_sha256",
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def _write_rejection_taxonomy(
    *, rejected_rows: Sequence[Mapping[str, Any]], output_path: Path
) -> dict[str, Any]:
    counts = Counter(str(row.get("reject_reason_category")) for row in rejected_rows)
    examples: dict[str, list[str]] = defaultdict(list)
    for row in rejected_rows:
        category = str(row.get("reject_reason_category"))
        if len(examples[category]) < 3:
            examples[category].append(str(row.get("candidate_id")))
    report = {
        "schema_version": REJECTION_TAXONOMY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "split": "train",
        "rejected_count": len(rejected_rows),
        "categories": dict(sorted(counts.items())),
        "examples": {key: examples[key] for key in sorted(examples)},
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _display_path(path: Path, output_path: Path) -> str:
    try:
        return path.resolve().relative_to(output_path.resolve()).as_posix()
    except ValueError:
        return path.as_posix()

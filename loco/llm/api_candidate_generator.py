"""Stage 3.2 real LLM API smoke runner.

The runner calls a configured chat API once, stores sanitized response
provenance, parses the returned train-only candidate batch, and reuses Stage
3.1 candidate replay. It does not run evolution, execute ASTs, evaluate
objectives, or use test feedback.
"""

from __future__ import annotations

import json
from pathlib import Path

from loco.llm.candidate_batch import process_stage3_1_candidate_batch
from loco.llm.operator_prompt_contract import build_operator_prompt_contract
from loco.llm.provider_client import (
    call_chat_completion,
    load_llm_config_from_env,
)


def run_stage3_2_api_smoke(
    *,
    env_path: Path | str,
    output_dir: Path | str,
    shared_variables: set[int] | frozenset[int],
    protocol_report_path: Path | str,
    candidate_count: int = 1,
    temperature: float = 0.2,
) -> dict[str, object]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    config = load_llm_config_from_env(Path(env_path))
    contract = build_operator_prompt_contract()
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
                    ]
                ),
            },
            {
                "role": "user",
                "content": _stage3_2_user_prompt(candidate_count),
            },
        ],
        temperature=temperature,
    )

    raw_response_path = output_path / "raw_response.json"
    raw_output_path = output_path / "raw_llm_output.json"
    raw_response_path.write_text(
        json.dumps(result.to_artifact_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    raw_batch = _parse_json_object(result.content)
    raw_output_path.write_text(
        json.dumps(raw_batch, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    batch_result = process_stage3_1_candidate_batch(
        raw_output_path=raw_output_path,
        output_dir=output_path,
        shared_variables=shared_variables,
        protocol_report_path=protocol_report_path,
    )
    smoke_report = {
        "schema_version": "loco.stage3_2_api_smoke_report.v1",
        "stage": "3.2",
        "status": batch_result["status"],
        "api_called": True,
        "provider": (
            "deepseek"
            if result.provenance.get("base_url_host") == "api.deepseek.com"
            else "custom"
        ),
        "base_url_host": result.provenance.get("base_url_host"),
        "model": result.provenance.get("model"),
        "wire_api": result.provenance.get("wire_api"),
        "reasoning_effort": result.provenance.get("reasoning_effort"),
        "split": batch_result["split"],
        "accepted_count": batch_result["accepted_count"],
        "rejected_count": batch_result["rejected_count"],
        "raw_response_path": "raw_response.json",
        "raw_output_path": "raw_llm_output.json",
        "no_evolution_run": True,
        "no_objective_evaluation": True,
        "no_optimizer_generation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
        "secret_redacted": True,
    }
    (output_path / "smoke_report.json").write_text(
        json.dumps(smoke_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return smoke_report


def _stage3_2_user_prompt(candidate_count: int) -> str:
    return (
        "Generate a train-only small batch of "
        f"{candidate_count} LOCO-LSGO coordination operator candidate. "
        "Return JSON only, with no markdown and no explanation. The output "
        "MUST match this exact schema shape and field names. Use shared "
        "variable id 5 only. Do not add fields.\n\n"
        "{\n"
        '  "schema_version": "loco.stage3_1_raw_llm_batch.v1",\n'
        '  "stage": "3.1",\n'
        '  "split": "train",\n'
        '  "prompt_contract_version": "loco.operator_prompt_contract.v1",\n'
        '  "source": {\n'
        '    "provider": "deepseek",\n'
        '    "model": "deepseek-v4-pro",\n'
        '    "captured_by": "Stage 3.2 API smoke"\n'
        "  },\n"
        '  "candidates": [\n'
        "    {\n"
        '      "schema_version": "loco.llm_candidate.v1",\n'
        '      "candidate_id": "stage3_2_deepseek_weighted_clip_shared_5",\n'
        '      "generator": {\n'
        '        "type": "llm",\n'
        '        "provider": "deepseek",\n'
        '        "model": "deepseek-v4-pro",\n'
        '        "prompt_contract_version": "loco.operator_prompt_contract.v1"\n'
        "      },\n"
        '      "ast": {\n'
        '        "schema_version": "loco.dsl.v1",\n'
        '        "operator_id": "stage3_2_deepseek_weighted_clip_shared_5",\n'
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
        "The AST must be a coordination operator AST, not an optimizer. "
        "Allowed node kinds include weighted_consensus and clip. The only "
        "target variable_id allowed is 5."
    )


def _parse_json_object(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError("LLM candidate output must be a JSON object.")
    return payload

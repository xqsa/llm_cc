import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_CONFIG = ROOT / "configs" / "stage3_search_protocol.yaml"
PROTOCOL_DOC = ROOT / "docs" / "stage3" / "stage3_0_protocol_lock.md"
SEARCH_SPACE_DOC = ROOT / "docs" / "stage3" / "operator_ast_search_space.md"
SELECTION_DOC = ROOT / "docs" / "stage3" / "evolution_selection_protocol.md"
FIREWALL_DOC = ROOT / "docs" / "stage3" / "test_feedback_firewall.md"
SELF_CHECK = ROOT / "docs" / "stage3" / "stage3_0_self_check_report.md"
READINESS_DECISION = (
    ROOT / "artifacts" / "readiness" / "stage2_10_readiness_decision.json"
)
PROTOCOL_REPORT = (
    ROOT / "artifacts" / "readiness" / "stage3_0_protocol_lock_report.json"
)


def _valid_llm_payload() -> dict:
    return {
        "schema_version": "loco.llm_candidate.v1",
        "candidate_id": "stage3_0_valid_weighted_clip_shared_5",
        "generator": {
            "type": "llm",
            "provider": "protocol_stub",
            "model": "not_called",
            "prompt_contract_version": "loco.operator_prompt_contract.v1",
        },
        "ast": {
            "schema_version": "loco.dsl.v1",
            "operator_id": "stage3_0_valid_weighted_clip_shared_5",
            "nodes": [
                {
                    "id": "weighted",
                    "kind": "weighted_consensus",
                    "target": {"variable_id": 5},
                    "inputs": {"temperature": 1.0},
                },
                {
                    "id": "bounded",
                    "kind": "clip",
                    "target": {"variable_id": 5},
                    "inputs": {"source": "weighted", "lower": -1.0, "upper": 1.0},
                },
            ],
            "output": {"source": "bounded"},
        },
        "declared_scope": {
            "target": "shared_variables_only",
            "not_optimizer": True,
            "not_controller": True,
            "not_scheduler": True,
            "not_optimizer_selection": True,
            "not_benchmark_specific": True,
            "no_test_feedback": True,
        },
    }


def test_stage3_0_candidate_schema_accepts_only_wrapped_typed_ast() -> None:
    from loco.llm.ast_candidate_schema import (
        load_llm_candidate_payload,
        validate_llm_candidate_payload,
    )

    candidate = load_llm_candidate_payload(_valid_llm_payload())
    report = validate_llm_candidate_payload(candidate, shared_variables={5})

    assert report.schema_version == "loco.llm_candidate_validation.v1"
    assert report.candidate_id == "stage3_0_valid_weighted_clip_shared_5"
    assert report.ast_operator_id == "stage3_0_valid_weighted_clip_shared_5"
    assert report.target_scope == "shared_variables_only"
    assert report.no_test_feedback is True
    assert len(report.ast_fingerprint_sha256) == 64


@pytest.mark.parametrize(
    "scope_key",
    [
        "not_optimizer",
        "not_controller",
        "not_scheduler",
        "not_optimizer_selection",
        "not_benchmark_specific",
        "no_test_feedback",
    ],
)
def test_stage3_0_candidate_schema_requires_negative_scope_flags(
    scope_key: str,
) -> None:
    from loco.llm.ast_candidate_schema import (
        load_llm_candidate_payload,
        validate_llm_candidate_payload,
    )

    payload = _valid_llm_payload()
    payload["declared_scope"][scope_key] = False

    with pytest.raises(ValueError, match=scope_key):
        validate_llm_candidate_payload(
            load_llm_candidate_payload(payload),
            shared_variables={5},
        )


def test_stage3_0_candidate_schema_reuses_stage2_ast_boundary() -> None:
    from loco.llm.ast_candidate_schema import (
        load_llm_candidate_payload,
        validate_llm_candidate_payload,
    )

    payload = _valid_llm_payload()
    payload["ast"]["nodes"][0]["target"]["variable_id"] = 9
    payload["ast"]["nodes"][1]["target"]["variable_id"] = 9

    with pytest.raises(ValueError, match="non-shared variables"):
        validate_llm_candidate_payload(
            load_llm_candidate_payload(payload),
            shared_variables={5},
        )


def test_stage3_0_prompt_contract_contains_required_firewall_text() -> None:
    from loco.llm.operator_prompt_contract import build_operator_prompt_contract

    contract = build_operator_prompt_contract()
    text = "\n".join(contract.system_rules + contract.output_rules)

    assert contract.schema_version == "loco.operator_prompt_contract.v1"
    assert "typed coordination operator AST" in text
    assert "shared variables" in text
    assert "do not generate optimizer" in text
    assert "do not generate scheduler" in text
    assert "do not generate controller" in text
    assert "do not select optimizer" in text
    assert "no test feedback" in text
    assert "no benchmark-specific metadata" in text
    assert "no arbitrary executable code" in text


def test_stage3_0_protocol_lock_reads_stage2_10_readiness_and_blocks_if_not_ready(
    tmp_path,
) -> None:
    from loco.llm.ast_candidate_schema import evaluate_stage3_protocol_lock

    ready = evaluate_stage3_protocol_lock(
        readiness_decision_path=READINESS_DECISION,
        protocol_config_path=PROTOCOL_CONFIG,
        report_path=tmp_path / "ready.json",
    )
    assert ready["status"] == "PASS"
    assert ready["stage3_allowed"] is True
    assert ready["no_llm_call"] is True
    assert ready["no_evolution_run"] is True
    assert ready["no_objective_evaluation"] is True
    assert ready["not_performance_claim"] is True

    blocked_decision = tmp_path / "blocked_readiness.json"
    payload = json.loads(READINESS_DECISION.read_text(encoding="utf-8"))
    payload["decision"] = "BLOCK_STAGE3"
    payload["stage3_allowed"] = False
    blocked_decision.write_text(json.dumps(payload), encoding="utf-8")

    blocked = evaluate_stage3_protocol_lock(
        readiness_decision_path=blocked_decision,
        protocol_config_path=PROTOCOL_CONFIG,
        report_path=tmp_path / "blocked.json",
    )
    assert blocked["status"] == "BLOCKED"
    assert blocked["stage3_allowed"] is False


def test_stage3_0_docs_and_config_lock_protocol_not_execution() -> None:
    required = [
        PROTOCOL_CONFIG,
        PROTOCOL_DOC,
        SEARCH_SPACE_DOC,
        SELECTION_DOC,
        FIREWALL_DOC,
        SELF_CHECK,
        PROTOCOL_REPORT,
    ]
    for path in required:
        assert path.is_file(), path

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required)
    assert "Stage 3.0" in combined
    assert "typed coordination operator AST" in combined
    assert "shared variables" in combined
    assert "no LLM call" in combined
    assert "no evolution run" in combined
    assert "no objective evaluation" in combined
    assert "no optimizer generation" in combined
    assert "no scheduler/controller generation" in combined
    assert "no test feedback" in combined
    assert "train" in combined
    assert "validation" in combined
    assert "test" in combined
    assert "READY_FOR_STAGE3_BOUNDARY_ONLY" in combined
    assert "not a performance claim" in combined

    report = json.loads(PROTOCOL_REPORT.read_text(encoding="utf-8"))
    assert report["schema_version"] == "loco.stage3_protocol_lock.v1"
    assert report["stage"] == "3.0"
    assert report["status"] == "PASS"
    assert report["stage3_allowed"] is True
    assert report["no_llm_call"] is True
    assert report["no_evolution_run"] is True
    assert report["no_objective_evaluation"] is True
    assert report["not_performance_claim"] is True


def test_stage3_0_import_does_not_load_llm_or_evolution_clients() -> None:
    forbidden_loaded_before = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }

    from loco.llm.ast_candidate_schema import load_llm_candidate_payload
    from loco.llm.operator_prompt_contract import build_operator_prompt_contract

    load_llm_candidate_payload(_valid_llm_payload())
    build_operator_prompt_contract()

    forbidden_loaded_after = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }
    assert forbidden_loaded_after == forbidden_loaded_before

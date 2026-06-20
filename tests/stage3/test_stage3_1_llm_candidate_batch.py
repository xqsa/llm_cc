import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage3_1_llm_candidate_batch.yaml"
RAW_OUTPUT = ROOT / "artifacts" / "candidates" / "stage3_1" / "raw_llm_output.json"
ACCEPTED_LOG = (
    ROOT / "artifacts" / "candidates" / "stage3_1" / "accepted_candidates.jsonl"
)
REJECTED_LOG = (
    ROOT / "artifacts" / "candidates" / "stage3_1" / "rejected_candidates.jsonl"
)
REPLAY_REPORT = ROOT / "artifacts" / "candidates" / "stage3_1" / "replay_report.json"
SELF_CHECK = ROOT / "docs" / "stage3" / "stage3_1_self_check_report.md"
STAGE_DOC = ROOT / "docs" / "stage3" / "stage3_1_llm_candidate_batch.md"
PROTOCOL_REPORT = (
    ROOT / "artifacts" / "readiness" / "stage3_0_protocol_lock_report.json"
)


def _valid_candidate(candidate_id: str, variable_id: int = 5) -> dict:
    return {
        "schema_version": "loco.llm_candidate.v1",
        "candidate_id": candidate_id,
        "generator": {
            "type": "llm",
            "provider": "codex",
            "model": "gpt-5-codex",
            "prompt_contract_version": "loco.operator_prompt_contract.v1",
        },
        "ast": {
            "schema_version": "loco.dsl.v1",
            "operator_id": candidate_id,
            "nodes": [
                {
                    "id": "weighted",
                    "kind": "weighted_consensus",
                    "target": {"variable_id": variable_id},
                    "inputs": {"temperature": 1.0},
                },
                {
                    "id": "bounded",
                    "kind": "clip",
                    "target": {"variable_id": variable_id},
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


def _raw_batch() -> dict:
    valid = _valid_candidate("stage3_1_test_valid_weighted_clip_shared_5")
    non_shared = _valid_candidate("stage3_1_test_reject_non_shared_9", variable_id=9)
    forbidden = _valid_candidate("stage3_1_test_reject_optimizer_node")
    forbidden["ast"]["nodes"][0]["kind"] = "optimizer"
    return {
        "schema_version": "loco.stage3_1_raw_llm_batch.v1",
        "stage": "3.1",
        "split": "train",
        "prompt_contract_version": "loco.operator_prompt_contract.v1",
        "source": {
            "provider": "codex",
            "model": "gpt-5-codex",
            "captured_by": "Codex",
        },
        "candidates": [valid, non_shared, forbidden],
    }


def test_stage3_1_logs_train_only_candidate_batch(tmp_path) -> None:
    from loco.llm.candidate_batch import process_stage3_1_candidate_batch

    raw_path = tmp_path / "raw_llm_output.json"
    raw_path.write_text(json.dumps(_raw_batch()), encoding="utf-8")

    result = process_stage3_1_candidate_batch(
        raw_output_path=raw_path,
        output_dir=tmp_path,
        shared_variables={5},
        protocol_report_path=PROTOCOL_REPORT,
    )

    assert result["status"] == "PASS"
    assert result["stage"] == "3.1"
    assert result["split"] == "train"
    assert result["accepted_count"] == 1
    assert result["rejected_count"] == 2
    assert result["no_evolution_run"] is True
    assert result["no_objective_evaluation"] is True
    assert result["no_test_feedback"] is True
    assert result["not_performance_claim"] is True

    accepted = [
        json.loads(line)
        for line in (tmp_path / "accepted_candidates.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    rejected = [
        json.loads(line)
        for line in (tmp_path / "rejected_candidates.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]

    assert accepted[0]["stage"] == "3.1"
    assert accepted[0]["split"] == "train"
    assert accepted[0]["decision"] == "accepted"
    assert accepted[0]["target_scope"] == "shared_variables_only"
    assert accepted[0]["no_test_feedback"] is True
    assert accepted[0]["no_evolution"] is True
    assert accepted[0]["no_objective_evaluation"] is True
    assert len(accepted[0]["ast_fingerprint_sha256"]) == 64

    categories = {row["reject_reason_category"] for row in rejected}
    assert categories == {"non_shared_target", "forbidden_optimizer_or_controller"}
    assert all(row["split"] == "train" for row in rejected)

    replay = json.loads((tmp_path / "replay_report.json").read_text(encoding="utf-8"))
    assert replay["status"] == "PASS"
    assert replay["accepted_count"] == 1
    assert replay["rejected_count"] == 2
    assert replay["test_feedback_violation_count"] == 0


def test_stage3_1_rejects_non_train_raw_batch(tmp_path) -> None:
    from loco.llm.candidate_batch import process_stage3_1_candidate_batch

    payload = _raw_batch()
    payload["split"] = "test"
    raw_path = tmp_path / "raw_llm_output.json"
    raw_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="split must be train"):
        process_stage3_1_candidate_batch(
            raw_output_path=raw_path,
            output_dir=tmp_path,
            shared_variables={5},
            protocol_report_path=PROTOCOL_REPORT,
        )


def test_stage3_1_requires_stage3_0_protocol_pass(tmp_path) -> None:
    from loco.llm.candidate_batch import process_stage3_1_candidate_batch

    raw_path = tmp_path / "raw_llm_output.json"
    raw_path.write_text(json.dumps(_raw_batch()), encoding="utf-8")
    blocked_report = tmp_path / "stage3_0_blocked.json"
    blocked_report.write_text(
        json.dumps(
            {"schema_version": "loco.stage3_protocol_lock.v1", "status": "FAIL"}
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Stage 3.0 protocol lock must be PASS"):
        process_stage3_1_candidate_batch(
            raw_output_path=raw_path,
            output_dir=tmp_path,
            shared_variables={5},
            protocol_report_path=blocked_report,
        )


def test_stage3_1_committed_artifacts_are_replayable_and_train_only() -> None:
    required = [CONFIG, RAW_OUTPUT, ACCEPTED_LOG, REJECTED_LOG, REPLAY_REPORT]
    for path in required:
        assert path.is_file(), path

    raw = json.loads(RAW_OUTPUT.read_text(encoding="utf-8"))
    replay = json.loads(REPLAY_REPORT.read_text(encoding="utf-8"))
    accepted = [
        json.loads(line)
        for line in ACCEPTED_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rejected = [
        json.loads(line)
        for line in REJECTED_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert raw["schema_version"] == "loco.stage3_1_raw_llm_batch.v1"
    assert raw["split"] == "train"
    assert replay["status"] == "PASS"
    assert replay["accepted_count"] >= 1
    assert replay["rejected_count"] >= 1
    assert replay["test_feedback_violation_count"] == 0
    assert {row["split"] for row in accepted + rejected} == {"train"}
    assert all(row["no_test_feedback"] is True for row in accepted + rejected)
    assert all(row["no_evolution"] is True for row in accepted + rejected)
    assert all(row["no_objective_evaluation"] is True for row in accepted + rejected)


def test_stage3_1_docs_state_scope_and_claim_boundary() -> None:
    required = [CONFIG, SELF_CHECK, STAGE_DOC]
    for path in required:
        assert path.is_file(), path

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required)
    assert "Stage 3.1" in combined
    assert "small-batch LLM candidate generation" in combined
    assert "train-only" in combined
    assert "typed coordination operator AST" in combined
    assert "shared variables" in combined
    assert "no evolution run" in combined
    assert "no objective evaluation" in combined
    assert "no optimizer generation" in combined
    assert "no scheduler/controller generation" in combined
    assert "no test feedback" in combined
    assert "not a performance claim" in combined


def test_stage3_1_import_does_not_load_evolution_or_optimizer_clients() -> None:
    forbidden_loaded_before = {
        name for name in sys.modules if name.startswith(("deap", "cma", "pyswarms"))
    }

    from loco.llm.candidate_batch import parse_stage3_1_raw_batch

    parse_stage3_1_raw_batch(_raw_batch())

    forbidden_loaded_after = {
        name for name in sys.modules if name.startswith(("deap", "cma", "pyswarms"))
    }
    assert forbidden_loaded_after == forbidden_loaded_before

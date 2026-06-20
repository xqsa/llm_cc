import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "artifacts" / "candidates" / "stage2_6"
ACCEPTED_LOG = LOG_DIR / "accepted_candidates.jsonl"
REJECTED_LOG = LOG_DIR / "rejected_candidates.jsonl"
REJECTION_CORPUS = LOG_DIR / "rejection_corpus.jsonl"
REPLAY_REPORT = LOG_DIR / "replay_report.json"


def _valid_candidate() -> dict:
    return {
        "schema_version": "loco.dsl.v1",
        "operator_id": "stage2_6_valid_weighted_clip_shared_5",
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
    }


def _non_shared_candidate() -> dict:
    payload = _valid_candidate()
    payload["operator_id"] = "stage2_6_reject_non_shared_target_9"
    payload["nodes"][0]["target"]["variable_id"] = 9
    payload["nodes"][1]["target"]["variable_id"] = 9
    return payload


def _optimizer_candidate() -> dict:
    payload = _valid_candidate()
    payload["operator_id"] = "stage2_6_reject_optimizer_node"
    payload["nodes"][0]["kind"] = "optimizer"
    return payload


def test_stage2_6_logs_accepted_and_rejected_candidates_with_schema(tmp_path) -> None:
    from loco.coordination.candidate_logging import log_candidate_preflight

    result = log_candidate_preflight(
        [_valid_candidate(), _non_shared_candidate(), _optimizer_candidate()],
        shared_variables={5},
        output_dir=tmp_path,
        source_stage="stage2_6_test_fixture",
    )

    assert result.total_count == 3
    assert result.accepted_count == 1
    assert result.rejected_count == 2
    assert result.accepted_log_path.is_file()
    assert result.rejected_log_path.is_file()
    assert result.replay_report_path.is_file()

    accepted = [
        json.loads(line)
        for line in result.accepted_log_path.read_text(encoding="utf-8").splitlines()
    ]
    rejected = [
        json.loads(line)
        for line in result.rejected_log_path.read_text(encoding="utf-8").splitlines()
    ]

    assert len(accepted) == 1
    assert accepted[0]["log_schema_version"] == "loco.candidate_log.v1"
    assert accepted[0]["stage"] == "2.6"
    assert accepted[0]["decision"] == "accepted"
    assert accepted[0]["candidate_id"] == "stage2_6_valid_weighted_clip_shared_5"
    assert len(accepted[0]["ast_fingerprint_sha256"]) == 64
    assert accepted[0]["no_llm"] is True
    assert accepted[0]["no_evolution"] is True
    assert accepted[0]["no_test_feedback"] is True
    assert accepted[0]["split"] == "pre_stage3_schema_only"
    assert accepted[0]["serialized_ast"].startswith("{")

    categories = {row["reject_reason_category"] for row in rejected}
    assert categories == {"non_shared_target", "forbidden_optimizer_or_controller"}
    for row in rejected:
        assert row["log_schema_version"] == "loco.candidate_log.v1"
        assert row["stage"] == "2.6"
        assert row["decision"] == "rejected"
        assert row["candidate_id"].startswith("stage2_6_reject_")
        assert row["reject_reason"]
        assert row["no_llm"] is True
        assert row["no_evolution"] is True
        assert row["no_test_feedback"] is True

    replay = json.loads(result.replay_report_path.read_text(encoding="utf-8"))
    assert replay["status"] == "PASS"
    assert replay["total_count"] == 3
    assert replay["accepted_count"] == 1
    assert replay["rejected_count"] == 2


def test_stage2_6_replay_detects_tampered_accepted_log(tmp_path) -> None:
    from loco.coordination.candidate_logging import (
        log_candidate_preflight,
        replay_candidate_logs,
    )

    result = log_candidate_preflight(
        [_valid_candidate()],
        shared_variables={5},
        output_dir=tmp_path,
        source_stage="stage2_6_test_fixture",
    )
    row = json.loads(result.accepted_log_path.read_text(encoding="utf-8"))
    row["ast_payload"]["nodes"][0]["inputs"]["temperature"] = 2.0
    result.accepted_log_path.write_text(json.dumps(row, sort_keys=True) + "\n")

    replay = replay_candidate_logs(
        accepted_log_path=result.accepted_log_path,
        rejected_log_path=result.rejected_log_path,
        shared_variables={5},
        report_path=tmp_path / "tamper_report.json",
    )

    assert replay["status"] == "FAIL"
    assert replay["fingerprint_mismatch_count"] == 1


def test_stage2_6_rejection_corpus_is_replayable_and_covers_required_categories() -> (
    None
):
    from loco.coordination.candidate_logging import replay_rejection_corpus

    result = replay_rejection_corpus(
        corpus_path=REJECTION_CORPUS,
        shared_variables={5},
        report_path=REPLAY_REPORT,
    )

    assert REJECTION_CORPUS.is_file()
    assert REPLAY_REPORT.is_file()
    assert result["status"] == "PASS"
    assert result["accepted_count"] == 1
    assert result["rejected_count"] >= 5
    assert set(result["reject_reason_categories"]) >= {
        "non_shared_target",
        "forbidden_optimizer_or_controller",
        "executable_code",
        "forbidden_metadata",
        "invalid_schema",
    }


def test_stage2_6_artifacts_and_docs_state_no_llm_evolution_or_test_feedback() -> None:
    required_paths = [
        ROOT / "configs" / "stage2_6_candidate_logging.yaml",
        ROOT / "docs" / "stage2" / "stage2_6_candidate_logging.md",
        ROOT / "docs" / "stage2" / "stage2_6_self_check_report.md",
        ACCEPTED_LOG,
        REJECTED_LOG,
        REJECTION_CORPUS,
        REPLAY_REPORT,
    ]
    for path in required_paths:
        assert path.is_file(), path

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required_paths)
    assert "no LLM" in combined
    assert "no evolution" in combined
    assert "no optimizer" in combined
    assert "no test feedback" in combined
    assert "candidate artifact logging schema" in combined
    assert "replay verifier" in combined


def test_stage2_6_does_not_import_llm_or_evolution_modules(tmp_path) -> None:
    forbidden_loaded_before = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }

    from loco.coordination.candidate_logging import log_candidate_preflight

    log_candidate_preflight(
        [_valid_candidate()],
        shared_variables={5},
        output_dir=tmp_path,
        source_stage="stage2_6_test_fixture",
    )

    forbidden_loaded_after = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }
    assert forbidden_loaded_after == forbidden_loaded_before


def test_stage2_6_replay_rejects_missing_log_file(tmp_path) -> None:
    from loco.coordination.candidate_logging import replay_candidate_logs

    with pytest.raises(FileNotFoundError):
        replay_candidate_logs(
            accepted_log_path=tmp_path / "missing_accepted.jsonl",
            rejected_log_path=tmp_path / "missing_rejected.jsonl",
            shared_variables={5},
            report_path=tmp_path / "report.json",
        )

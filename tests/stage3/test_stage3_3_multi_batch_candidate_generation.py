import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage3_3_multi_batch_candidate_generation.yaml"
OUTPUT_DIR = ROOT / "artifacts" / "candidates" / "stage3_3"
RAW_BATCH_DIR = OUTPUT_DIR / "raw_batches"
ACCEPTED_LOG = OUTPUT_DIR / "accepted_candidates.jsonl"
REJECTED_LOG = OUTPUT_DIR / "rejected_candidates.jsonl"
DEDUP_REPORT = OUTPUT_DIR / "dedup_report.json"
REJECTION_TAXONOMY = OUTPUT_DIR / "rejection_taxonomy.json"
MULTI_BATCH_REPORT = OUTPUT_DIR / "multi_batch_report.json"
SELF_CHECK = ROOT / "docs" / "stage3" / "stage3_3_self_check_report.md"
STAGE_DOC = ROOT / "docs" / "stage3" / "stage3_3_multi_batch_candidate_generation.md"
PROTOCOL_REPORT = (
    ROOT / "artifacts" / "readiness" / "stage3_0_protocol_lock_report.json"
)


def _candidate(candidate_id: str, variable_id: int = 5, kind: str = "clip") -> dict:
    return {
        "schema_version": "loco.llm_candidate.v1",
        "candidate_id": candidate_id,
        "generator": {
            "type": "llm",
            "provider": "fake",
            "model": "fake-chat-model",
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
                    "kind": kind,
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


def _batch_text(batch_index: int) -> str:
    duplicate = _candidate("stage3_3_fake_duplicate_weighted_clip_shared_5")
    if batch_index == 0:
        candidates = [
            duplicate,
            _candidate("stage3_3_fake_reject_non_shared_9", variable_id=9),
        ]
    else:
        forbidden = _candidate("stage3_3_fake_reject_optimizer_node")
        forbidden["ast"]["nodes"][0]["kind"] = "optimizer"
        candidates = [
            duplicate,
            _candidate("stage3_3_fake_unique_clip_shared_6", variable_id=6),
            forbidden,
        ]
    payload = {
        "schema_version": "loco.stage3_1_raw_llm_batch.v1",
        "stage": "3.1",
        "split": "train",
        "prompt_contract_version": "loco.operator_prompt_contract.v1",
        "source": {
            "provider": "fake",
            "model": "fake-chat-model",
            "captured_by": f"unit-test-batch-{batch_index}",
        },
        "candidates": candidates,
    }
    return json.dumps(payload)


class _FakeMultiBatchChatHandler(BaseHTTPRequestHandler):
    request_payloads: list[dict] = []
    auth_headers: list[str] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        body = self.rfile.read(length)
        payload = json.loads(body)
        batch_index = len(_FakeMultiBatchChatHandler.request_payloads)
        _FakeMultiBatchChatHandler.request_payloads.append(payload)
        _FakeMultiBatchChatHandler.auth_headers.append(
            self.headers.get("Authorization", "")
        )
        response = {
            "id": f"chatcmpl_fake_{batch_index}",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": _batch_text(batch_index),
                    }
                }
            ],
            "usage": {"prompt_tokens": 10 + batch_index, "completion_tokens": 30},
        }
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


@pytest.fixture
def fake_multi_batch_server():
    _FakeMultiBatchChatHandler.request_payloads = []
    _FakeMultiBatchChatHandler.auth_headers = []
    server = HTTPServer(("127.0.0.1", 0), _FakeMultiBatchChatHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_stage3_3_runs_train_only_multi_batch_generation_and_hardens_corpus(
    tmp_path,
    fake_multi_batch_server,
) -> None:
    from loco.llm.multibatch_candidate_generator import run_stage3_3_multi_batch

    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "LLM_API_KEY=secret-test-key",
                f"LLM_BASE_URL=http://127.0.0.1:{fake_multi_batch_server.server_port}",
                "LLM_MODEL=fake-chat-model",
                "LLM_REASONING_EFFORT=high",
                "LLM_WIRE_API=chat",
            ]
        ),
        encoding="utf-8",
    )

    result = run_stage3_3_multi_batch(
        env_path=env_path,
        output_dir=tmp_path,
        shared_variables={5, 6},
        protocol_report_path=PROTOCOL_REPORT,
        batch_count=2,
        candidates_per_batch=3,
        temperature=0.35,
    )

    assert result["status"] == "PASS"
    assert result["stage"] == "3.3"
    assert result["api_call_count"] == 2
    assert result["split"] == "train"
    assert result["raw_candidate_count"] == 5
    assert result["accepted_count"] == 3
    assert result["unique_accepted_count"] == 2
    assert result["duplicate_accepted_count"] == 1
    assert result["rejected_count"] == 2
    assert result["no_evolution_run"] is True
    assert result["no_objective_evaluation"] is True
    assert result["no_test_feedback"] is True
    assert result["not_performance_claim"] is True
    assert result["secret_redacted"] is True

    raw_response_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((tmp_path / "raw_batches").glob("raw_response_*.json"))
    )
    assert "secret-test-key" not in raw_response_text
    assert "Authorization" not in raw_response_text

    dedup = json.loads((tmp_path / "dedup_report.json").read_text(encoding="utf-8"))
    taxonomy = json.loads(
        (tmp_path / "rejection_taxonomy.json").read_text(encoding="utf-8")
    )
    accepted = [
        json.loads(line)
        for line in (tmp_path / "accepted_candidates.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]

    assert dedup["status"] == "PASS"
    assert dedup["duplicate_accepted_count"] == 1
    assert taxonomy["status"] == "PASS"
    assert taxonomy["categories"] == {
        "forbidden_optimizer_or_controller": 1,
        "non_shared_target": 1,
    }
    assert {row["split"] for row in accepted} == {"train"}
    assert all(row["no_evolution"] is True for row in accepted)
    assert all(row["no_objective_evaluation"] is True for row in accepted)
    assert len(_FakeMultiBatchChatHandler.request_payloads) == 2
    assert _FakeMultiBatchChatHandler.auth_headers == [
        "Bearer secret-test-key",
        "Bearer secret-test-key",
    ]


def test_stage3_3_committed_artifacts_are_replayable_and_boundary_honest() -> None:
    required = [
        CONFIG,
        RAW_BATCH_DIR,
        ACCEPTED_LOG,
        REJECTED_LOG,
        DEDUP_REPORT,
        REJECTION_TAXONOMY,
        MULTI_BATCH_REPORT,
    ]
    for path in required:
        assert path.exists(), path

    report = json.loads(MULTI_BATCH_REPORT.read_text(encoding="utf-8"))
    dedup = json.loads(DEDUP_REPORT.read_text(encoding="utf-8"))
    taxonomy = json.loads(REJECTION_TAXONOMY.read_text(encoding="utf-8"))
    raw_response_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(RAW_BATCH_DIR.glob("raw_response_*.json"))
    )

    assert report["status"] == "PASS"
    assert report["stage"] == "3.3"
    assert report["split"] == "train"
    assert report["api_call_count"] >= 2
    assert report["accepted_count"] >= 1
    assert report["unique_accepted_count"] >= 1
    assert report["rejected_count"] >= 0
    assert report["no_evolution_run"] is True
    assert report["no_objective_evaluation"] is True
    assert report["no_test_feedback"] is True
    assert report["not_performance_claim"] is True
    assert dedup["status"] == "PASS"
    assert taxonomy["status"] == "PASS"
    assert "sk-" not in raw_response_text
    assert "Authorization" not in raw_response_text
    assert "Bearer" not in raw_response_text
    assert "LLM_API_KEY" not in raw_response_text


def test_stage3_3_docs_state_multi_batch_boundary() -> None:
    required = [CONFIG, STAGE_DOC, SELF_CHECK]
    for path in required:
        assert path.is_file(), path

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required)
    assert "Stage 3.3" in combined
    assert "train-only multi-batch" in combined
    assert "typed coordination operator AST" in combined
    assert "rejection-corpus hardening" in combined
    assert "dedup" in combined
    assert "no evolution run" in combined
    assert "no objective evaluation" in combined
    assert "no optimizer generation" in combined
    assert "no scheduler/controller generation" in combined
    assert "no test feedback" in combined
    assert "not a performance claim" in combined

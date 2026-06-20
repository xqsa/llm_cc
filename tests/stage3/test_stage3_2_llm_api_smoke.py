import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage3_2_llm_api_smoke.yaml"
ENV_EXAMPLE = ROOT / ".env.example"
RAW_RESPONSE = ROOT / "artifacts" / "candidates" / "stage3_2" / "raw_response.json"
RAW_OUTPUT = ROOT / "artifacts" / "candidates" / "stage3_2" / "raw_llm_output.json"
ACCEPTED_LOG = (
    ROOT / "artifacts" / "candidates" / "stage3_2" / "accepted_candidates.jsonl"
)
REJECTED_LOG = (
    ROOT / "artifacts" / "candidates" / "stage3_2" / "rejected_candidates.jsonl"
)
REPLAY_REPORT = ROOT / "artifacts" / "candidates" / "stage3_2" / "replay_report.json"
SMOKE_REPORT = ROOT / "artifacts" / "candidates" / "stage3_2" / "smoke_report.json"
STAGE_DOC = ROOT / "docs" / "stage3" / "stage3_2_llm_api_smoke.md"
SELF_CHECK = ROOT / "docs" / "stage3" / "stage3_2_self_check_report.md"


def _candidate_batch_text() -> str:
    payload = {
        "schema_version": "loco.stage3_1_raw_llm_batch.v1",
        "stage": "3.1",
        "split": "train",
        "prompt_contract_version": "loco.operator_prompt_contract.v1",
        "source": {
            "provider": "fake",
            "model": "fake-chat-model",
            "captured_by": "unit-test",
        },
        "candidates": [
            {
                "schema_version": "loco.llm_candidate.v1",
                "candidate_id": "stage3_2_fake_weighted_clip_shared_5",
                "generator": {
                    "type": "llm",
                    "provider": "fake",
                    "model": "fake-chat-model",
                    "prompt_contract_version": "loco.operator_prompt_contract.v1",
                },
                "ast": {
                    "schema_version": "loco.dsl.v1",
                    "operator_id": "stage3_2_fake_weighted_clip_shared_5",
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
                            "inputs": {
                                "source": "weighted",
                                "lower": -1.0,
                                "upper": 1.0,
                            },
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
        ],
    }
    return json.dumps(payload)


class _FakeChatHandler(BaseHTTPRequestHandler):
    request_payloads: list[dict] = []
    auth_headers: list[str] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        body = self.rfile.read(length)
        _FakeChatHandler.request_payloads.append(json.loads(body))
        _FakeChatHandler.auth_headers.append(self.headers.get("Authorization", ""))
        response = {
            "id": "chatcmpl_fake",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": _candidate_batch_text(),
                    }
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 34},
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
def fake_chat_server():
    _FakeChatHandler.request_payloads = []
    _FakeChatHandler.auth_headers = []
    server = HTTPServer(("127.0.0.1", 0), _FakeChatHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_stage3_2_provider_client_calls_chat_api_without_leaking_secret(
    fake_chat_server,
) -> None:
    from loco.llm.provider_client import LLMClientConfig, call_chat_completion

    config = LLMClientConfig(
        api_key="secret-test-key",
        base_url=f"http://127.0.0.1:{fake_chat_server.server_port}",
        model="fake-chat-model",
        wire_api="chat",
        reasoning_effort="high",
        timeout_seconds=10,
    )
    response = call_chat_completion(
        config,
        messages=[{"role": "user", "content": "return candidate json"}],
        temperature=0.2,
    )

    assert response.content == _candidate_batch_text()
    assert (
        response.sanitized_response["choices"][0]["message"]["content"] == "<omitted>"
    )
    assert response.provenance["base_url_host"] == "127.0.0.1"
    assert response.provenance["model"] == "fake-chat-model"
    assert response.provenance["wire_api"] == "chat"
    assert "secret-test-key" not in json.dumps(response.to_artifact_dict())
    assert _FakeChatHandler.auth_headers == ["Bearer secret-test-key"]
    assert _FakeChatHandler.request_payloads[0]["model"] == "fake-chat-model"


def test_stage3_2_api_smoke_writes_sanitized_artifacts_and_replay(
    tmp_path,
    fake_chat_server,
) -> None:
    from loco.llm.api_candidate_generator import run_stage3_2_api_smoke

    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "LLM_API_KEY=secret-test-key",
                f"LLM_BASE_URL=http://127.0.0.1:{fake_chat_server.server_port}",
                "LLM_MODEL=fake-chat-model",
                "LLM_REASONING_EFFORT=high",
                "LLM_WIRE_API=chat",
            ]
        ),
        encoding="utf-8",
    )

    result = run_stage3_2_api_smoke(
        env_path=env_path,
        output_dir=tmp_path,
        shared_variables={5},
        protocol_report_path=ROOT
        / "artifacts"
        / "readiness"
        / "stage3_0_protocol_lock_report.json",
    )

    assert result["status"] == "PASS"
    assert result["api_called"] is True
    assert result["split"] == "train"
    assert result["accepted_count"] == 1
    assert result["rejected_count"] == 0
    assert result["no_evolution_run"] is True
    assert result["no_objective_evaluation"] is True
    assert result["no_test_feedback"] is True
    assert result["not_performance_claim"] is True

    raw_response = (tmp_path / "raw_response.json").read_text(encoding="utf-8")
    raw_output = json.loads(
        (tmp_path / "raw_llm_output.json").read_text(encoding="utf-8")
    )
    replay = json.loads((tmp_path / "replay_report.json").read_text(encoding="utf-8"))

    assert "secret-test-key" not in raw_response
    assert raw_output["schema_version"] == "loco.stage3_1_raw_llm_batch.v1"
    assert raw_output["split"] == "train"
    assert replay["status"] == "PASS"


def test_stage3_2_committed_artifacts_are_sanitized_and_replayable() -> None:
    required = [
        CONFIG,
        ENV_EXAMPLE,
        RAW_RESPONSE,
        RAW_OUTPUT,
        ACCEPTED_LOG,
        REJECTED_LOG,
        REPLAY_REPORT,
        SMOKE_REPORT,
    ]
    for path in required:
        assert path.is_file(), path

    raw_response_text = RAW_RESPONSE.read_text(encoding="utf-8")
    env_example_text = ENV_EXAMPLE.read_text(encoding="utf-8")
    replay = json.loads(REPLAY_REPORT.read_text(encoding="utf-8"))
    smoke = json.loads(SMOKE_REPORT.read_text(encoding="utf-8"))

    assert "LLM_API_KEY=" in env_example_text
    assert "sk-" not in raw_response_text
    assert "Authorization" not in raw_response_text
    assert replay["status"] == "PASS"
    assert smoke["status"] == "PASS"
    assert smoke["api_called"] is True
    assert smoke["no_evolution_run"] is True
    assert smoke["no_objective_evaluation"] is True
    assert smoke["no_test_feedback"] is True


def test_stage3_2_docs_state_real_api_boundary() -> None:
    required = [CONFIG, STAGE_DOC, SELF_CHECK]
    for path in required:
        assert path.is_file(), path

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required)
    assert "Stage 3.2" in combined
    assert "Real LLM API Adapter Smoke" in combined
    assert "DeepSeek" in combined
    assert "train-only" in combined
    assert "typed coordination operator AST" in combined
    assert "no evolution run" in combined
    assert "no objective evaluation" in combined
    assert "no test feedback" in combined
    assert "not a performance claim" in combined


def test_stage3_2_env_file_is_ignored() -> None:
    assert (ROOT / ".env").is_file()
    assert ".env" not in {
        str(path) for path in ROOT.joinpath(".git").glob("**/*") if path.name == ".env"
    }

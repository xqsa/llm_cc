import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage3_5_prompt_space_hardening.yaml"
OUTPUT_DIR = ROOT / "artifacts" / "candidates" / "stage3_5"
MULTI_BATCH_REPORT = OUTPUT_DIR / "multi_batch_report.json"
QUALITY_REPORT = OUTPUT_DIR / "quality_filter_report.json"
DIVERSITY_REPORT = OUTPUT_DIR / "static_diversity_audit.json"
COVERAGE_REPORT = OUTPUT_DIR / "coverage_gate_report.json"
SUMMARY_REPORT = OUTPUT_DIR / "stage3_5_summary.json"
SELF_CHECK = ROOT / "docs" / "stage3" / "stage3_5_self_check_report.md"
STAGE_DOC = ROOT / "docs" / "stage3" / "stage3_5_prompt_space_hardening.md"
PROTOCOL_REPORT = (
    ROOT / "artifacts" / "readiness" / "stage3_0_protocol_lock_report.json"
)


def _candidate(candidate_id: str, nodes: list[dict]) -> dict:
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
            "nodes": nodes,
            "output": {"source": nodes[-1]["id"]},
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


def _node(
    node_id: str, kind: str, variable_id: int = 5, inputs: dict | None = None
) -> dict:
    return {
        "id": node_id,
        "kind": kind,
        "target": {"variable_id": variable_id},
        "inputs": inputs or {},
    }


def _coverage_candidates() -> list[dict]:
    return [
        _candidate(
            "stage3_5_fake_weighted_clip",
            [
                _node("w", "weighted_consensus", 5, {"temperature": 1.0}),
                _node("c", "clip", 5, {"source": "w", "lower": -1.0, "upper": 1.0}),
            ],
        ),
        _candidate(
            "stage3_5_fake_projection",
            [
                _node("w", "weighted_consensus", 6, {"temperature": 0.8}),
                _node("p", "projection", 6, {"source": "w", "projection": "box"}),
            ],
        ),
        _candidate(
            "stage3_5_fake_dampening",
            [
                _node("w", "weighted_consensus", 5, {"temperature": 0.5}),
                _node("d", "dampening", 5, {"source": "w", "damping_strength": 0.4}),
            ],
        ),
        _candidate(
            "stage3_5_fake_reweighting",
            [
                _node("r", "reweighting", 6, {"weights": [0.7, 0.3]}),
                _node(
                    "w", "weighted_consensus", 6, {"source": "r", "temperature": 1.2}
                ),
            ],
        ),
        _candidate(
            "stage3_5_fake_repair",
            [
                _node("w", "weighted_consensus", 5, {"temperature": 1.0}),
                _node("repair", "repair", 5, {"source": "w", "mode": "safe"}),
            ],
        ),
        _candidate(
            "stage3_5_fake_best_reward",
            [
                _node("best", "best_reward_select", 6, {"reward_key": "local_delta"}),
                _node(
                    "clip", "clip", 6, {"source": "best", "lower": -1.0, "upper": 1.0}
                ),
            ],
        ),
        _candidate(
            "stage3_5_fake_projection_dampening",
            [
                _node("p", "projection", 5, {"projection": "box"}),
                _node("d", "dampening", 5, {"source": "p", "damping_strength": 0.2}),
            ],
        ),
        _candidate(
            "stage3_5_fake_reweighting_repair",
            [
                _node("r", "reweighting", 6, {"weights": [0.5, 0.5]}),
                _node("repair", "repair", 6, {"source": "r", "mode": "safe"}),
            ],
        ),
        _candidate(
            "stage3_5_fake_consensus_projection_repair",
            [
                _node("c", "consensus", 5),
                _node("p", "projection", 5, {"source": "c", "projection": "box"}),
                _node("repair", "repair", 5, {"source": "p", "mode": "safe"}),
            ],
        ),
        _candidate(
            "stage3_5_fake_reward_dampening_clip",
            [
                _node("best", "best_reward_select", 6, {"reward_key": "local_delta"}),
                _node("d", "dampening", 6, {"source": "best", "damping_strength": 0.3}),
                _node("clip", "clip", 6, {"source": "d", "lower": -2.0, "upper": 2.0}),
            ],
        ),
        _candidate(
            "stage3_5_fake_reweighting_projection",
            [
                _node("r", "reweighting", 5, {"weights": [0.6, 0.4]}),
                _node("p", "projection", 5, {"source": "r", "projection": "box"}),
            ],
        ),
        _candidate(
            "stage3_5_fake_repair_clip",
            [
                _node("repair", "repair", 6, {"mode": "safe"}),
                _node(
                    "clip", "clip", 6, {"source": "repair", "lower": -1.0, "upper": 1.0}
                ),
            ],
        ),
    ]


def _batch_text(batch_index: int) -> str:
    candidates = _coverage_candidates()[batch_index * 4 : (batch_index + 1) * 4]
    payload = {
        "schema_version": "loco.stage3_1_raw_llm_batch.v1",
        "stage": "3.1",
        "split": "train",
        "prompt_contract_version": "loco.operator_prompt_contract.v1",
        "source": {
            "provider": "fake",
            "model": "fake-chat-model",
            "captured_by": f"stage3-5-fake-batch-{batch_index}",
        },
        "candidates": candidates,
    }
    return json.dumps(payload)


class _FakeCoverageChatHandler(BaseHTTPRequestHandler):
    request_payloads: list[dict] = []
    auth_headers: list[str] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["Content-Length"])
        body = self.rfile.read(length)
        batch_index = len(_FakeCoverageChatHandler.request_payloads)
        _FakeCoverageChatHandler.request_payloads.append(json.loads(body))
        _FakeCoverageChatHandler.auth_headers.append(
            self.headers.get("Authorization", "")
        )
        response = {
            "id": f"stage3_5_fake_{batch_index}",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": _batch_text(batch_index),
                    }
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 60},
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
def fake_coverage_server():
    _FakeCoverageChatHandler.request_payloads = []
    _FakeCoverageChatHandler.auth_headers = []
    server = HTTPServer(("127.0.0.1", 0), _FakeCoverageChatHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_stage3_5_prompt_hardened_generation_passes_coverage_gate(
    tmp_path,
    fake_coverage_server,
) -> None:
    from loco.llm.prompt_space_hardening import run_stage3_5_prompt_space_hardening

    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "LLM_API_KEY=secret-test-key",
                f"LLM_BASE_URL=http://127.0.0.1:{fake_coverage_server.server_port}",
                "LLM_MODEL=fake-chat-model",
                "LLM_REASONING_EFFORT=high",
                "LLM_WIRE_API=chat",
            ]
        ),
        encoding="utf-8",
    )

    result = run_stage3_5_prompt_space_hardening(
        env_path=env_path,
        output_dir=tmp_path,
        shared_variables={5, 6},
        protocol_report_path=PROTOCOL_REPORT,
        batch_count=3,
        candidates_per_batch=4,
        temperature=0.45,
    )

    assert result["status"] == "PASS"
    assert result["stage"] == "3.5"
    assert result["api_call_count"] == 3
    assert result["raw_candidate_count"] == 12
    assert result["accepted_count"] == 12
    assert result["quality_pass_count"] == 12
    assert result["unique_kind_sequence_count"] >= 6
    assert result["operator_family_count"] >= 6
    assert result["dominant_ratio"] <= 0.5
    assert result["must_include_projection"] is True
    assert result["must_include_dampening"] is True
    assert result["must_include_reweighting"] is True
    assert result["must_include_repair"] is True
    assert result["must_include_best_reward_select"] is True
    assert result["no_evolution_run"] is True
    assert result["no_objective_evaluation"] is True
    assert result["not_performance_claim"] is True

    raw_response_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((tmp_path / "raw_batches").glob("raw_response_*.json"))
    )
    assert "secret-test-key" not in raw_response_text
    assert "Authorization" not in raw_response_text
    assert len(_FakeCoverageChatHandler.request_payloads) == 3


def test_stage3_5_committed_artifacts_satisfy_pass_thresholds() -> None:
    required = [
        CONFIG,
        MULTI_BATCH_REPORT,
        QUALITY_REPORT,
        DIVERSITY_REPORT,
        COVERAGE_REPORT,
        SUMMARY_REPORT,
    ]
    for path in required:
        assert path.is_file(), path

    summary = json.loads(SUMMARY_REPORT.read_text(encoding="utf-8"))
    coverage = json.loads(COVERAGE_REPORT.read_text(encoding="utf-8"))
    diversity = json.loads(DIVERSITY_REPORT.read_text(encoding="utf-8"))

    assert summary["status"] == "PASS"
    assert summary["api_call_count"] >= 3
    assert summary["raw_candidate_count"] >= 12
    assert summary["accepted_count"] >= 8
    assert summary["quality_pass_count"] >= 8
    assert summary["unique_kind_sequence_count"] >= 5
    assert summary["operator_family_count"] >= 5
    assert summary["dominant_ratio"] <= 0.5
    assert summary["must_include_projection"] is True
    assert summary["must_include_dampening"] is True
    assert summary["must_include_reweighting"] is True
    assert summary["must_include_repair"] is True
    assert summary["must_include_best_reward_select"] is True
    assert summary["no_evolution_run"] is True
    assert summary["no_objective_evaluation"] is True
    assert summary["not_performance_claim"] is True

    assert coverage["status"] == "PASS"
    assert coverage["thresholds"]["raw_candidate_count"] == 12
    assert coverage["thresholds"]["quality_pass_count"] == 8
    assert coverage["required_node_kinds_present"] == {
        "best_reward_select": True,
        "dampening": True,
        "projection": True,
        "repair": True,
        "reweighting": True,
    }
    assert len(diversity["operator_family_counts"]) >= 5


def test_stage3_5_docs_state_prompt_hardening_boundary() -> None:
    required = [CONFIG, STAGE_DOC, SELF_CHECK]
    for path in required:
        assert path.is_file(), path

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required)
    assert "Stage 3.5" in combined
    assert "prompt-space hardening" in combined
    assert "projection" in combined
    assert "dampening" in combined
    assert "reweighting" in combined
    assert "repair" in combined
    assert "best_reward_select" in combined
    assert "no evolution run" in combined
    assert "no objective evaluation" in combined
    assert "not a performance claim" in combined

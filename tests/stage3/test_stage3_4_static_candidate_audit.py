import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage3_4_static_candidate_audit.yaml"
OUTPUT_DIR = ROOT / "artifacts" / "candidates" / "stage3_4"
QUALITY_REPORT = OUTPUT_DIR / "quality_filter_report.json"
DIVERSITY_REPORT = OUTPUT_DIR / "static_diversity_audit.json"
SUMMARY_REPORT = OUTPUT_DIR / "stage3_4_summary.json"
SELF_CHECK = ROOT / "docs" / "stage3" / "stage3_4_self_check_report.md"
STAGE_DOC = ROOT / "docs" / "stage3" / "stage3_4_static_candidate_audit.md"
STAGE3_3_ACCEPTED = (
    ROOT / "artifacts" / "candidates" / "stage3_3" / "accepted_candidates.jsonl"
)


def _candidate_row(candidate_id: str, nodes: list[dict]) -> dict:
    ast = {
        "schema_version": "loco.dsl.v1",
        "operator_id": candidate_id,
        "nodes": nodes,
        "output": {"source": nodes[-1]["id"]},
    }
    return {
        "log_schema_version": "loco.stage3_1_candidate_log.v1",
        "stage": "3.1",
        "split": "train",
        "candidate_id": candidate_id,
        "decision": "accepted",
        "llm_candidate_payload": {
            "schema_version": "loco.llm_candidate.v1",
            "candidate_id": candidate_id,
            "generator": {
                "type": "llm",
                "provider": "fake",
                "model": "fake",
                "prompt_contract_version": "loco.operator_prompt_contract.v1",
            },
            "ast": ast,
            "declared_scope": {
                "target": "shared_variables_only",
                "not_optimizer": True,
                "not_controller": True,
                "not_scheduler": True,
                "not_optimizer_selection": True,
                "not_benchmark_specific": True,
                "no_test_feedback": True,
            },
        },
        "ast_fingerprint_sha256": candidate_id.rjust(64, "0")[-64:],
        "no_evolution": True,
        "no_objective_evaluation": True,
        "no_test_feedback": True,
        "not_performance_claim": True,
    }


def _node(
    node_id: str, kind: str, variable_id: int, inputs: dict | None = None
) -> dict:
    return {
        "id": node_id,
        "kind": kind,
        "target": {"variable_id": variable_id},
        "inputs": inputs or {},
    }


def test_stage3_4_static_audit_detects_quality_and_diversity(tmp_path) -> None:
    from loco.llm.static_candidate_audit import run_stage3_4_static_audit

    rows = [
        _candidate_row(
            "weighted_clip_a",
            [
                _node("weighted", "weighted_consensus", 5, {"temperature": 1.0}),
                _node(
                    "bounded",
                    "clip",
                    5,
                    {"source": "weighted", "lower": -1.0, "upper": 1.0},
                ),
            ],
        ),
        _candidate_row(
            "weighted_clip_b",
            [
                _node("weighted", "weighted_consensus", 6, {"temperature": 0.5}),
                _node(
                    "bounded",
                    "clip",
                    6,
                    {"source": "weighted", "lower": -2.0, "upper": 2.0},
                ),
            ],
        ),
        _candidate_row(
            "projection_dampening_repair",
            [
                _node("project", "projection", 5, {"projection": "box"}),
                _node(
                    "dampen",
                    "dampening",
                    5,
                    {"source": "project", "damping_strength": 0.3},
                ),
                _node("repair", "repair", 5, {"source": "dampen", "mode": "safe"}),
            ],
        ),
    ]
    accepted_path = tmp_path / "accepted_candidates.jsonl"
    accepted_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )

    result = run_stage3_4_static_audit(
        accepted_log_path=accepted_path,
        output_dir=tmp_path,
        low_diversity_unique_kind_sequence_threshold=2,
    )

    assert result["status"] == "PASS"
    assert result["stage"] == "3.4"
    assert result["candidate_count"] == 3
    assert result["quality_pass_count"] == 3
    assert result["quality_reject_count"] == 0
    assert result["unique_kind_sequence_count"] == 2
    assert result["dominant_kind_sequence"] == "weighted_consensus->clip"
    assert result["dominant_kind_sequence_count"] == 2
    assert result["low_diversity_warning"] is False
    assert result["no_evolution_run"] is True
    assert result["no_objective_evaluation"] is True
    assert result["not_performance_claim"] is True

    quality = json.loads((tmp_path / "quality_filter_report.json").read_text())
    diversity = json.loads((tmp_path / "static_diversity_audit.json").read_text())

    assert quality["status"] == "PASS"
    assert quality["quality_pass_count"] == 3
    assert diversity["operator_family_counts"] == {
        "projection+dampening+repair": 1,
        "weighted_consensus+clip": 2,
    }
    assert diversity["node_kind_counts"]["clip"] == 2
    assert diversity["target_variable_counts"] == {"5": 5, "6": 2}


def test_stage3_4_committed_audit_reports_stage3_3_candidates_honestly() -> None:
    required = [CONFIG, QUALITY_REPORT, DIVERSITY_REPORT, SUMMARY_REPORT]
    for path in required:
        assert path.is_file(), path

    quality = json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))
    diversity = json.loads(DIVERSITY_REPORT.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY_REPORT.read_text(encoding="utf-8"))

    assert summary["status"] == "PASS"
    assert summary["stage"] == "3.4"
    assert summary["candidate_count"] == 9
    assert summary["quality_pass_count"] == 7
    assert summary["quality_reject_count"] == 2
    assert summary["unique_kind_sequence_count"] == 2
    assert summary["dominant_kind_sequence"] == "weighted_consensus->clip"
    assert summary["dominant_kind_sequence_count"] == 7
    assert summary["low_diversity_warning"] is True
    assert summary["no_evolution_run"] is True
    assert summary["no_objective_evaluation"] is True
    assert summary["not_performance_claim"] is True

    assert quality["quality_pass_count"] == 7
    assert quality["quality_reject_count"] == 2
    assert quality["issue_counts"] == {"single_consensus_only": 2}
    assert diversity["kind_sequence_counts"] == {
        "weighted_consensus": 2,
        "weighted_consensus->clip": 7,
    }
    assert diversity["operator_family_counts"] == {
        "weighted_consensus": 2,
        "weighted_consensus+clip": 7,
    }


def test_stage3_4_docs_state_static_only_boundary() -> None:
    required = [CONFIG, STAGE_DOC, SELF_CHECK]
    for path in required:
        assert path.is_file(), path

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required)
    assert "Stage 3.4" in combined
    assert "static diversity audit" in combined
    assert "candidate quality filter" in combined
    assert "weighted_consensus->clip" in combined
    assert "low diversity" in combined
    assert "no evolution run" in combined
    assert "no objective evaluation" in combined
    assert "not a performance claim" in combined
    assert "no optimizer generation" in combined
    assert "no scheduler/controller generation" in combined

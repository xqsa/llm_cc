import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage5_1_selected_operator_freeze.yaml"
SELECTION_DECISION = (
    ROOT / "artifacts" / "validation" / "stage5_0" / "selection_decision.json"
)
VALIDATION_REPORT = (
    ROOT / "artifacts" / "validation" / "stage5_0" / "validation_report.json"
)
FROZEN_POOL = (
    ROOT / "artifacts" / "candidates" / "stage3_6" / "frozen_candidate_pool.jsonl"
)
OUTPUT_DIR = ROOT / "artifacts" / "selected" / "stage5_1"
SELECTED_OPERATOR = OUTPUT_DIR / "selected_operator.json"
SELECTED_AST = OUTPUT_DIR / "selected_operator_ast.json"
FREEZE_MANIFEST = OUTPUT_DIR / "selected_operator_manifest.json"
SEALED_TEST_PROTOCOL = OUTPUT_DIR / "sealed_test_readiness_protocol.json"
FREEZE_REPORT = OUTPUT_DIR / "freeze_report.json"
STAGE_DOC = ROOT / "docs" / "stage5" / "stage5_1_selected_operator_freeze.md"
SELF_CHECK = ROOT / "docs" / "stage5" / "stage5_1_self_check_report.md"
README = ROOT / "README.md"


def test_stage5_1_freezes_only_selected_candidate_for_sealed_test(tmp_path) -> None:
    from loco.coordination.selected_operator_freeze import (
        freeze_stage5_1_selected_operator,
    )

    report = freeze_stage5_1_selected_operator(
        selection_decision_path=SELECTION_DECISION,
        validation_report_path=VALIDATION_REPORT,
        frozen_pool_path=FROZEN_POOL,
        output_dir=tmp_path,
    )

    assert report["stage"] == "5.1"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "5.0"
    assert report["selected_candidate_id"] == (
        "stage3_5_batch_1_weighted_consensus_projection"
    )
    assert report["selected_operator_frozen"] is True
    assert report["candidate_count"] == 1
    assert report["sealed_test_ready"] is True
    assert report["next_status"] == "READY_FOR_STAGE6_SEALED_TEST_REPORTING"
    assert report["validation_feedback_used"] is False
    assert report["test_feedback_used"] is False
    assert report["sealed_test_access_used"] is False
    assert report["objective_evaluation_used"] is False
    assert report["llm_call_used"] is False
    assert report["new_candidate_generation_used"] is False
    assert report["prompt_revision_used"] is False
    assert report["train_search_revision_used"] is False
    assert report["promotion_rule_revision_used"] is False
    assert report["validation_rule_revision_used"] is False
    assert report["baseopt_modified"] is False
    assert report["optimizer_generation_used"] is False
    assert report["controller_scheduler_generation_used"] is False
    assert report["not_performance_claim"] is True

    selected_operator = json.loads((tmp_path / "selected_operator.json").read_text())
    selected_ast = json.loads((tmp_path / "selected_operator_ast.json").read_text())
    manifest = json.loads((tmp_path / "selected_operator_manifest.json").read_text())
    protocol = json.loads(
        (tmp_path / "sealed_test_readiness_protocol.json").read_text()
    )

    assert selected_operator["freeze_status"] == "FROZEN_FOR_SEALED_TEST_NOT_FINAL"
    assert selected_operator["candidate_id"] == report["selected_candidate_id"]
    assert selected_operator["kind_sequence"] == "weighted_consensus->projection"
    assert selected_operator["operator_family"] == "weighted_consensus+projection"
    assert selected_operator["target_scope"] == "shared_variables_only"
    assert selected_operator["selection_status"] == "SELECTED_FOR_SEALED_TEST_NOT_FINAL"
    assert selected_operator["selected_validation_score"] == 0.300902808172
    assert selected_operator["not_performance_claim"] is True

    assert selected_ast["operator_id"] == report["selected_candidate_id"]
    assert selected_ast["schema_version"] == "loco.dsl.v1"
    assert len(selected_ast["nodes"]) == 2

    assert manifest["status"] == "PASS"
    assert manifest["selected_operator_frozen"] is True
    assert manifest["selected_candidate_id"] == report["selected_candidate_id"]
    assert manifest["source_selection_decision_sha256"]
    assert manifest["source_frozen_candidate_sha256"]
    assert manifest["selected_operator_freeze_sha256"]
    assert manifest["validation_feedback_used"] is False
    assert manifest["test_feedback_used"] is False

    assert protocol["status"] == "READY_FOR_STAGE6_SEALED_TEST_REPORTING"
    assert protocol["allowed_next_use"] == "sealed test final reporting only"
    assert protocol["selected_candidate_id"] == report["selected_candidate_id"]
    assert (
        protocol["selected_operator_freeze_sha256"]
        == manifest["selected_operator_freeze_sha256"]
    )
    assert protocol["no_llm_call"] is True
    assert protocol["no_new_candidate_generation"] is True
    assert protocol["no_validation_rule_revision"] is True
    assert protocol["not_performance_claim"] is True


def test_stage5_1_committed_artifacts_and_docs_record_freeze_boundary() -> None:
    required = [
        CONFIG,
        SELECTED_OPERATOR,
        SELECTED_AST,
        FREEZE_MANIFEST,
        SEALED_TEST_PROTOCOL,
        FREEZE_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    selected_operator = json.loads(SELECTED_OPERATOR.read_text(encoding="utf-8"))
    manifest = json.loads(FREEZE_MANIFEST.read_text(encoding="utf-8"))
    protocol = json.loads(SEALED_TEST_PROTOCOL.read_text(encoding="utf-8"))
    report = json.loads(FREEZE_REPORT.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["stage"] == "5.1"
    assert report["selected_operator_frozen"] is True
    assert report["sealed_test_ready"] is True
    assert report["test_feedback_used"] is False
    assert report["objective_evaluation_used"] is False
    assert report["not_performance_claim"] is True
    assert selected_operator["candidate_id"] == report["selected_candidate_id"]
    assert (
        manifest["selected_operator_freeze_sha256"]
        == protocol["selected_operator_freeze_sha256"]
    )
    assert protocol["status"] == "READY_FOR_STAGE6_SEALED_TEST_REPORTING"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 5.1" in combined
    assert "selected operator freeze" in combined
    assert "FROZEN_FOR_SEALED_TEST_NOT_FINAL" in combined
    assert "stage3_5_batch_1_weighted_consensus_projection" in combined
    assert "no LLM call" in combined
    assert "no new candidate generation" in combined
    assert "no validation-rule revision" in combined
    assert "no sealed-test access" in combined
    assert "no objective evaluation" in combined
    assert "not a performance claim" in combined

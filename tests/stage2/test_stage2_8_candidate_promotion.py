import json
import shutil
import sys
from pathlib import Path

from loco.conflict.conflict_state import GroupProposal, SharedVariableConflictState


ROOT = Path(__file__).resolve().parents[2]
STAGE2_6_DIR = ROOT / "artifacts" / "candidates" / "stage2_6"
STAGE2_7_DIR = ROOT / "artifacts" / "candidates" / "stage2_7"
STAGE2_8_DIR = ROOT / "artifacts" / "operators" / "stage2_8"
MANIFEST_PATH = STAGE2_7_DIR / "sealed_split_manifest.json"
AUDIT_REPORT_PATH = STAGE2_7_DIR / "split_replay_audit_report.json"
PROMOTED_ARTIFACT_PATH = (
    STAGE2_8_DIR / "stage2_6_corpus_valid_weighted_clip_shared_5.json"
)
PROMOTION_RECEIPT_PATH = (
    STAGE2_8_DIR / "stage2_6_corpus_valid_weighted_clip_shared_5_promotion_receipt.json"
)
PROMOTION_REGISTRY_PATH = ROOT / "artifacts" / "operators" / "stage2_8_registry.jsonl"


def _state(variable_id: int) -> SharedVariableConflictState:
    return SharedVariableConflictState.from_group_proposals(
        variable_id=variable_id,
        current_value=0.0,
        bounds=(-2.0, 2.0),
        proposals=[
            GroupProposal(
                group_id=0,
                variable_id=variable_id,
                proposed_value=-1.0,
                reward=0.1,
            ),
            GroupProposal(
                group_id=1,
                variable_id=variable_id,
                proposed_value=1.0,
                reward=0.2,
            ),
        ],
        consensus_history=[],
    )


def test_stage2_8_promoted_artifact_is_committed_and_loadable() -> None:
    from loco.coordination.candidate_promotion import load_promotion_receipt
    from loco.coordination.operator_artifacts import load_frozen_operator_artifact

    artifact = load_frozen_operator_artifact(PROMOTED_ARTIFACT_PATH)
    receipt = load_promotion_receipt(PROMOTION_RECEIPT_PATH)

    assert artifact.artifact_id == (
        "stage2_8.promoted.stage2_6_corpus_valid_weighted_clip_shared_5"
    )
    assert artifact.operator_name == "PromotedCandidateWeightedClip"
    assert artifact.source == "stage2_6_accepted_candidate_promotion"
    assert artifact.target_scope == "shared_variables_only"
    assert artifact.frozen is True
    assert artifact.no_llm is True
    assert artifact.no_evolution is True
    assert artifact.no_optimizer is True
    assert artifact.no_objective_evaluation is True
    assert artifact.no_test_feedback is True
    assert artifact.test_mode_allowed is True
    instantiated = artifact.instantiate_for_conflict_state(_state(variable_id=9))
    assert instantiated["operator_id"] == (
        "stage2_8_promoted_stage2_6_corpus_valid_weighted_clip_shared_5_shared_9"
    )
    assert {node["target"]["variable_id"] for node in instantiated["nodes"]} == {9}

    assert receipt["schema_version"] == "loco.candidate_promotion_receipt.v1"
    assert receipt["stage"] == "2.8"
    assert receipt["status"] == "PROMOTED"
    assert receipt["candidate_id"] == "stage2_6_corpus_valid_weighted_clip_shared_5"
    assert receipt["source_candidate_log_path"].endswith(
        "artifacts/candidates/stage2_6/accepted_candidates.jsonl"
    )
    assert receipt["source_sealed_manifest_path"].endswith(
        "artifacts/candidates/stage2_7/sealed_split_manifest.json"
    )
    assert receipt["source_audit_report_path"].endswith(
        "artifacts/candidates/stage2_7/split_replay_audit_report.json"
    )
    assert receipt["source_ast_fingerprint_sha256"] == (
        "ad6866257797a6373679ec30f1fac4a8c7313c6ec21361d972a622a025deb71c"
    )
    assert len(receipt["sealed_manifest_fingerprint_sha256"]) == 64
    assert len(receipt["promotion_fingerprint_sha256"]) == 64
    assert receipt["no_llm"] is True
    assert receipt["no_evolution"] is True
    assert receipt["no_optimizer"] is True
    assert receipt["no_candidate_generation"] is True
    assert receipt["no_test_feedback"] is True
    assert receipt["no_objective_evaluation"] is True


def test_stage2_8_registry_binds_promoted_artifact_and_receipt() -> None:
    row = json.loads(PROMOTION_REGISTRY_PATH.read_text(encoding="utf-8"))

    assert row["registry_schema_version"] == "loco.promoted_operator_registry.v1"
    assert row["stage"] == "2.8"
    assert row["artifact_id"] == (
        "stage2_8.promoted.stage2_6_corpus_valid_weighted_clip_shared_5"
    )
    assert row["artifact_path"].endswith(
        "artifacts/operators/stage2_8/stage2_6_corpus_valid_weighted_clip_shared_5.json"
    )
    assert row["promotion_receipt_path"].endswith(
        "artifacts/operators/stage2_8/"
        "stage2_6_corpus_valid_weighted_clip_shared_5_promotion_receipt.json"
    )
    assert row["source_candidate_id"] == "stage2_6_corpus_valid_weighted_clip_shared_5"
    assert row["split"] == "pre_stage3_schema_only"
    assert row["target_scope"] == "shared_variables_only"
    assert row["frozen"] is True
    assert row["no_test_feedback"] is True
    assert len(row["artifact_fingerprint_sha256"]) == 64
    assert len(row["promotion_receipt_fingerprint_sha256"]) == 64
    assert len(row["promotion_fingerprint_sha256"]) == 64


def test_stage2_8_promotion_recomputes_committed_artifacts(tmp_path) -> None:
    from loco.coordination.candidate_promotion import promote_accepted_candidate
    from loco.coordination.operator_artifacts import load_frozen_operator_artifact

    output_dir = tmp_path / "stage2_8"
    result = promote_accepted_candidate(
        candidate_id="stage2_6_corpus_valid_weighted_clip_shared_5",
        accepted_log_path=STAGE2_6_DIR / "accepted_candidates.jsonl",
        sealed_manifest_path=MANIFEST_PATH,
        audit_report_path=AUDIT_REPORT_PATH,
        output_dir=output_dir,
        registry_path=tmp_path / "stage2_8_registry.jsonl",
    )

    assert result["status"] == "PROMOTED"
    assert result["candidate_id"] == "stage2_6_corpus_valid_weighted_clip_shared_5"
    assert result["artifact_path"].endswith(
        "stage2_6_corpus_valid_weighted_clip_shared_5.json"
    )
    assert result["promotion_receipt_path"].endswith(
        "stage2_6_corpus_valid_weighted_clip_shared_5_promotion_receipt.json"
    )
    artifact = load_frozen_operator_artifact(output_dir / result["artifact_filename"])
    assert artifact.metadata()["target_scope"] == "shared_variables_only"
    assert artifact.metadata()["no_test_feedback"] is True


def test_stage2_8_promotion_rejects_rejected_candidate_log(tmp_path) -> None:
    from loco.coordination.candidate_promotion import promote_accepted_candidate

    try:
        promote_accepted_candidate(
            candidate_id="stage2_6_reject_optimizer_node",
            accepted_log_path=STAGE2_6_DIR / "rejected_candidates.jsonl",
            sealed_manifest_path=MANIFEST_PATH,
            audit_report_path=AUDIT_REPORT_PATH,
            output_dir=tmp_path / "stage2_8",
            registry_path=tmp_path / "stage2_8_registry.jsonl",
        )
    except ValueError as exc:
        assert "accepted" in str(exc)
    else:
        raise AssertionError("rejected candidate must not be promoted")


def test_stage2_8_promotion_rejects_failed_or_tampered_audit(tmp_path) -> None:
    from loco.coordination.candidate_promotion import promote_accepted_candidate

    audit = tmp_path / "split_replay_audit_report.json"
    shutil.copyfile(AUDIT_REPORT_PATH, audit)
    payload = json.loads(audit.read_text(encoding="utf-8"))
    payload["status"] = "FAIL"
    audit.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    try:
        promote_accepted_candidate(
            candidate_id="stage2_6_corpus_valid_weighted_clip_shared_5",
            accepted_log_path=STAGE2_6_DIR / "accepted_candidates.jsonl",
            sealed_manifest_path=MANIFEST_PATH,
            audit_report_path=audit,
            output_dir=tmp_path / "stage2_8",
            registry_path=tmp_path / "stage2_8_registry.jsonl",
        )
    except ValueError as exc:
        assert "audit" in str(exc).lower()
    else:
        raise AssertionError("failed audit report must block promotion")


def test_stage2_8_docs_and_config_state_boundaries() -> None:
    required = [
        ROOT / "configs" / "stage2_8_candidate_promotion.yaml",
        ROOT / "docs" / "stage2" / "stage2_8_candidate_promotion.md",
        ROOT / "docs" / "stage2" / "stage2_8_self_check_report.md",
        PROMOTED_ARTIFACT_PATH,
        PROMOTION_RECEIPT_PATH,
        PROMOTION_REGISTRY_PATH,
    ]
    for path in required:
        assert path.is_file(), path

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required)
    assert "frozen candidate promotion contract" in combined
    assert "sealed split replay audit" in combined
    assert "no LLM" in combined
    assert "no evolution" in combined
    assert "no optimizer" in combined
    assert "no candidate generation" in combined
    assert "no test feedback" in combined
    assert "no objective evaluation" in combined


def test_stage2_8_promotion_does_not_import_llm_or_evolution_modules(tmp_path) -> None:
    forbidden_loaded_before = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }

    from loco.coordination.candidate_promotion import promote_accepted_candidate

    promote_accepted_candidate(
        candidate_id="stage2_6_corpus_valid_weighted_clip_shared_5",
        accepted_log_path=STAGE2_6_DIR / "accepted_candidates.jsonl",
        sealed_manifest_path=MANIFEST_PATH,
        audit_report_path=AUDIT_REPORT_PATH,
        output_dir=tmp_path / "stage2_8",
        registry_path=tmp_path / "stage2_8_registry.jsonl",
    )

    forbidden_loaded_after = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }
    assert forbidden_loaded_after == forbidden_loaded_before

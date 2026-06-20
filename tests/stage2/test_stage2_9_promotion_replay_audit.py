import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STAGE2_8_REGISTRY_PATH = ROOT / "artifacts" / "operators" / "stage2_8_registry.jsonl"
STAGE2_9_DIR = ROOT / "artifacts" / "operators" / "stage2_9"
AUDIT_REPORT_PATH = STAGE2_9_DIR / "promotion_replay_audit_report.json"


def test_stage2_9_committed_audit_report_replays_stage2_8_registry() -> None:
    report = json.loads(AUDIT_REPORT_PATH.read_text(encoding="utf-8"))

    assert report["schema_version"] == "loco.promotion_replay_audit.v1"
    assert report["stage"] == "2.9"
    assert report["status"] == "PASS"
    assert report["registry_path"].endswith(
        "artifacts/operators/stage2_8_registry.jsonl"
    )
    assert report["registry_entry_count"] == 1
    assert report["audited_artifact_count"] == 1
    assert report["artifact_fingerprint_mismatch_count"] == 0
    assert report["receipt_fingerprint_mismatch_count"] == 0
    assert report["promotion_fingerprint_mismatch_count"] == 0
    assert report["source_candidate_fingerprint_mismatch_count"] == 0
    assert report["sealed_manifest_fingerprint_mismatch_count"] == 0
    assert report["audit_report_fingerprint_mismatch_count"] == 0
    assert report["schema_violation_count"] == 0
    assert report["boundary_violation_count"] == 0
    assert report["no_llm"] is True
    assert report["no_evolution"] is True
    assert report["no_optimizer"] is True
    assert report["no_candidate_generation"] is True
    assert report["no_test_feedback"] is True
    assert report["no_objective_evaluation"] is True
    assert report["entries"][0]["artifact_id"] == (
        "stage2_8.promoted.stage2_6_corpus_valid_weighted_clip_shared_5"
    )
    assert report["entries"][0]["status"] == "PASS"


def test_stage2_9_audit_recomputes_pass_from_committed_artifacts(tmp_path) -> None:
    from loco.coordination.promotion_replay_audit import audit_promotion_registry

    report = audit_promotion_registry(
        registry_path=STAGE2_8_REGISTRY_PATH,
        report_path=tmp_path / "promotion_replay_audit_report.json",
    )

    assert report["status"] == "PASS"
    assert report["registry_entry_count"] == 1
    assert report["artifact_fingerprint_mismatch_count"] == 0
    assert report["promotion_fingerprint_mismatch_count"] == 0
    assert report["source_candidate_fingerprint_mismatch_count"] == 0
    assert (tmp_path / "promotion_replay_audit_report.json").is_file()


def test_stage2_9_audit_detects_tampered_artifact(tmp_path) -> None:
    from loco.coordination.promotion_replay_audit import audit_promotion_registry

    registry = tmp_path / "stage2_8_registry.jsonl"
    artifact = tmp_path / "promoted.json"
    receipt = tmp_path / "receipt.json"
    original_row = json.loads(STAGE2_8_REGISTRY_PATH.read_text(encoding="utf-8"))
    shutil.copyfile(ROOT / original_row["artifact_path"], artifact)
    shutil.copyfile(ROOT / original_row["promotion_receipt_path"], receipt)

    row = dict(original_row)
    row["artifact_path"] = artifact.as_posix()
    row["promotion_receipt_path"] = receipt.as_posix()
    registry.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")

    artifact_payload = json.loads(artifact.read_text(encoding="utf-8"))
    artifact_payload["split_policy"]["no_test_feedback"] = False
    artifact.write_text(
        json.dumps(artifact_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = audit_promotion_registry(
        registry_path=registry,
        report_path=tmp_path / "tampered_report.json",
    )

    assert report["status"] == "FAIL"
    assert report["artifact_fingerprint_mismatch_count"] == 1
    assert report["promotion_fingerprint_mismatch_count"] == 1
    assert report["boundary_violation_count"] >= 1


def test_stage2_9_audit_detects_tampered_receipt(tmp_path) -> None:
    from loco.coordination.promotion_replay_audit import audit_promotion_registry

    registry = tmp_path / "stage2_8_registry.jsonl"
    artifact = tmp_path / "promoted.json"
    receipt = tmp_path / "receipt.json"
    original_row = json.loads(STAGE2_8_REGISTRY_PATH.read_text(encoding="utf-8"))
    shutil.copyfile(ROOT / original_row["artifact_path"], artifact)
    shutil.copyfile(ROOT / original_row["promotion_receipt_path"], receipt)

    row = dict(original_row)
    row["artifact_path"] = artifact.as_posix()
    row["promotion_receipt_path"] = receipt.as_posix()
    registry.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")

    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    receipt_payload["source_ast_fingerprint_sha256"] = "0" * 64
    receipt.write_text(
        json.dumps(receipt_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = audit_promotion_registry(
        registry_path=registry,
        report_path=tmp_path / "tampered_receipt_report.json",
    )

    assert report["status"] == "FAIL"
    assert report["receipt_fingerprint_mismatch_count"] == 1
    assert report["source_candidate_fingerprint_mismatch_count"] == 1
    assert report["promotion_fingerprint_mismatch_count"] == 1


def test_stage2_9_docs_and_config_state_boundaries() -> None:
    required = [
        ROOT / "configs" / "stage2_9_promotion_replay_audit.yaml",
        ROOT / "docs" / "stage2" / "stage2_9_promotion_replay_audit.md",
        ROOT / "docs" / "stage2" / "stage2_9_self_check_report.md",
        AUDIT_REPORT_PATH,
    ]
    for path in required:
        assert path.is_file(), path

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required)
    assert "promotion replay and registry audit" in combined
    assert "cold-start replay" in combined
    assert "sealed split replay audit" in combined
    assert "no LLM" in combined
    assert "no evolution" in combined
    assert "no optimizer" in combined
    assert "no candidate generation" in combined
    assert "no test feedback" in combined
    assert "no objective evaluation" in combined


def test_stage2_9_audit_does_not_import_llm_or_evolution_modules(tmp_path) -> None:
    forbidden_loaded_before = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }

    from loco.coordination.promotion_replay_audit import audit_promotion_registry

    audit_promotion_registry(
        registry_path=STAGE2_8_REGISTRY_PATH,
        report_path=tmp_path / "promotion_replay_audit_report.json",
    )

    forbidden_loaded_after = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }
    assert forbidden_loaded_after == forbidden_loaded_before

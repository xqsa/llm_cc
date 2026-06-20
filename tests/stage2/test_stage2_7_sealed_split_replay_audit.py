import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STAGE2_6_DIR = ROOT / "artifacts" / "candidates" / "stage2_6"
STAGE2_7_DIR = ROOT / "artifacts" / "candidates" / "stage2_7"
MANIFEST_PATH = STAGE2_7_DIR / "sealed_split_manifest.json"
AUDIT_REPORT_PATH = STAGE2_7_DIR / "split_replay_audit_report.json"


def test_stage2_7_sealed_split_manifest_exists_and_binds_stage2_6_logs() -> None:
    from loco.coordination.split_replay_audit import load_sealed_split_manifest

    manifest = load_sealed_split_manifest(MANIFEST_PATH)

    assert manifest["schema_version"] == "loco.sealed_split_manifest.v1"
    assert manifest["stage"] == "2.7"
    assert manifest["sealed"] is True
    assert manifest["no_llm"] is True
    assert manifest["no_evolution"] is True
    assert manifest["no_test_feedback"] is True
    assert manifest["test_split_locked"] is True
    assert manifest["allowed_candidate_log_splits"] == ["pre_stage3_schema_only"]

    logs = manifest["candidate_logs"]
    assert logs["accepted"]["path"].endswith(
        "artifacts/candidates/stage2_6/accepted_candidates.jsonl"
    )
    assert logs["rejected"]["path"].endswith(
        "artifacts/candidates/stage2_6/rejected_candidates.jsonl"
    )
    assert logs["replay_report"]["path"].endswith(
        "artifacts/candidates/stage2_6/replay_report.json"
    )
    assert len(logs["accepted"]["sha256"]) == 64
    assert len(logs["rejected"]["sha256"]) == 64
    assert len(logs["replay_report"]["sha256"]) == 64


def test_stage2_7_audit_report_is_committed_and_passes() -> None:
    report = json.loads(AUDIT_REPORT_PATH.read_text(encoding="utf-8"))

    assert report["schema_version"] == "loco.sealed_split_replay_audit.v1"
    assert report["stage"] == "2.7"
    assert report["status"] == "PASS"
    assert report["sealed_manifest_status"] == "PASS"
    assert report["replay_report_status"] == "PASS"
    assert report["accepted_count"] == 1
    assert report["rejected_count"] == 5
    assert report["file_fingerprint_mismatch_count"] == 0
    assert report["split_violation_count"] == 0
    assert report["test_feedback_violation_count"] == 0
    assert report["no_llm"] is True
    assert report["no_evolution"] is True
    assert report["no_test_feedback"] is True


def test_stage2_7_audit_recomputes_pass_from_committed_artifacts(tmp_path) -> None:
    from loco.coordination.split_replay_audit import audit_sealed_split_replay

    report = audit_sealed_split_replay(
        manifest_path=MANIFEST_PATH,
        report_path=tmp_path / "audit_report.json",
    )

    assert report["status"] == "PASS"
    assert report["file_fingerprint_mismatch_count"] == 0
    assert report["split_violation_count"] == 0
    assert report["test_feedback_violation_count"] == 0
    assert (tmp_path / "audit_report.json").is_file()


def test_stage2_7_audit_detects_tampered_candidate_log(tmp_path) -> None:
    from loco.coordination.split_replay_audit import audit_sealed_split_replay

    working = tmp_path / "stage2_7"
    working.mkdir()
    accepted = working / "accepted_candidates.jsonl"
    rejected = working / "rejected_candidates.jsonl"
    replay = working / "replay_report.json"
    manifest = working / "sealed_split_manifest.json"
    shutil.copyfile(STAGE2_6_DIR / "accepted_candidates.jsonl", accepted)
    shutil.copyfile(STAGE2_6_DIR / "rejected_candidates.jsonl", rejected)
    shutil.copyfile(STAGE2_6_DIR / "replay_report.json", replay)

    original_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    original_manifest["candidate_logs"]["accepted"]["path"] = accepted.as_posix()
    original_manifest["candidate_logs"]["rejected"]["path"] = rejected.as_posix()
    original_manifest["candidate_logs"]["replay_report"]["path"] = replay.as_posix()
    manifest.write_text(json.dumps(original_manifest, indent=2, sort_keys=True) + "\n")

    row = json.loads(accepted.read_text(encoding="utf-8"))
    row["split"] = "test"
    row["no_test_feedback"] = False
    accepted.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")

    report = audit_sealed_split_replay(
        manifest_path=manifest,
        report_path=working / "tamper_audit_report.json",
    )

    assert report["status"] == "FAIL"
    assert report["file_fingerprint_mismatch_count"] == 1
    assert report["split_violation_count"] == 1
    assert report["test_feedback_violation_count"] == 1


def test_stage2_7_docs_and_config_state_boundaries() -> None:
    required = [
        ROOT / "configs" / "stage2_7_sealed_split_replay_audit.yaml",
        ROOT / "docs" / "stage2" / "stage2_7_sealed_split_replay_audit.md",
        ROOT / "docs" / "stage2" / "stage2_7_self_check_report.md",
        MANIFEST_PATH,
        AUDIT_REPORT_PATH,
    ]
    for path in required:
        assert path.is_file(), path

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required)
    assert "sealed split replay audit" in combined
    assert "no LLM" in combined
    assert "no evolution" in combined
    assert "no optimizer" in combined
    assert "no test feedback" in combined
    assert "no candidate generation" in combined
    assert "pre_stage3_schema_only" in combined


def test_stage2_7_audit_does_not_import_llm_or_evolution_modules(tmp_path) -> None:
    forbidden_loaded_before = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }

    from loco.coordination.split_replay_audit import audit_sealed_split_replay

    audit_sealed_split_replay(
        manifest_path=MANIFEST_PATH,
        report_path=tmp_path / "audit_report.json",
    )

    forbidden_loaded_after = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }
    assert forbidden_loaded_after == forbidden_loaded_before

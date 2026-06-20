import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage3_6_freeze_candidate_pool.yaml"
OUTPUT_DIR = ROOT / "artifacts" / "candidates" / "stage3_6"
FROZEN_POOL = OUTPUT_DIR / "frozen_candidate_pool.jsonl"
POOL_MANIFEST = OUTPUT_DIR / "frozen_pool_manifest.json"
FAMILY_DESCRIPTORS = OUTPUT_DIR / "candidate_family_descriptors.json"
SEARCH_PROTOCOL = OUTPUT_DIR / "train_only_search_protocol.json"
FREEZE_REPORT = OUTPUT_DIR / "freeze_report.json"
SELF_CHECK = ROOT / "docs" / "stage3" / "stage3_6_self_check_report.md"
STAGE_DOC = ROOT / "docs" / "stage3" / "stage3_6_freeze_candidate_pool.md"
STAGE3_5_ACCEPTED = (
    ROOT / "artifacts" / "candidates" / "stage3_5" / "accepted_candidates.jsonl"
)
STAGE3_5_QUALITY = (
    ROOT / "artifacts" / "candidates" / "stage3_5" / "quality_filter_report.json"
)
STAGE3_5_DIVERSITY = (
    ROOT / "artifacts" / "candidates" / "stage3_5" / "static_diversity_audit.json"
)
STAGE3_5_COVERAGE = (
    ROOT / "artifacts" / "candidates" / "stage3_5" / "coverage_gate_report.json"
)


def test_stage3_6_freezes_quality_pass_pool_without_execution(tmp_path) -> None:
    from loco.llm.freeze_candidate_pool import freeze_stage3_6_candidate_pool

    result = freeze_stage3_6_candidate_pool(
        accepted_log_path=STAGE3_5_ACCEPTED,
        quality_report_path=STAGE3_5_QUALITY,
        diversity_report_path=STAGE3_5_DIVERSITY,
        coverage_report_path=STAGE3_5_COVERAGE,
        output_dir=tmp_path,
    )

    assert result["status"] == "PASS"
    assert result["stage"] == "3.6"
    assert result["source_stage"] == "3.5"
    assert result["frozen_candidate_count"] == 12
    assert result["quality_pass_only"] is True
    assert result["train_only_search_protocol_prepared"] is True
    assert result["no_llm_call"] is True
    assert result["no_evolution_run"] is True
    assert result["no_objective_evaluation"] is True
    assert result["no_test_feedback"] is True
    assert result["not_performance_claim"] is True

    frozen_rows = [
        json.loads(line)
        for line in (tmp_path / "frozen_candidate_pool.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    manifest = json.loads((tmp_path / "frozen_pool_manifest.json").read_text())
    descriptors = json.loads(
        (tmp_path / "candidate_family_descriptors.json").read_text()
    )
    protocol = json.loads((tmp_path / "train_only_search_protocol.json").read_text())

    assert len(frozen_rows) == 12
    assert len({row["freeze_fingerprint_sha256"] for row in frozen_rows}) == 12
    assert all(row["frozen"] is True for row in frozen_rows)
    assert all(row["split"] == "train" for row in frozen_rows)
    assert all(row["target_scope"] == "shared_variables_only" for row in frozen_rows)
    assert all(row["no_evolution_run"] is True for row in frozen_rows)
    assert all(row["no_objective_evaluation"] is True for row in frozen_rows)
    assert all(row["no_test_feedback"] is True for row in frozen_rows)
    assert all(row["not_performance_claim"] is True for row in frozen_rows)

    assert manifest["status"] == "PASS"
    assert manifest["frozen_candidate_count"] == 12
    assert manifest["coverage_gate_status"] == "PASS"
    assert manifest["quality_pass_only"] is True
    assert manifest["unique_family_count"] >= 5
    assert descriptors["family_count"] >= 5
    assert "projection+dampening" in descriptors["families"]
    assert "reweighting+repair" in descriptors["families"]
    assert protocol["status"] == "READY_FOR_STAGE4_TRAIN_ONLY_SEARCH"
    assert protocol["allowed_split"] == "train"
    assert protocol["validation_usage"] == "selection only after train search"
    assert protocol["test_usage"] == "sealed final reporting only"
    assert protocol["no_evolution_executed_in_stage3_6"] is True
    assert protocol["no_objective_evaluation_in_stage3_6"] is True


def test_stage3_6_committed_artifacts_freeze_stage3_5_quality_pass_pool() -> None:
    required = [
        CONFIG,
        FROZEN_POOL,
        POOL_MANIFEST,
        FAMILY_DESCRIPTORS,
        SEARCH_PROTOCOL,
        FREEZE_REPORT,
    ]
    for path in required:
        assert path.is_file(), path

    frozen_rows = [
        json.loads(line)
        for line in FROZEN_POOL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    manifest = json.loads(POOL_MANIFEST.read_text(encoding="utf-8"))
    descriptors = json.loads(FAMILY_DESCRIPTORS.read_text(encoding="utf-8"))
    protocol = json.loads(SEARCH_PROTOCOL.read_text(encoding="utf-8"))
    report = json.loads(FREEZE_REPORT.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["frozen_candidate_count"] == 12
    assert report["quality_pass_only"] is True
    assert manifest["coverage_gate_status"] == "PASS"
    assert manifest["source_quality_pass_count"] == 12
    assert manifest["frozen_candidate_count"] == 12
    assert manifest["unique_family_count"] >= 5
    assert len(frozen_rows) == 12
    assert len({row["candidate_id"] for row in frozen_rows}) == 12
    assert len({row["freeze_fingerprint_sha256"] for row in frozen_rows}) == 12
    assert descriptors["family_count"] >= 5
    assert protocol["status"] == "READY_FOR_STAGE4_TRAIN_ONLY_SEARCH"
    assert protocol["candidate_pool_frozen"] is True
    assert protocol["no_test_feedback"] is True
    assert protocol["not_performance_claim"] is True


def test_stage3_6_docs_state_freeze_and_protocol_boundary() -> None:
    required = [CONFIG, STAGE_DOC, SELF_CHECK]
    for path in required:
        assert path.is_file(), path

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required)
    assert "Stage 3.6" in combined
    assert "freeze" in combined
    assert "quality-pass candidate pool" in combined
    assert "train-only evolution/search protocol" in combined
    assert "READY_FOR_STAGE4_TRAIN_ONLY_SEARCH" in combined
    assert "no evolution run" in combined
    assert "no objective evaluation" in combined
    assert "no test feedback" in combined
    assert "not a performance claim" in combined

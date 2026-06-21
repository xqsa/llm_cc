import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
CONFIG = ROOT / "configs" / "stage7_6_reported_results_comparator_audit.yaml"
STAGE_DOC = ROOT / "docs" / "stage7" / "stage7_6_reported_results_comparator_audit.md"
SELF_CHECK = ROOT / "docs" / "stage7" / "stage7_6_self_check_report.md"
README = ROOT / "README.md"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_6"
REPORT = OUTPUT_DIR / "reported_results_comparator_audit_report.json"
REGISTRY = OUTPUT_DIR / "reported_results_comparator_registry.json"
ROUTE = OUTPUT_DIR / "next_route_decision.json"


def test_stage7_6_fails_red_before_implementation() -> None:
    from loco.coordination.reported_results_comparator_audit import (
        run_stage7_6_reported_results_comparator_audit,
    )

    report = run_stage7_6_reported_results_comparator_audit(
        output_dir=OUTPUT_DIR,
    )

    assert report["stage"] == "7.6"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "7.5"
    assert report["registry_size"] == 2
    assert report["direct_comparator_count"] == 1
    assert report["background_only_count"] == 1
    assert report["not_admissible_count"] == 0
    assert report["next_status"] == "READY_FOR_STAGE8_0_TRAIN_ONLY_OPERATOR_IMPROVEMENT"

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert registry["stage"] == "7.6"
    assert registry["status"] == "PASS"
    assert registry["source_stage"] == "7.5"
    assert registry["entries"][0]["source_name"] == "HCC"
    assert registry["entries"][0]["admissibility"] == "direct_comparator"
    assert registry["entries"][0]["same_setting"] is True
    assert registry["entries"][0]["reported_result_notes"]
    assert registry["entries"][1]["source_name"] == "OEDG"
    assert registry["entries"][1]["admissibility"] == "background_only"
    assert registry["entries"][1]["same_setting"] is False
    assert registry["entries"][1]["reason"] == "non_cec2013_custom_benchmark"
    assert registry["locked_rules_source"] == "Stage 7.5 same-setting comparator contract"

    route = json.loads(ROUTE.read_text(encoding="utf-8"))
    assert route["stage"] == "7.6"
    assert route["decision"] == "LOCK_REPORTED_RESULTS_COMPARATOR_AUDIT"
    assert route["next_stage"] == "Stage 8.0"
    assert route["allowed_next_work"] == "train_only_operator_improvement"
    assert route["use_reported_results_as_runtime_feedback"] is False
    assert route["sota_claim_made"] is False


def test_stage7_6_committed_artifacts_record_audit_and_boundary() -> None:
    required = [CONFIG, STAGE_DOC, SELF_CHECK]
    for path in required:
        assert path.is_file(), path

    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 7.6" in combined
    assert "Reported-Results Comparator Audit" in combined
    assert "direct_comparator" in combined
    assert "background_only" in combined
    assert "Stage 8.0" in combined
    assert "train-only operator improvement" in combined
    assert "no LLM call" in combined
    assert "no evolution/search" in combined
    assert "no AST execution" in combined
    assert "no objective evaluation" in combined
    assert "not a SOTA claim" in combined

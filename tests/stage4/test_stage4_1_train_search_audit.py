import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage4_1_train_search_audit.yaml"
STAGE4_0_DIR = ROOT / "artifacts" / "search" / "stage4_0"
OUTPUT_DIR = ROOT / "artifacts" / "search" / "stage4_1"
AUDIT_REPORT = OUTPUT_DIR / "train_search_audit_report.json"
TIE_AUDIT = OUTPUT_DIR / "tie_audit.json"
HARDENED_RULE = OUTPUT_DIR / "hardened_promotion_rule.json"
PROMOTION_DECISION = OUTPUT_DIR / "promotion_decision.json"
STAGE_DOC = ROOT / "docs" / "stage4" / "stage4_1_train_search_audit.md"
SELF_CHECK = ROOT / "docs" / "stage4" / "stage4_1_self_check_report.md"
README = ROOT / "README.md"


def test_stage4_1_audits_search_trace_and_hardens_tie_cutoff(tmp_path) -> None:
    from loco.coordination.train_search_audit import run_stage4_1_train_search_audit

    report = run_stage4_1_train_search_audit(
        search_trace_path=STAGE4_0_DIR / "search_trace.jsonl",
        promotion_candidates_path=STAGE4_0_DIR / "promotion_candidates.json",
        fe_ledger_path=STAGE4_0_DIR / "fe_ledger.json",
        search_report_path=STAGE4_0_DIR / "search_report.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "4.1"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "4.0"
    assert report["candidate_count"] == 12
    assert report["original_promotion_top_k"] == 3
    assert report["top_score_tie_count"] == 6
    assert report["boundary_tie_detected"] is True
    assert report["hardened_promotion_candidate_count"] == 6
    assert report["promotion_rule_hardened"] is True
    assert report["next_status"] == "READY_FOR_STAGE5_VALIDATION_SELECTION"
    assert report["validation_feedback_used"] is False
    assert report["test_feedback_used"] is False
    assert report["objective_evaluation_used"] is False
    assert report["ast_execution_used"] is False
    assert report["not_performance_claim"] is True

    tie_audit = json.loads((tmp_path / "tie_audit.json").read_text())
    hardened_rule = json.loads((tmp_path / "hardened_promotion_rule.json").read_text())
    decision = json.loads((tmp_path / "promotion_decision.json").read_text())

    assert tie_audit["status"] == "PASS"
    assert tie_audit["boundary_tie_detected"] is True
    assert tie_audit["cutoff_rank"] == 3
    assert tie_audit["cutoff_score"] == 1.0
    assert tie_audit["tie_group_size_at_cutoff"] == 6
    assert len(tie_audit["tie_group_candidate_ids"]) == 6
    assert len(tie_audit["dropped_by_original_top_k"]) == 3

    assert hardened_rule["status"] == "PASS"
    assert hardened_rule["rule_name"] == "include_all_candidates_tied_at_cutoff"
    assert hardened_rule["original_top_k"] == 3
    assert hardened_rule["hardened_candidate_count"] == 6
    assert hardened_rule["validation_usage"] == "selection only after train search"
    assert hardened_rule["not_performance_claim"] is True

    assert decision["status"] == "PASS"
    assert len(decision["validation_ready_candidates"]) == 6
    assert all(
        row["promotion_status"] == "VALIDATION_READY_TIE_HARDENED_NOT_FINAL"
        for row in decision["validation_ready_candidates"]
    )
    assert decision["validation_feedback_used"] is False
    assert decision["test_feedback_used"] is False


def test_stage4_1_committed_artifacts_and_docs_record_audit_boundary() -> None:
    required = [
        CONFIG,
        AUDIT_REPORT,
        TIE_AUDIT,
        HARDENED_RULE,
        PROMOTION_DECISION,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(AUDIT_REPORT.read_text(encoding="utf-8"))
    tie_audit = json.loads(TIE_AUDIT.read_text(encoding="utf-8"))
    hardened_rule = json.loads(HARDENED_RULE.read_text(encoding="utf-8"))
    decision = json.loads(PROMOTION_DECISION.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["boundary_tie_detected"] is True
    assert report["hardened_promotion_candidate_count"] == 6
    assert tie_audit["tie_group_size_at_cutoff"] == 6
    assert hardened_rule["rule_name"] == "include_all_candidates_tied_at_cutoff"
    assert len(decision["validation_ready_candidates"]) == 6

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 4.1" in combined
    assert "train search audit" in combined
    assert "promotion-rule hardening" in combined
    assert "include_all_candidates_tied_at_cutoff" in combined
    assert "no validation feedback" in combined
    assert "no test feedback" in combined
    assert "no objective evaluation" in combined
    assert "not a performance claim" in combined

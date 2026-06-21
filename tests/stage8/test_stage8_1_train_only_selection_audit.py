import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_1_train_only_selection_audit.yaml"
IMPROVEMENT_DIR = ROOT / "artifacts" / "improvement" / "stage8_0"
OUTPUT_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_1"
TRACE = IMPROVEMENT_DIR / "improvement_trace.jsonl"
IMPROVEMENT_CANDIDATES = IMPROVEMENT_DIR / "improvement_candidates.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
TIE_AUDIT = OUTPUT_DIR / "tie_audit.json"
HARDENED_RULE = OUTPUT_DIR / "hardened_selection_rule.json"
DECISION = OUTPUT_DIR / "selection_decision.json"
REPORT = OUTPUT_DIR / "selection_audit_report.json"
ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_1_train_only_selection_audit.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_1_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_1_audits_improvement_trace_and_hardens_selection_cutoff(
    tmp_path,
) -> None:
    from loco.coordination.train_only_selection_audit import (
        run_stage8_1_train_only_selection_audit,
    )

    report = run_stage8_1_train_only_selection_audit(
        improvement_trace_path=TRACE,
        improvement_candidates_path=IMPROVEMENT_CANDIDATES,
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.1"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.0"
    assert report["candidate_count"] == 12
    assert report["original_selection_top_k"] == 4
    assert report["top_score_tie_count"] == 6
    assert report["boundary_tie_detected"] is True
    assert report["hardened_selection_candidate_count"] == 6
    assert report["selection_rule_hardened"] is True
    assert report["next_status"] == "READY_FOR_STAGE8_2_TRAIN_ONLY_BOUNDARY_LOCK"
    assert report["validation_feedback_used"] is False
    assert report["test_feedback_used"] is False
    assert report["objective_evaluation_used"] is False
    assert report["benchmark_execution_used"] is False
    assert report["reported_results_used_as_runtime_feedback"] is False
    assert report["not_performance_claim"] is True

    tie_audit = json.loads((tmp_path / "tie_audit.json").read_text())
    hardened_rule = json.loads((tmp_path / "hardened_selection_rule.json").read_text())
    decision = json.loads((tmp_path / "selection_decision.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())

    assert tie_audit["status"] == "PASS"
    assert tie_audit["boundary_tie_detected"] is True
    assert tie_audit["cutoff_rank"] == 4
    assert tie_audit["cutoff_score"] == 0.775
    assert tie_audit["tie_group_size_at_cutoff"] == 6
    assert len(tie_audit["tie_group_candidate_ids"]) == 6
    assert len(tie_audit["dropped_by_original_top_k"]) == 5

    assert hardened_rule["status"] == "PASS"
    assert (
        hardened_rule["rule_name"] == "include_all_candidates_tied_at_selection_cutoff"
    )
    assert hardened_rule["original_top_k"] == 4
    assert hardened_rule["hardened_candidate_count"] == 6
    assert hardened_rule["validation_usage"] == "selection only after train improvement"
    assert hardened_rule["not_performance_claim"] is True

    assert decision["status"] == "PASS"
    assert len(decision["selection_ready_candidates"]) == 6
    assert all(
        row["selection_status"] == "TRAIN_ONLY_SELECTION_READY_NOT_FINAL"
        for row in decision["selection_ready_candidates"]
    )
    assert decision["validation_feedback_used"] is False
    assert decision["test_feedback_used"] is False

    assert ledger["status"] == "PASS"
    assert ledger["FE_total"] == 12
    assert ledger["budget_scope"] == "train_only_selection_audit"


def test_stage8_1_committed_artifacts_and_docs_record_boundaries() -> None:
    required = [
        CONFIG,
        REPORT,
        TIE_AUDIT,
        HARDENED_RULE,
        DECISION,
        FE_LEDGER,
        ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    tie_audit = json.loads(TIE_AUDIT.read_text(encoding="utf-8"))
    hardened_rule = json.loads(HARDENED_RULE.read_text(encoding="utf-8"))
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["boundary_tie_detected"] is True
    assert report["hardened_selection_candidate_count"] == 6
    assert tie_audit["tie_group_size_at_cutoff"] == 6
    assert (
        hardened_rule["rule_name"] == "include_all_candidates_tied_at_selection_cutoff"
    )
    assert len(decision["selection_ready_candidates"]) == 6
    assert ledger["FE_total"] == 12

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 8.1" in combined
    assert "selection audit" in combined
    assert "train-only selection" in combined
    assert "frozen Stage 8.0 improvement trace" in combined
    assert "no validation feedback" in combined
    assert "no test feedback" in combined
    assert "no objective evaluation" in combined
    assert "not a performance claim" in combined

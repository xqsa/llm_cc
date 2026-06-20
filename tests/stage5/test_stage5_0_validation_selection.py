import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage5_0_validation_selection.yaml"
PROMOTION_DECISION = (
    ROOT / "artifacts" / "search" / "stage4_1" / "promotion_decision.json"
)
FROZEN_POOL = (
    ROOT / "artifacts" / "candidates" / "stage3_6" / "frozen_candidate_pool.jsonl"
)
OUTPUT_DIR = ROOT / "artifacts" / "validation" / "stage5_0"
VALIDATION_TRACE = OUTPUT_DIR / "validation_trace.jsonl"
VALIDATION_METRICS = OUTPUT_DIR / "validation_metrics.json"
SELECTION_DECISION = OUTPUT_DIR / "selection_decision.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
VALIDATION_REPORT = OUTPUT_DIR / "validation_report.json"
STAGE_DOC = ROOT / "docs" / "stage5" / "stage5_0_validation_selection.md"
SELF_CHECK = ROOT / "docs" / "stage5" / "stage5_0_self_check_report.md"
README = ROOT / "README.md"


def test_stage5_0_selects_from_validation_ready_candidates_only(tmp_path) -> None:
    from loco.coordination.validation_selection import (
        run_stage5_0_validation_selection,
    )

    report = run_stage5_0_validation_selection(
        promotion_decision_path=PROMOTION_DECISION,
        frozen_pool_path=FROZEN_POOL,
        output_dir=tmp_path,
    )

    assert report["stage"] == "5.0"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "4.1"
    assert report["candidate_count"] == 6
    assert report["selection_scope"] == "validation_only_after_train_search"
    assert report["selected_candidate_status"] == "SELECTED_FOR_SEALED_TEST_NOT_FINAL"
    assert report["next_status"] == "READY_FOR_STAGE5_1_SELECTED_OPERATOR_FREEZE"
    assert report["validation_feedback_used"] is True
    assert report["test_feedback_used"] is False
    assert report["objective_evaluation_used"] is False
    assert report["llm_call_used"] is False
    assert report["new_candidate_generation_used"] is False
    assert report["prompt_revision_used"] is False
    assert report["train_search_revision_used"] is False
    assert report["promotion_rule_revision_used"] is False
    assert report["baseopt_modified"] is False
    assert report["optimizer_generation_used"] is False
    assert report["controller_scheduler_generation_used"] is False
    assert report["not_performance_claim"] is True

    trace_rows = _read_jsonl(tmp_path / "validation_trace.jsonl")
    metrics = json.loads((tmp_path / "validation_metrics.json").read_text())
    decision = json.loads((tmp_path / "selection_decision.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())

    assert len(trace_rows) == 18
    assert {row["split"] for row in trace_rows} == {"validation"}
    assert {row["selection_scope"] for row in trace_rows} == {
        "validation_only_after_train_search"
    }
    assert all(row["ast_execution_used"] is True for row in trace_rows)
    assert all(row["objective_evaluation_used"] is False for row in trace_rows)
    assert all(row["test_feedback_used"] is False for row in trace_rows)
    assert all(row["not_performance_claim"] is True for row in trace_rows)
    assert all(row["target_scope"] == "shared_variables_only" for row in trace_rows)

    assert metrics["status"] == "PASS"
    assert metrics["candidate_count"] == 6
    assert metrics["validation_state_count"] == 3
    assert len(metrics["candidate_metrics"]) == 6
    assert all(row["selection_score"] >= 0.0 for row in metrics["candidate_metrics"])
    assert metrics["selection_rule"]["primary"] == "minimize_selection_score"
    assert metrics["validation_feedback_used"] is True
    assert metrics["test_feedback_used"] is False
    assert metrics["objective_evaluation_used"] is False

    ranked = sorted(
        metrics["candidate_metrics"],
        key=lambda row: (
            row["selection_score"],
            row["FE_total"],
            row["node_count"],
            row["candidate_id"],
        ),
    )
    assert decision["selected_candidate_id"] == ranked[0]["candidate_id"]
    assert decision["selection_status"] == "SELECTED_FOR_SEALED_TEST_NOT_FINAL"
    assert decision["validation_feedback_used"] is True
    assert decision["test_feedback_used"] is False
    assert decision["not_performance_claim"] is True
    assert len(decision["selection_pool_candidate_ids"]) == 6

    assert ledger["status"] == "PASS"
    assert ledger["budget_scope"] == "validation_only_selection"
    assert ledger["FE_total"] == (
        ledger["FE_grouping"]
        + ledger["FE_proposal"]
        + ledger["FE_coordination_extra"]
        + ledger["FE_repair"]
    )
    assert ledger["FE_total"] == 18
    assert ledger["objective_evaluation_used"] is False
    assert ledger["test_feedback_used"] is False


def test_stage5_0_committed_artifacts_and_docs_record_validation_boundary() -> None:
    required = [
        CONFIG,
        VALIDATION_TRACE,
        VALIDATION_METRICS,
        SELECTION_DECISION,
        FE_LEDGER,
        VALIDATION_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(VALIDATION_REPORT.read_text(encoding="utf-8"))
    metrics = json.loads(VALIDATION_METRICS.read_text(encoding="utf-8"))
    decision = json.loads(SELECTION_DECISION.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    trace_rows = _read_jsonl(VALIDATION_TRACE)

    assert report["status"] == "PASS"
    assert report["candidate_count"] == 6
    assert report["selected_candidate_status"] == "SELECTED_FOR_SEALED_TEST_NOT_FINAL"
    assert report["validation_feedback_used"] is True
    assert report["test_feedback_used"] is False
    assert report["objective_evaluation_used"] is False
    assert report["not_performance_claim"] is True
    assert len(trace_rows) == 18
    assert metrics["candidate_count"] == 6
    assert decision["selected_candidate_id"] in decision["selection_pool_candidate_ids"]
    assert ledger["FE_total"] == 18

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 5.0" in combined
    assert "validation-only selection" in combined
    assert "tie-hardened validation-ready candidates" in combined
    assert "no LLM call" in combined
    assert "no new candidate generation" in combined
    assert "no test feedback" in combined
    assert "no objective evaluation" in combined
    assert "not a performance claim" in combined


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

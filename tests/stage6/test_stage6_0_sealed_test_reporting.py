import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage6_0_sealed_test_reporting.yaml"
PROTOCOL = (
    ROOT / "artifacts" / "selected" / "stage5_1" / "sealed_test_readiness_protocol.json"
)
SELECTED_OPERATOR = (
    ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator.json"
)
SELECTED_AST = (
    ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator_ast.json"
)
OUTPUT_DIR = ROOT / "artifacts" / "sealed_test" / "stage6_0"
SEALED_TRACE = OUTPUT_DIR / "sealed_test_trace.jsonl"
SEALED_METRICS = OUTPUT_DIR / "sealed_test_metrics.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
BOUNDARY = OUTPUT_DIR / "final_reporting_boundary.json"
SEALED_REPORT = OUTPUT_DIR / "sealed_test_report.json"
STAGE_DOC = ROOT / "docs" / "stage6" / "stage6_0_sealed_test_reporting.md"
SELF_CHECK = ROOT / "docs" / "stage6" / "stage6_0_self_check_report.md"
README = ROOT / "README.md"


EXPECTED_METHODS = {
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "selected_loco_operator",
}


def test_stage6_0_locks_protocol_and_runs_minimal_sealed_test_panel(tmp_path) -> None:
    from loco.coordination.sealed_test_reporting import (
        run_stage6_0_sealed_test_reporting,
    )

    report = run_stage6_0_sealed_test_reporting(
        readiness_protocol_path=PROTOCOL,
        selected_operator_path=SELECTED_OPERATOR,
        selected_ast_path=SELECTED_AST,
        output_dir=tmp_path,
    )

    assert report["stage"] == "6.0"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "5.1"
    assert report["selected_candidate_id"] == (
        "stage3_5_batch_1_weighted_consensus_projection"
    )
    assert report["sealed_test_reporting_executed"] is True
    assert report["method_count"] == 4
    assert set(report["method_names"]) == EXPECTED_METHODS
    assert report["sealed_state_count"] == 3
    assert report["trace_row_count"] == 12
    assert report["next_status"] == "READY_FOR_STAGE6_1_BASELINE_ABLATION_ANALYSIS"
    assert report["llm_call_used"] is False
    assert report["new_candidate_generation_used"] is False
    assert report["prompt_revision_used"] is False
    assert report["train_search_revision_used"] is False
    assert report["promotion_rule_revision_used"] is False
    assert report["validation_rule_revision_used"] is False
    assert report["test_feedback_tuning_used"] is False
    assert report["objective_evaluation_used"] is False
    assert report["baseopt_modified"] is False
    assert report["optimizer_generation_used"] is False
    assert report["controller_scheduler_generation_used"] is False
    assert report["not_sota_claim"] is True
    assert report["not_performance_claim"] is True

    trace_rows = _read_jsonl(tmp_path / "sealed_test_trace.jsonl")
    metrics = json.loads((tmp_path / "sealed_test_metrics.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "final_reporting_boundary.json").read_text())

    assert len(trace_rows) == 12
    assert {row["split"] for row in trace_rows} == {"sealed_test"}
    assert {row["method_name"] for row in trace_rows} == EXPECTED_METHODS
    assert all(row["selected_operator_reselection_used"] is False for row in trace_rows)
    assert all(row["objective_evaluation_used"] is False for row in trace_rows)
    assert all(row["test_feedback_tuning_used"] is False for row in trace_rows)
    assert all(row["target_scope"] == "shared_variables_only" for row in trace_rows)
    assert all(row["FE_proposal"] == 1 for row in trace_rows)

    assert metrics["status"] == "PASS"
    assert metrics["method_count"] == 4
    assert set(metrics["methods"]) == EXPECTED_METHODS
    assert len(metrics["method_metrics"]) == 4
    assert all(row["sealed_test_case_count"] == 3 for row in metrics["method_metrics"])
    assert metrics["selected_loco_operator_id"] == report["selected_candidate_id"]
    assert metrics["not_sota_claim"] is True

    assert ledger["status"] == "PASS"
    assert ledger["budget_scope"] == "sealed_test_final_reporting"
    assert ledger["FE_total"] == (
        ledger["FE_grouping"]
        + ledger["FE_proposal"]
        + ledger["FE_coordination_extra"]
        + ledger["FE_repair"]
    )
    assert ledger["FE_total"] == 12
    assert ledger["method_count"] == 4
    assert ledger["sealed_state_count"] == 3

    assert boundary["status"] == "PASS"
    assert boundary["legal_inputs"] == [
        "artifacts/selected/stage5_1/sealed_test_readiness_protocol.json",
        "artifacts/selected/stage5_1/selected_operator.json",
        "artifacts/selected/stage5_1/selected_operator_ast.json",
    ]
    assert boundary["forbidden_behaviors"]["llm_call"] is False
    assert boundary["forbidden_behaviors"]["new_candidate_generation"] is False
    assert boundary["forbidden_behaviors"]["test_feedback_tuning"] is False
    assert boundary["forbidden_behaviors"]["objective_evaluation"] is False
    assert boundary["claim_scope"] == "sealed-test coordination diagnostics only"


def test_stage6_0_committed_artifacts_and_docs_record_protocol_boundary() -> None:
    required = [
        CONFIG,
        SEALED_TRACE,
        SEALED_METRICS,
        FE_LEDGER,
        BOUNDARY,
        SEALED_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(SEALED_REPORT.read_text(encoding="utf-8"))
    metrics = json.loads(SEALED_METRICS.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    trace_rows = _read_jsonl(SEALED_TRACE)

    assert report["status"] == "PASS"
    assert report["method_count"] == 4
    assert set(report["method_names"]) == EXPECTED_METHODS
    assert report["not_sota_claim"] is True
    assert len(trace_rows) == 12
    assert set(metrics["methods"]) == EXPECTED_METHODS
    assert ledger["FE_total"] == 12
    assert boundary["claim_scope"] == "sealed-test coordination diagnostics only"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 6.0" in combined
    assert "sealed test final reporting" in combined
    assert "legal inputs" in combined
    assert "identity_no_coord" in combined
    assert "simple_consensus" in combined
    assert "weighted_consensus" in combined
    assert "selected_loco_operator" in combined
    assert "no LLM call" in combined
    assert "no new candidate generation" in combined
    assert "no test-feedback tuning" in combined
    assert "full FE accounting" in combined
    assert "not a SOTA claim" in combined


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

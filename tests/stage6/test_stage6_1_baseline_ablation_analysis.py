import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage6_1_baseline_ablation_analysis.yaml"
STAGE6_0_DIR = ROOT / "artifacts" / "sealed_test" / "stage6_0"
OUTPUT_DIR = ROOT / "artifacts" / "sealed_test" / "stage6_1"
COMPARISON_TABLE = OUTPUT_DIR / "baseline_comparison_table.json"
ABLATION_SUMMARY = OUTPUT_DIR / "ablation_summary.json"
FAILURE_ANALYSIS = OUTPUT_DIR / "failure_analysis.json"
CLAIM_BOUNDARY = OUTPUT_DIR / "claim_boundary.json"
ANALYSIS_REPORT = OUTPUT_DIR / "analysis_report.json"
STAGE_DOC = ROOT / "docs" / "stage6" / "stage6_1_baseline_ablation_analysis.md"
SELF_CHECK = ROOT / "docs" / "stage6" / "stage6_1_self_check_report.md"
README = ROOT / "README.md"


EXPECTED_METHODS = {
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "selected_loco_operator",
}


def test_stage6_1_analyzes_stage6_0_baselines_without_feedback_tuning(
    tmp_path,
) -> None:
    from loco.coordination.baseline_ablation_analysis import (
        run_stage6_1_baseline_ablation_analysis,
    )

    report = run_stage6_1_baseline_ablation_analysis(
        sealed_test_trace_path=STAGE6_0_DIR / "sealed_test_trace.jsonl",
        sealed_test_metrics_path=STAGE6_0_DIR / "sealed_test_metrics.json",
        fe_ledger_path=STAGE6_0_DIR / "fe_ledger.json",
        final_reporting_boundary_path=STAGE6_0_DIR / "final_reporting_boundary.json",
        sealed_test_report_path=STAGE6_0_DIR / "sealed_test_report.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "6.1"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "6.0"
    assert report["selected_candidate_id"] == (
        "stage3_5_batch_1_weighted_consensus_projection"
    )
    assert report["analysis_scope"] == "sealed-test baseline diagnostics only"
    assert report["method_count"] == 4
    assert set(report["method_names"]) == EXPECTED_METHODS
    assert report["baseline_method_count"] == 3
    assert report["selected_method_name"] == "selected_loco_operator"
    assert report["sealed_state_count"] == 3
    assert report["trace_row_count"] == 12
    assert report["comparison_table_written"] is True
    assert report["ablation_summary_written"] is True
    assert report["failure_analysis_written"] is True
    assert report["claim_boundary_written"] is True
    assert report["next_status"] == "READY_FOR_PAPER_CLAIM_POLISH_OR_STAGE7_OBJECTIVE_EVAL"

    for flag in [
        "llm_call_used",
        "new_candidate_generation_used",
        "prompt_revision_used",
        "train_search_revision_used",
        "promotion_rule_revision_used",
        "validation_rule_revision_used",
        "test_feedback_tuning_used",
        "objective_evaluation_used",
        "baseopt_modified",
        "optimizer_generation_used",
        "controller_scheduler_generation_used",
    ]:
        assert report[flag] is False
    assert report["not_sota_claim"] is True
    assert report["not_performance_claim"] is True

    comparison = json.loads((tmp_path / "baseline_comparison_table.json").read_text())
    ablation = json.loads((tmp_path / "ablation_summary.json").read_text())
    failures = json.loads((tmp_path / "failure_analysis.json").read_text())
    boundary = json.loads((tmp_path / "claim_boundary.json").read_text())

    assert comparison["stage"] == "6.1"
    assert comparison["status"] == "PASS"
    assert comparison["source_stage"] == "6.0"
    assert set(comparison["methods"]) == EXPECTED_METHODS
    assert len(comparison["rows"]) == 4
    assert all(row["sealed_test_case_count"] == 3 for row in comparison["rows"])
    assert all(row["rank_by_distance_to_best"] >= 1 for row in comparison["rows"])
    assert any(row["method_name"] == "selected_loco_operator" for row in comparison["rows"])

    selected_row = next(
        row for row in comparison["rows"] if row["method_name"] == "selected_loco_operator"
    )
    assert selected_row["is_selected_loco_operator"] is True
    assert selected_row["best_baseline_delta_distance"] == (
        selected_row["mean_normalized_distance_to_best_reward_proposal"]
        - comparison["best_baseline"][
            "mean_normalized_distance_to_best_reward_proposal"
        ]
    )

    assert ablation["stage"] == "6.1"
    assert ablation["status"] == "PASS"
    assert ablation["selected_method_name"] == "selected_loco_operator"
    assert set(ablation["baseline_methods"]) == {
        "identity_no_coord",
        "simple_consensus",
        "weighted_consensus",
    }
    assert len(ablation["pairwise_deltas_vs_selected"]) == 3
    assert ablation["lower_distance_to_best_is_better"] is True
    assert ablation["smaller_update_is_not_automatically_better"] is True
    assert ablation["not_performance_claim"] is True

    assert failures["stage"] == "6.1"
    assert failures["status"] == "PASS"
    assert failures["case_count"] == 3
    assert len(failures["cases"]) == 3
    assert all(case["selected_method_present"] is True for case in failures["cases"])
    assert all(case["winner_method_name"] in EXPECTED_METHODS for case in failures["cases"])
    assert all("selected_loco_operator" in case["method_distances"] for case in failures["cases"])
    assert failures["failure_mode_count"] >= 1
    assert failures["not_performance_claim"] is True

    assert boundary["stage"] == "6.1"
    assert boundary["status"] == "PASS"
    assert boundary["legal_inputs"] == [
        "artifacts/sealed_test/stage6_0/sealed_test_trace.jsonl",
        "artifacts/sealed_test/stage6_0/sealed_test_metrics.json",
        "artifacts/sealed_test/stage6_0/fe_ledger.json",
        "artifacts/sealed_test/stage6_0/final_reporting_boundary.json",
        "artifacts/sealed_test/stage6_0/sealed_test_report.json",
    ]
    assert boundary["claim_scope"] == "sealed-test baseline diagnostics only"
    assert boundary["forbidden_behaviors"]["test_feedback_tuning"] is False
    assert boundary["forbidden_behaviors"]["objective_evaluation"] is False
    assert boundary["allowed_next_paths"] == [
        "paper_claim_polish_from_diagnostics",
        "stage7_objective_value_eval_with_new_protocol_and_fe_accounting",
    ]


def test_stage6_1_committed_artifacts_and_docs_record_baseline_analysis() -> None:
    required = [
        CONFIG,
        COMPARISON_TABLE,
        ABLATION_SUMMARY,
        FAILURE_ANALYSIS,
        CLAIM_BOUNDARY,
        ANALYSIS_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(ANALYSIS_REPORT.read_text(encoding="utf-8"))
    comparison = json.loads(COMPARISON_TABLE.read_text(encoding="utf-8"))
    ablation = json.loads(ABLATION_SUMMARY.read_text(encoding="utf-8"))
    failures = json.loads(FAILURE_ANALYSIS.read_text(encoding="utf-8"))
    boundary = json.loads(CLAIM_BOUNDARY.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["stage"] == "6.1"
    assert report["source_stage"] == "6.0"
    assert report["method_count"] == 4
    assert set(report["method_names"]) == EXPECTED_METHODS
    assert report["not_sota_claim"] is True
    assert comparison["status"] == "PASS"
    assert len(comparison["rows"]) == 4
    assert ablation["selected_method_name"] == "selected_loco_operator"
    assert failures["case_count"] == 3
    assert boundary["claim_scope"] == "sealed-test baseline diagnostics only"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 6.1" in combined
    assert "baseline comparison" in combined
    assert "ablation" in combined
    assert "failure analysis" in combined
    assert "identity_no_coord" in combined
    assert "simple_consensus" in combined
    assert "weighted_consensus" in combined
    assert "selected_loco_operator" in combined
    assert "no LLM call" in combined
    assert "no new candidate generation" in combined
    assert "no test-feedback tuning" in combined
    assert "not a SOTA claim" in combined
    assert "not an objective-value performance claim" in combined

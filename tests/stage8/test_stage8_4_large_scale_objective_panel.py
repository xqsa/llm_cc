import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_4_large_scale_objective_panel.yaml"
PROTOCOL = ROOT / "configs" / "stage7_0_objective_eval_protocol.yaml"
STAGE8_3_DECISION = (
    ROOT
    / "artifacts"
    / "selection_audit"
    / "stage8_3"
    / "objective_utility_selection_decision.json"
)
SELECTED_OPERATOR = (
    ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator.json"
)
SELECTED_AST = (
    ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator_ast.json"
)
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_4"
OBJECTIVE_TRACE = OUTPUT_DIR / "objective_trace.jsonl"
METHOD_SUMMARY = OUTPUT_DIR / "method_summary.json"
PANEL_SUMMARY = OUTPUT_DIR / "panel_summary.json"
WIN_LOSS_REPORT = OUTPUT_DIR / "win_loss_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
ROUTE = OUTPUT_DIR / "next_route_decision.json"
PANEL_REPORT = OUTPUT_DIR / "panel_report.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_4_large_scale_objective_panel.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_4_self_check_report.md"
README = ROOT / "README.md"


EXPECTED_PANELS = {
    "synthetic_low_overlap_panel",
    "synthetic_medium_overlap_panel",
    "synthetic_high_overlap_panel",
    "synthetic_conflicting_overlap_panel",
}
EXPECTED_DIMENSIONS = {500, 1000, 2000}
EXPECTED_SEEDS = {0, 1, 2}
EXPECTED_METHODS = {
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "frozen_stage5_selected_operator",
    "stage8_3_selected_operator",
}


def test_stage8_4_runs_large_scale_objective_panel(tmp_path) -> None:
    from loco.coordination.large_scale_objective_panel import (
        run_stage8_4_large_scale_objective_panel,
    )

    report = run_stage8_4_large_scale_objective_panel(
        protocol_path=PROTOCOL,
        stage8_3_selection_decision_path=STAGE8_3_DECISION,
        frozen_stage5_operator_path=SELECTED_OPERATOR,
        frozen_stage5_ast_path=SELECTED_AST,
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.4"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.3"
    assert report["panel_scope"] == "large_scale_objective_panel_evaluation"
    assert report["selected_candidate_id"] == "stage3_5_batch_1_reweighting_repair"
    assert report["previous_frozen_candidate_id"] == (
        "stage3_5_batch_1_weighted_consensus_projection"
    )
    assert report["stage8_3_selected_operator_executed"] is True
    assert report["large_scale_panel_executed"] is True
    assert report["dimension_count"] == 3
    assert set(report["dimensions"]) == EXPECTED_DIMENSIONS
    assert report["panel_count"] == 4
    assert set(report["synthetic_panels"]) == EXPECTED_PANELS
    assert report["seed_count"] == 3
    assert set(report["seeds"]) == EXPECTED_SEEDS
    assert report["method_count"] == 6
    assert set(report["method_names"]) == EXPECTED_METHODS
    assert report["objective_step_count_per_method_per_panel"] == 3
    assert report["trace_row_count"] == 648
    assert report["baseline_comparison_made"] is True
    assert report["win_loss_report_written"] is True
    assert report["same_budget_across_methods"] is True
    assert report["objective_benchmark_run"] is False
    assert report["next_status"] == "READY_FOR_STAGE8_5_OFFICIAL_OR_PAPER_PANEL_DECISION"

    for flag in [
        "llm_call_used",
        "new_candidate_generation_used",
        "selected_operator_revision_used",
        "evolution_search_used",
        "validation_feedback_used",
        "test_feedback_used",
        "reported_results_used_as_runtime_feedback",
        "baseopt_modified",
        "optimizer_generation_used",
        "controller_scheduler_generation_used",
    ]:
        assert report[flag] is False
    assert report["not_sota_claim"] is True
    assert report["not_final_performance_claim"] is True

    trace_rows = _read_jsonl(tmp_path / "objective_trace.jsonl")
    panel_summary = json.loads((tmp_path / "panel_summary.json").read_text())
    method_summary = json.loads((tmp_path / "method_summary.json").read_text())
    win_loss = json.loads((tmp_path / "win_loss_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())

    assert len(trace_rows) == 648
    assert {row["synthetic_panel"] for row in trace_rows} == EXPECTED_PANELS
    assert {row["problem_dimension"] for row in trace_rows} == EXPECTED_DIMENSIONS
    assert {row["seed"] for row in trace_rows} == EXPECTED_SEEDS
    assert {row["method_name"] for row in trace_rows} == EXPECTED_METHODS
    assert all(row["objective_name"] == "synthetic_sphere" for row in trace_rows)
    assert all(row["split"] == "large_scale_objective_panel" for row in trace_rows)
    assert all(row["target_scope"] == "shared_variables_only" for row in trace_rows)
    assert all(row["shared_conflict_present"] is True for row in trace_rows)
    assert all(row["shared_variable_id"] == 6 for row in trace_rows)
    assert all(row["FE_global_objective"] == 1 for row in trace_rows)
    assert all(row["FE_proposal"] == 1 for row in trace_rows)
    assert all(row["FE_total"] == 2 for row in trace_rows)
    assert all(row["objective_value"] >= 0.0 for row in trace_rows)
    assert all(row["llm_call_used"] is False for row in trace_rows)
    assert all(row["new_candidate_generation_used"] is False for row in trace_rows)
    assert all(row["selected_operator_revision_used"] is False for row in trace_rows)
    assert all(row["test_feedback_used"] is False for row in trace_rows)
    assert all(
        row["reported_results_used_as_runtime_feedback"] is False
        for row in trace_rows
    )

    selected_rows = [
        row for row in trace_rows if row["method_name"] == "stage8_3_selected_operator"
    ]
    frozen_rows = [
        row
        for row in trace_rows
        if row["method_name"] == "frozen_stage5_selected_operator"
    ]
    assert len(selected_rows) == 108
    assert len(frozen_rows) == 108
    assert all(row["selected_loco_application_count"] == 1 for row in selected_rows)
    assert all(row["selected_loco_application_count"] == 1 for row in frozen_rows)
    assert all(
        row["selected_candidate_id"] == "stage3_5_batch_1_reweighting_repair"
        for row in selected_rows
    )
    assert all(
        row["previous_frozen_candidate_id"]
        == "stage3_5_batch_1_weighted_consensus_projection"
        for row in frozen_rows
    )

    assert panel_summary["stage"] == "8.4"
    assert panel_summary["status"] == "PASS"
    assert len(panel_summary["panel_rows"]) == 36
    assert all(row["method_count"] == 6 for row in panel_summary["panel_rows"])
    assert all(row["trace_row_count"] == 18 for row in panel_summary["panel_rows"])

    assert method_summary["stage"] == "8.4"
    assert method_summary["status"] == "PASS"
    assert len(method_summary["method_rows"]) == 6
    assert all(row["trace_row_count"] == 108 for row in method_summary["method_rows"])
    assert all(row["panel_count"] == 4 for row in method_summary["method_rows"])
    assert all(row["dimension_count"] == 3 for row in method_summary["method_rows"])
    assert all(row["seed_count"] == 3 for row in method_summary["method_rows"])

    assert win_loss["stage"] == "8.4"
    assert win_loss["status"] == "PASS"
    assert win_loss["comparison_case_count"] == 36
    assert win_loss["selected_operator_case_count"] == 36
    assert win_loss["vs_frozen_stage5"]["win"] >= 1
    assert (
        win_loss["vs_frozen_stage5"]["win"]
        + win_loss["vs_frozen_stage5"]["tie"]
        + win_loss["vs_frozen_stage5"]["loss"]
        == 36
    )
    assert (
        win_loss["vs_best_baseline"]["win"]
        + win_loss["vs_best_baseline"]["tie"]
        + win_loss["vs_best_baseline"]["loss"]
        == 36
    )
    assert win_loss["selected_operator_mean_final_best"] >= 0.0
    assert win_loss["selected_operator_median_final_best"] >= 0.0
    assert win_loss["not_final_performance_claim"] is True

    assert ledger["stage"] == "8.4"
    assert ledger["status"] == "PASS"
    assert ledger["FE_total"] == (
        ledger["FE_grouping"]
        + ledger["FE_proposal"]
        + ledger["FE_coordination_extra"]
        + ledger["FE_repair"]
        + ledger["FE_global_objective"]
    )
    assert ledger["FE_global_objective"] == 648
    assert ledger["FE_proposal"] == 648
    assert ledger["FE_total"] == 1296
    assert ledger["same_budget_across_methods"] is True
    assert ledger["all_extra_fe_counted"] is True

    assert boundary["stage"] == "8.4"
    assert boundary["status"] == "PASS"
    assert boundary["claim_scope"] == "large-scale objective panel utility evidence"
    assert boundary["forbidden_behaviors"]["llm_call"] is False
    assert boundary["forbidden_behaviors"]["new_candidate_generation"] is False
    assert boundary["forbidden_behaviors"]["test_feedback"] is False
    assert boundary["forbidden_behaviors"]["baseopt_modification"] is False
    assert "SOTA improvement" in boundary["forbidden_claims"]
    assert "final objective-value performance improvement" in boundary["forbidden_claims"]


def test_stage8_4_committed_artifacts_and_docs_record_panel_boundary() -> None:
    required = [
        CONFIG,
        OBJECTIVE_TRACE,
        METHOD_SUMMARY,
        PANEL_SUMMARY,
        WIN_LOSS_REPORT,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        ROUTE,
        PANEL_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(PANEL_REPORT.read_text(encoding="utf-8"))
    trace_rows = _read_jsonl(OBJECTIVE_TRACE)
    method_summary = json.loads(METHOD_SUMMARY.read_text(encoding="utf-8"))
    panel_summary = json.loads(PANEL_SUMMARY.read_text(encoding="utf-8"))
    win_loss = json.loads(WIN_LOSS_REPORT.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    boundary = json.loads(RUNTIME_BOUNDARY.read_text(encoding="utf-8"))
    route = json.loads(ROUTE.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["stage"] == "8.4"
    assert report["selected_candidate_id"] == "stage3_5_batch_1_reweighting_repair"
    assert report["trace_row_count"] == 648
    assert len(trace_rows) == 648
    assert method_summary["status"] == "PASS"
    assert panel_summary["status"] == "PASS"
    assert win_loss["status"] == "PASS"
    assert ledger["FE_total"] == 1296
    assert boundary["not_final_performance_claim"] is True
    assert route["next_stage"] == "Stage 8.5"
    assert route["use_test_feedback"] is False

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 8.4" in combined
    assert "large-scale objective panel evaluation" in combined
    assert "Current repository state: `Stage 8.4 PASS`" in combined
    assert "stage3_5_batch_1_reweighting_repair" in combined
    assert "frozen Stage 5.1 operator" in combined
    assert "win/loss report" in combined
    assert "FE_total = 1296" in combined
    assert "no LLM call" in combined
    assert "no new candidate generation" in combined
    assert "no validation feedback" in combined
    assert "no test feedback" in combined
    assert "not a final objective-value performance claim" in combined


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

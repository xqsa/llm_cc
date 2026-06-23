import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_8_conditional_policy_objective_rerun.yaml"
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
STAGE8_7_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_7"
STAGE8_7_POLICY_REPORT = STAGE8_7_DIR / "conditional_policy_report.json"
STAGE8_7_CASE_POLICY = STAGE8_7_DIR / "case_policy_table.jsonl"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_8"
OBJECTIVE_TRACE = OUTPUT_DIR / "objective_trace.jsonl"
METHOD_SUMMARY = OUTPUT_DIR / "method_summary.json"
PANEL_SUMMARY = OUTPUT_DIR / "panel_summary.json"
WIN_LOSS_REPORT = OUTPUT_DIR / "win_loss_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
ROUTE = OUTPUT_DIR / "next_route_decision.json"
PANEL_REPORT = OUTPUT_DIR / "panel_report.json"
POLICY_RUNTIME_REPORT = OUTPUT_DIR / "conditional_policy_runtime_report.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_8_conditional_policy_objective_rerun.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_8_self_check_report.md"
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
    "stage8_7_conditional_policy",
}


def test_stage8_8_runs_conditional_policy_objective_loop_rerun(tmp_path) -> None:
    from loco.coordination.conditional_policy_objective_rerun import (
        run_stage8_8_conditional_policy_objective_rerun,
    )

    report = run_stage8_8_conditional_policy_objective_rerun(
        protocol_path=PROTOCOL,
        stage8_3_selection_decision_path=STAGE8_3_DECISION,
        frozen_stage5_operator_path=SELECTED_OPERATOR,
        frozen_stage5_ast_path=SELECTED_AST,
        stage8_7_policy_report_path=STAGE8_7_POLICY_REPORT,
        stage8_7_case_policy_path=STAGE8_7_CASE_POLICY,
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.8"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.7"
    assert report["panel_scope"] == "conditional_policy_objective_loop_rerun"
    assert report["selected_candidate_id"] == "stage3_5_batch_1_reweighting_repair"
    assert report["conditional_policy_name"] == "overlap_reward_reliability_switch_v1"
    assert report["conditional_policy_executed"] is True
    assert report["objective_loop_executed"] is True
    assert report["new_objective_evaluation_used"] is True
    assert report["large_scale_panel_executed"] is True
    assert report["dimension_count"] == 3
    assert set(report["dimensions"]) == EXPECTED_DIMENSIONS
    assert report["panel_count"] == 4
    assert set(report["synthetic_panels"]) == EXPECTED_PANELS
    assert report["seed_count"] == 3
    assert set(report["seeds"]) == EXPECTED_SEEDS
    assert report["method_count"] == 7
    assert set(report["method_names"]) == EXPECTED_METHODS
    assert report["objective_step_count_per_method_per_panel"] == 3
    assert report["trace_row_count"] == 756
    assert report["baseline_comparison_made"] is True
    assert report["win_loss_report_written"] is True
    assert report["same_budget_across_methods"] is True
    assert report["objective_benchmark_run"] is False
    assert report["next_status"] == "READY_FOR_STAGE8_9_FAILURE_HONEST_INTERPRETATION"

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
    policy_runtime = json.loads(
        (tmp_path / "conditional_policy_runtime_report.json").read_text()
    )
    method_summary = json.loads((tmp_path / "method_summary.json").read_text())
    panel_summary = json.loads((tmp_path / "panel_summary.json").read_text())
    win_loss = json.loads((tmp_path / "win_loss_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert len(trace_rows) == 756
    assert {row["synthetic_panel"] for row in trace_rows} == EXPECTED_PANELS
    assert {row["problem_dimension"] for row in trace_rows} == EXPECTED_DIMENSIONS
    assert {row["seed"] for row in trace_rows} == EXPECTED_SEEDS
    assert {row["method_name"] for row in trace_rows} == EXPECTED_METHODS
    assert all(row["stage"] == "8.8" for row in trace_rows)
    assert all(row["source_stage"] == "8.7" for row in trace_rows)
    assert all(
        row["split"] == "conditional_policy_objective_rerun" for row in trace_rows
    )
    assert all(row["target_scope"] == "shared_variables_only" for row in trace_rows)
    assert all(row["shared_conflict_present"] is True for row in trace_rows)
    assert all(row["FE_global_objective"] == 1 for row in trace_rows)
    assert all(row["FE_proposal"] == 1 for row in trace_rows)
    assert all(row["FE_total"] == 2 for row in trace_rows)
    assert all(row["llm_call_used"] is False for row in trace_rows)
    assert all(row["new_candidate_generation_used"] is False for row in trace_rows)
    assert all(row["selected_operator_revision_used"] is False for row in trace_rows)
    assert all(row["test_feedback_used"] is False for row in trace_rows)

    conditional_rows = [
        row for row in trace_rows if row["method_name"] == "stage8_7_conditional_policy"
    ]
    assert len(conditional_rows) == 108
    assert all(row["is_loco_operator"] is True for row in conditional_rows)
    assert all(row["selected_loco_application_count"] == 1 for row in conditional_rows)
    assert all(
        row["method_selected_candidate_id"] == "stage3_5_batch_1_reweighting_repair"
        for row in conditional_rows
    )
    assert (
        sum(
            row["conditional_policy_action"] == "use_simple_consensus"
            for row in conditional_rows
        )
        == 36
    )
    assert (
        sum(
            row["conditional_policy_action"] == "keep_weighted_consensus"
            for row in conditional_rows
        )
        == 72
    )
    assert all(
        row["conditional_policy_name"] == "overlap_reward_reliability_switch_v1"
        for row in conditional_rows
    )

    assert policy_runtime["stage"] == "8.8"
    assert policy_runtime["status"] == "PASS"
    assert policy_runtime["conditional_policy_name"] == (
        "overlap_reward_reliability_switch_v1"
    )
    assert policy_runtime["conditional_policy_trace_row_count"] == 108
    assert policy_runtime["switch_to_simple_trace_row_count"] == 36
    assert policy_runtime["keep_weighted_trace_row_count"] == 72
    assert policy_runtime["simple_preferred_case_recovery_count"] == 12
    assert policy_runtime["weighted_sufficient_case_regression_count"] == 0
    assert (
        policy_runtime["conditional_policy_not_equivalent_to_weighted_consensus"]
        is True
    )

    assert method_summary["stage"] == "8.8"
    assert method_summary["status"] == "PASS"
    assert len(method_summary["method_rows"]) == 7
    assert all(row["trace_row_count"] == 108 for row in method_summary["method_rows"])

    assert panel_summary["stage"] == "8.8"
    assert panel_summary["status"] == "PASS"
    assert len(panel_summary["panel_rows"]) == 36
    assert all(row["method_count"] == 7 for row in panel_summary["panel_rows"])
    assert all(row["trace_row_count"] == 21 for row in panel_summary["panel_rows"])

    assert win_loss["stage"] == "8.8"
    assert win_loss["status"] == "PASS"
    assert win_loss["comparison_case_count"] == 36
    assert win_loss["conditional_policy_case_count"] == 36
    assert win_loss["conditional_vs_stage8_3_selected_operator"] == {
        "win": 12,
        "tie": 24,
        "loss": 0,
    }
    assert win_loss["conditional_vs_weighted_consensus"] == {
        "win": 12,
        "tie": 24,
        "loss": 0,
    }
    assert win_loss["conditional_vs_simple_consensus"] == {
        "win": 24,
        "tie": 12,
        "loss": 0,
    }
    assert win_loss["conditional_vs_best_baseline"] == {
        "win": 0,
        "tie": 36,
        "loss": 0,
    }
    assert win_loss["simple_preferred_case_recovery_count"] == 12
    assert win_loss["weighted_sufficient_case_regression_count"] == 0
    assert win_loss["not_final_performance_claim"] is True

    assert ledger["stage"] == "8.8"
    assert ledger["status"] == "PASS"
    assert ledger["FE_total"] == (
        ledger["FE_grouping"]
        + ledger["FE_proposal"]
        + ledger["FE_coordination_extra"]
        + ledger["FE_repair"]
        + ledger["FE_global_objective"]
    )
    assert ledger["FE_global_objective"] == 756
    assert ledger["FE_proposal"] == 756
    assert ledger["FE_total"] == 1512
    assert ledger["same_budget_across_methods"] is True
    assert ledger["all_extra_fe_counted"] is True

    assert boundary["stage"] == "8.8"
    assert boundary["status"] == "PASS"
    assert (
        boundary["claim_scope"] == "conditional policy objective-loop utility evidence"
    )
    assert boundary["objective_loop_executed"] is True
    assert boundary["new_objective_evaluation_used"] is True
    assert boundary["forbidden_behaviors"]["llm_call"] is False
    assert boundary["forbidden_behaviors"]["new_candidate_generation"] is False
    assert boundary["forbidden_behaviors"]["test_feedback"] is False
    assert boundary["forbidden_behaviors"]["baseopt_modification"] is False

    assert route["stage"] == "8.8"
    assert route["status"] == "PASS"
    assert route["decision"] == "READY_FOR_STAGE8_9_FAILURE_HONEST_INTERPRETATION"
    assert route["next_stage"] == "Stage 8.9"
    assert route["use_test_feedback"] is False


def test_stage8_8_committed_artifacts_docs_and_readme_record_objective_rerun() -> None:
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
        POLICY_RUNTIME_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(PANEL_REPORT.read_text(encoding="utf-8"))
    trace_rows = _read_jsonl(OBJECTIVE_TRACE)
    win_loss = json.loads(WIN_LOSS_REPORT.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    policy_runtime = json.loads(POLICY_RUNTIME_REPORT.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["stage"] == "8.8"
    assert report["conditional_policy_executed"] is True
    assert len(trace_rows) == 756
    assert win_loss["conditional_vs_best_baseline"] == {"win": 0, "tie": 36, "loss": 0}
    assert win_loss["conditional_vs_stage8_3_selected_operator"] == {
        "win": 12,
        "tie": 24,
        "loss": 0,
    }
    assert policy_runtime["simple_preferred_case_recovery_count"] == 12
    assert policy_runtime["weighted_sufficient_case_regression_count"] == 0
    assert ledger["FE_total"] == 1512

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 8.8" in combined
    assert "Current repository state: `Stage 8.22 PASS`" in combined
    assert (
        "Stage 8.8    objective-loop rerun for conditional policy               PASS"
        in combined
    )
    assert "objective-loop rerun for conditional policy" in combined
    assert "overlap_reward_reliability_switch_v1" in combined
    assert (
        "conditional_vs_stage8_3_selected_operator = 12 win / 24 tie / 0 loss"
        in combined
    )
    assert "conditional_vs_best_baseline = 0 win / 36 tie / 0 loss" in combined
    assert "FE_total = 1512" in combined
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

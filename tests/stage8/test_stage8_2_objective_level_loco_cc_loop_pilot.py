import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_2_objective_level_loco_cc_loop_pilot.yaml"
PROTOCOL = ROOT / "configs" / "stage7_0_objective_eval_protocol.yaml"
SELECTION_DECISION = ROOT / "artifacts" / "selection_audit" / "stage8_1" / "selection_decision.json"
SELECTED_OPERATOR = ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator.json"
SELECTED_AST = ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator_ast.json"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_2"
OBJECTIVE_TRACE = OUTPUT_DIR / "objective_trace.jsonl"
METHOD_SUMMARY = OUTPUT_DIR / "method_summary.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
PILOT_REPORT = OUTPUT_DIR / "pilot_report.json"
UTIL_TRACE = OUTPUT_DIR / "utility_trace.jsonl"
UTILITY_REPORT = OUTPUT_DIR / "utility_report.json"
ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_2_objective_level_loco_cc_loop_pilot.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_2_self_check_report.md"
README = ROOT / "README.md"
EXPECTED_METHODS = {
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "frozen_stage5_selected_operator",
    "selection_ready_stage8_operator",
}


def test_stage8_2_runs_objective_level_loco_cc_loop_pilot(tmp_path) -> None:
    from loco.coordination.objective_level_loco_cc_loop_pilot import (
        run_stage8_2_objective_level_loco_cc_loop_pilot,
    )

    report = run_stage8_2_objective_level_loco_cc_loop_pilot(
        protocol_path=PROTOCOL,
        selection_decision_path=SELECTION_DECISION,
        selected_operator_path=SELECTED_OPERATOR,
        selected_ast_path=SELECTED_AST,
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.2"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.1"
    assert report["pilot_scope"] == "objective_level_loco_cc_loop_pilot"
    assert report["problem_dimension"] == 500
    assert report["synthetic_panel"] == "synthetic_conflicting_overlap_panel"
    assert report["selected_candidate_id"] in {
        "stage3_5_batch_0_projection_dampening",
        "stage3_5_batch_1_projection_dampening",
        "stage3_5_batch_1_reweighting_repair",
        "stage3_5_batch_1_weighted_consensus_projection",
        "stage3_5_batch_2_projection_dampening",
        "stage3_5_batch_2_reweighting_repair",
    }
    assert report["objective_loop_runner_implemented"] is True
    assert report["objective_loop_pilot_executed"] is True
    assert report["objective_benchmark_run"] is False
    assert report["objective_utility_evaluated"] is True
    assert report["baseline_comparison_made"] is True
    assert report["method_count"] == 6
    assert report["objective_step_count_per_method"] == 3
    assert report["trace_row_count"] == 18
    assert report["utility_trace_row_count"] == 6
    assert report["shared_variable_count"] >= 1
    assert report["selected_operator_target_variable"] == 6
    assert report["next_status"] == "READY_FOR_STAGE8_3_TRAIN_ONLY_OR_VALIDATION_SELECTION"

    for flag in [
        "llm_call_used",
        "new_candidate_generation_used",
        "selected_operator_revision_used",
        "evolution_search_used",
        "test_feedback_tuning_used",
        "baseopt_modified",
        "optimizer_generation_used",
        "controller_scheduler_generation_used",
        "reported_results_used_as_runtime_feedback",
    ]:
        assert report[flag] is False
    assert report["not_sota_claim"] is True
    assert report["not_final_performance_claim"] is True

    trace_rows = _read_jsonl(tmp_path / "objective_trace.jsonl")
    utility_rows = _read_jsonl(tmp_path / "utility_trace.jsonl")
    summary = json.loads((tmp_path / "method_summary.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    utility_report = json.loads((tmp_path / "utility_report.json").read_text())

    assert len(trace_rows) == 18
    assert len(utility_rows) == 6
    assert {row["method_name"] for row in trace_rows} == EXPECTED_METHODS
    assert {row["objective_name"] for row in trace_rows} == {"synthetic_sphere"}
    assert {row["split"] for row in trace_rows} == {"pilot_train_like"}
    assert all(row["problem_dimension"] == 500 for row in trace_rows)
    assert all(row["shared_variable_id"] == 6 for row in trace_rows)
    assert all(row["FE_global_objective"] == 1 for row in trace_rows)
    assert all(row["FE_total"] >= 2 for row in trace_rows)
    assert all(row["objective_value"] >= 0.0 for row in trace_rows)
    assert all(row["objective_improved_or_equal"] is True for row in trace_rows)
    assert all(row["target_scope"] == "shared_variables_only" for row in trace_rows)
    assert all(row["llm_call_used"] is False for row in trace_rows)
    assert all(row["reported_results_used_as_runtime_feedback"] is False for row in trace_rows)

    assert summary["stage"] == "8.2"
    assert summary["status"] == "PASS"
    assert len(summary["method_rows"]) == 6
    assert all(row["objective_step_count"] == 3 for row in summary["method_rows"])
    assert summary["utility_scope"] == "objective_level_loco_cc_loop_pilot"
    assert summary["not_final_performance_claim"] is True

    assert ledger["stage"] == "8.2"
    assert ledger["status"] == "PASS"
    assert ledger["FE_total"] == (
        ledger["FE_grouping"]
        + ledger["FE_proposal"]
        + ledger["FE_coordination_extra"]
        + ledger["FE_repair"]
        + ledger["FE_global_objective"]
    )
    assert ledger["FE_global_objective"] == 18
    assert ledger["FE_proposal"] == 18
    assert ledger["FE_total"] == 36
    assert ledger["same_budget_across_methods"] is True
    assert ledger["cross_method_evaluations_shared"] is False

    assert boundary["stage"] == "8.2"
    assert boundary["status"] == "PASS"
    assert boundary["claim_scope"] == "objective-level utility pilot"
    assert boundary["forbidden_behaviors"]["llm_call"] is False
    assert boundary["forbidden_behaviors"]["new_candidate_generation"] is False
    assert boundary["forbidden_behaviors"]["test_feedback_tuning"] is False
    assert boundary["forbidden_behaviors"]["baseopt_modification"] is False
    assert boundary["forbidden_claims"] == [
        "SOTA improvement",
        "final objective-value performance improvement",
        "large-scale benchmark success",
    ]

    assert utility_report["stage"] == "8.2"
    assert utility_report["status"] == "PASS"
    assert utility_report["baseline_selected_candidate_id"] == "stage3_5_batch_1_weighted_consensus_projection"
    assert utility_report["utility_ready_candidate_count"] == 6
    assert utility_report["selected_loco_method_count"] == 2
    assert utility_report["selected_loco_methods"] == [
        "frozen_stage5_selected_operator",
        "selection_ready_stage8_operator",
    ]
    assert utility_report["selection_ready_improved_over_frozen_selected_operator"] is True
    assert utility_report["selection_ready_vs_frozen_selected_operator_delta"] < 0.0
    assert utility_report["selection_ready_candidate_final_best"] < utility_report["frozen_selected_operator_final_best"]
    assert utility_report["best_candidate_rank"] == 2
    assert utility_report["best_candidate_improved_or_equal_methods"] >= 1
    assert utility_report["selection_ready_candidates_used"] is True
    assert utility_report["objective_level_utility_evaluated"] is True
    assert utility_report["not_performance_claim"] is True


def test_stage8_2_committed_artifacts_and_docs_record_objective_boundary() -> None:
    required = [
        CONFIG,
        OBJECTIVE_TRACE,
        METHOD_SUMMARY,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        PILOT_REPORT,
        UTIL_TRACE,
        UTILITY_REPORT,
        ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(PILOT_REPORT.read_text(encoding="utf-8"))
    summary = json.loads(METHOD_SUMMARY.read_text(encoding="utf-8"))
    utility_report = json.loads(UTILITY_REPORT.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    boundary = json.loads(RUNTIME_BOUNDARY.read_text(encoding="utf-8"))
    trace_rows = _read_jsonl(OBJECTIVE_TRACE)
    utility_rows = _read_jsonl(UTIL_TRACE)

    assert report["status"] == "PASS"
    assert report["objective_utility_evaluated"] is True
    assert len(trace_rows) == 18
    assert len(utility_rows) == 6
    assert summary["status"] == "PASS"
    assert utility_report["status"] == "PASS"
    assert ledger["FE_global_objective"] == 18
    assert boundary["claim_scope"] == "objective-level utility pilot"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 8.2" in combined
    assert "objective-level LOCO-CC loop pilot" in combined
    assert "selection-ready operators" in combined
    assert "frozen Stage 5.1 selected operator" in combined
    assert "frozen Stage 8.1 selection-ready operator" in combined
    assert "no validation feedback" in combined
    assert "no test feedback" in combined
    assert "no objective benchmark run" in combined
    assert "not a final objective-value performance claim" in combined


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

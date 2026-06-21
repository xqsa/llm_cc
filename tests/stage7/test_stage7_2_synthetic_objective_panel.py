import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage7_2_synthetic_objective_panel.yaml"
PROTOCOL = ROOT / "configs" / "stage7_0_objective_eval_protocol.yaml"
SELECTED_OPERATOR = (
    ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator.json"
)
SELECTED_AST = (
    ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator_ast.json"
)
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_2"
OBJECTIVE_TRACE = OUTPUT_DIR / "objective_trace.jsonl"
PANEL_SUMMARY = OUTPUT_DIR / "panel_summary.json"
METHOD_SUMMARY = OUTPUT_DIR / "method_summary.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
PANEL_REPORT = OUTPUT_DIR / "panel_report.json"
STAGE_DOC = ROOT / "docs" / "stage7" / "stage7_2_synthetic_objective_panel.md"
SELF_CHECK = ROOT / "docs" / "stage7" / "stage7_2_self_check_report.md"
README = ROOT / "README.md"


EXPECTED_PANELS = {
    "synthetic_no_overlap_panel",
    "synthetic_low_overlap_panel",
    "synthetic_conflicting_overlap_panel",
    "synthetic_high_overlap_panel",
}
EXPECTED_DIMENSIONS = {500, 1000}
EXPECTED_METHODS = {
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "selected_loco_operator",
}


def test_stage7_2_runs_locked_synthetic_large_scale_objective_panel(tmp_path) -> None:
    from loco.coordination.synthetic_objective_panel import (
        run_stage7_2_synthetic_objective_panel,
    )

    report = run_stage7_2_synthetic_objective_panel(
        protocol_path=PROTOCOL,
        selected_operator_path=SELECTED_OPERATOR,
        selected_ast_path=SELECTED_AST,
        output_dir=tmp_path,
    )

    assert report["stage"] == "7.2"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "7.1"
    assert report["panel_scope"] == "synthetic_large_scale_objective_panel"
    assert report["panel_count"] == 4
    assert set(report["synthetic_panels"]) == EXPECTED_PANELS
    assert set(report["dimensions"]) == EXPECTED_DIMENSIONS
    assert report["seed_count"] == 1
    assert report["seeds"] == [0]
    assert report["method_count"] == 5
    assert set(report["method_names"]) == EXPECTED_METHODS
    assert report["objective_step_count_per_method_per_panel"] == 3
    assert report["trace_row_count"] == 120
    assert report["selected_operator_target_variable"] == 6
    assert report["same_budget_across_methods"] is True
    assert report["objective_panel_executed"] is True
    assert report["objective_benchmark_run"] is False
    assert report["next_status"] == "READY_FOR_STAGE7_3_OBJECTIVE_RESULT_POLISH"

    for flag in [
        "llm_call_used",
        "new_candidate_generation_used",
        "selected_operator_revision_used",
        "evolution_search_used",
        "test_feedback_tuning_used",
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
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())

    assert len(trace_rows) == 120
    assert {row["synthetic_panel"] for row in trace_rows} == EXPECTED_PANELS
    assert {row["problem_dimension"] for row in trace_rows} == EXPECTED_DIMENSIONS
    assert {row["seed"] for row in trace_rows} == {0}
    assert {row["method_name"] for row in trace_rows} == EXPECTED_METHODS
    assert all(row["objective_name"] == "synthetic_sphere" for row in trace_rows)
    assert all(row["split"] == "synthetic_panel" for row in trace_rows)
    assert all(row["FE_global_objective"] == 1 for row in trace_rows)
    assert all(row["FE_proposal"] == 1 for row in trace_rows)
    assert all(row["FE_total"] == 2 for row in trace_rows)
    assert all(row["objective_value"] >= 0.0 for row in trace_rows)
    assert all(row["target_scope"] == "shared_variables_only" for row in trace_rows)
    assert all(row["llm_call_used"] is False for row in trace_rows)
    assert all(row["test_feedback_tuning_used"] is False for row in trace_rows)

    no_overlap_rows = [
        row
        for row in trace_rows
        if row["synthetic_panel"] == "synthetic_no_overlap_panel"
    ]
    overlap_rows = [
        row
        for row in trace_rows
        if row["synthetic_panel"] != "synthetic_no_overlap_panel"
    ]
    assert len(no_overlap_rows) == 30
    assert all(row["shared_conflict_present"] is False for row in no_overlap_rows)
    assert all(row["shared_variable_id"] is None for row in no_overlap_rows)
    assert all(row["coordination_update_size"] == 0.0 for row in no_overlap_rows)
    assert all(
        row["distance_to_best_reward_proposal"] is None for row in no_overlap_rows
    )
    assert all(row["selected_loco_application_count"] == 0 for row in no_overlap_rows)
    assert all(row["shared_conflict_present"] is True for row in overlap_rows)
    assert all(row["shared_variable_id"] == 6 for row in overlap_rows)
    assert all(row["selected_loco_application_count"] in {0, 1} for row in overlap_rows)

    assert panel_summary["stage"] == "7.2"
    assert panel_summary["status"] == "PASS"
    assert len(panel_summary["panel_rows"]) == 8
    assert {
        (row["synthetic_panel"], row["problem_dimension"])
        for row in panel_summary["panel_rows"]
    } == {
        (panel, dimension)
        for panel in EXPECTED_PANELS
        for dimension in EXPECTED_DIMENSIONS
    }
    assert all(row["method_count"] == 5 for row in panel_summary["panel_rows"])
    assert all(row["trace_row_count"] == 15 for row in panel_summary["panel_rows"])

    assert method_summary["stage"] == "7.2"
    assert method_summary["status"] == "PASS"
    assert len(method_summary["method_rows"]) == 5
    assert all(row["trace_row_count"] == 24 for row in method_summary["method_rows"])
    assert all(
        row["FE_global_objective"] == 24 for row in method_summary["method_rows"]
    )
    assert all(row["FE_total"] == 48 for row in method_summary["method_rows"])

    assert ledger["stage"] == "7.2"
    assert ledger["status"] == "PASS"
    assert ledger["FE_total"] == (
        ledger["FE_grouping"]
        + ledger["FE_proposal"]
        + ledger["FE_coordination_extra"]
        + ledger["FE_repair"]
        + ledger["FE_global_objective"]
    )
    assert ledger["FE_global_objective"] == 120
    assert ledger["FE_proposal"] == 120
    assert ledger["FE_total"] == 240
    assert ledger["same_budget_across_methods"] is True

    assert boundary["stage"] == "7.2"
    assert boundary["status"] == "PASS"
    assert boundary["claim_scope"] == "synthetic objective-panel execution"
    assert boundary["forbidden_behaviors"]["llm_call"] is False
    assert boundary["forbidden_behaviors"]["new_candidate_generation"] is False
    assert boundary["forbidden_behaviors"]["test_feedback_tuning"] is False
    assert boundary["forbidden_behaviors"]["baseopt_modification"] is False
    assert (
        "final objective-value performance improvement" in boundary["forbidden_claims"]
    )


def test_stage7_2_committed_artifacts_docs_and_readme_record_panel_boundary() -> None:
    required = [
        CONFIG,
        OBJECTIVE_TRACE,
        PANEL_SUMMARY,
        METHOD_SUMMARY,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        PANEL_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(PANEL_REPORT.read_text(encoding="utf-8"))
    trace_rows = _read_jsonl(OBJECTIVE_TRACE)
    panel_summary = json.loads(PANEL_SUMMARY.read_text(encoding="utf-8"))
    method_summary = json.loads(METHOD_SUMMARY.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    boundary = json.loads(RUNTIME_BOUNDARY.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["stage"] == "7.2"
    assert report["trace_row_count"] == 120
    assert set(report["synthetic_panels"]) == EXPECTED_PANELS
    assert len(trace_rows) == 120
    assert panel_summary["status"] == "PASS"
    assert method_summary["status"] == "PASS"
    assert ledger["FE_global_objective"] == 120
    assert ledger["FE_total"] == 240
    assert boundary["not_final_performance_claim"] is True

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 7.2" in combined
    assert "Synthetic Large-Scale Objective Panel" in combined
    assert "Current repository state: `Stage 7.3 PASS`" in combined
    assert (
        "Stage 7.2    synthetic large-scale objective panel                 PASS"
        in combined
    )
    assert "Stage 7.3" in combined
    assert "synthetic_no_overlap_panel" in combined
    assert "synthetic_low_overlap_panel" in combined
    assert "synthetic_conflicting_overlap_panel" in combined
    assert "synthetic_high_overlap_panel" in combined
    assert "same FE budget" in combined
    assert "no LLM call" in combined
    assert "no new candidate generation" in combined
    assert "not a final objective-value performance claim" in combined


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

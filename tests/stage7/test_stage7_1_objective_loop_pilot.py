import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage7_1_objective_loop_pilot.yaml"
PROTOCOL = ROOT / "configs" / "stage7_0_objective_eval_protocol.yaml"
SELECTED_OPERATOR = (
    ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator.json"
)
SELECTED_AST = (
    ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator_ast.json"
)
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_1"
OBJECTIVE_TRACE = OUTPUT_DIR / "objective_trace.jsonl"
METHOD_SUMMARY = OUTPUT_DIR / "method_summary.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
PILOT_REPORT = OUTPUT_DIR / "pilot_report.json"
STAGE_DOC = ROOT / "docs" / "stage7" / "stage7_1_objective_loop_pilot.md"
SELF_CHECK = ROOT / "docs" / "stage7" / "stage7_1_self_check_report.md"
README = ROOT / "README.md"


EXPECTED_METHODS = {
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "selected_loco_operator",
}


def test_stage7_1_runs_minimal_loco_cc_objective_loop_pilot(tmp_path) -> None:
    from loco.coordination.objective_loop_pilot import (
        run_stage7_1_objective_loop_pilot,
    )

    report = run_stage7_1_objective_loop_pilot(
        protocol_path=PROTOCOL,
        selected_operator_path=SELECTED_OPERATOR,
        selected_ast_path=SELECTED_AST,
        output_dir=tmp_path,
    )

    assert report["stage"] == "7.1"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "7.0"
    assert report["pilot_scope"] == "minimal_loco_cc_objective_loop_pilot"
    assert report["problem_dimension"] == 500
    assert report["synthetic_panel"] == "synthetic_conflicting_overlap_panel"
    assert report["selected_candidate_id"] == (
        "stage3_5_batch_1_weighted_consensus_projection"
    )
    assert report["objective_loop_runner_implemented"] is True
    assert report["objective_loop_pilot_executed"] is True
    assert report["objective_benchmark_run"] is False
    assert report["method_count"] == 5
    assert set(report["method_names"]) == EXPECTED_METHODS
    assert report["objective_step_count_per_method"] == 3
    assert report["trace_row_count"] == 15
    assert report["shared_variable_count"] >= 1
    assert report["selected_operator_target_variable"] == 6
    assert report["next_status"] == "READY_FOR_STAGE7_2_SYNTHETIC_LARGE_SCALE_PANEL"

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
    summary = json.loads((tmp_path / "method_summary.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())

    assert len(trace_rows) == 15
    assert {row["method_name"] for row in trace_rows} == EXPECTED_METHODS
    assert {row["objective_name"] for row in trace_rows} == {"synthetic_sphere"}
    assert {row["split"] for row in trace_rows} == {"pilot_train_like"}
    assert all(row["problem_dimension"] == 500 for row in trace_rows)
    assert all(row["shared_variable_id"] == 6 for row in trace_rows)
    assert all(row["FE_global_objective"] == 1 for row in trace_rows)
    assert all(row["FE_total"] == 2 for row in trace_rows)
    assert all(row["objective_value"] >= 0.0 for row in trace_rows)
    assert all(row["objective_improved_or_equal"] is True for row in trace_rows)
    assert all(row["target_scope"] == "shared_variables_only" for row in trace_rows)
    assert all(row["llm_call_used"] is False for row in trace_rows)
    assert all(row["test_feedback_tuning_used"] is False for row in trace_rows)

    assert summary["stage"] == "7.1"
    assert summary["status"] == "PASS"
    assert set(summary["methods"]) == EXPECTED_METHODS
    assert len(summary["method_rows"]) == 5
    assert all(row["objective_step_count"] == 3 for row in summary["method_rows"])
    assert all(row["FE_global_objective"] == 3 for row in summary["method_rows"])
    assert all(row["FE_total"] == 6 for row in summary["method_rows"])
    assert summary["not_final_performance_claim"] is True

    assert ledger["stage"] == "7.1"
    assert ledger["status"] == "PASS"
    assert ledger["FE_total"] == (
        ledger["FE_grouping"]
        + ledger["FE_proposal"]
        + ledger["FE_coordination_extra"]
        + ledger["FE_repair"]
        + ledger["FE_global_objective"]
    )
    assert ledger["FE_global_objective"] == 15
    assert ledger["FE_proposal"] == 15
    assert ledger["FE_total"] == 30
    assert ledger["same_budget_across_methods"] is True
    assert ledger["cross_method_evaluations_shared"] is False

    assert boundary["stage"] == "7.1"
    assert boundary["status"] == "PASS"
    assert boundary["legal_inputs"] == [
        "configs/stage7_0_objective_eval_protocol.yaml",
        "artifacts/selected/stage5_1/selected_operator.json",
        "artifacts/selected/stage5_1/selected_operator_ast.json",
    ]
    assert boundary["claim_scope"] == "minimal objective-loop integration pilot"
    assert boundary["forbidden_behaviors"]["llm_call"] is False
    assert boundary["forbidden_behaviors"]["new_candidate_generation"] is False
    assert boundary["forbidden_behaviors"]["test_feedback_tuning"] is False
    assert boundary["forbidden_behaviors"]["baseopt_modification"] is False
    assert boundary["forbidden_claims"] == [
        "SOTA improvement",
        "final objective-value performance improvement",
        "large-scale benchmark success",
    ]


def test_stage7_1_committed_artifacts_and_docs_record_pilot_boundary() -> None:
    required = [
        CONFIG,
        OBJECTIVE_TRACE,
        METHOD_SUMMARY,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        PILOT_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(PILOT_REPORT.read_text(encoding="utf-8"))
    summary = json.loads(METHOD_SUMMARY.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    boundary = json.loads(RUNTIME_BOUNDARY.read_text(encoding="utf-8"))
    trace_rows = _read_jsonl(OBJECTIVE_TRACE)

    assert report["status"] == "PASS"
    assert report["stage"] == "7.1"
    assert set(report["method_names"]) == EXPECTED_METHODS
    assert report["objective_loop_pilot_executed"] is True
    assert report["objective_benchmark_run"] is False
    assert len(trace_rows) == 15
    assert summary["status"] == "PASS"
    assert ledger["FE_global_objective"] == 15
    assert boundary["claim_scope"] == "minimal objective-loop integration pilot"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 7.1" in combined
    assert "Minimal LOCO-CC Objective Loop Pilot" in combined
    assert "Current repository state: `Stage 7.3 PASS`" in combined
    assert "Stage 7.1    minimal LOCO-CC objective loop pilot" in combined
    assert "Stage 7.2    synthetic large-scale objective panel" in combined
    assert "Stage 7.3    objective result polish and paper-ready tables" in combined
    assert "FE_global_objective" in combined
    assert "identity_no_coord" in combined
    assert "simple_consensus" in combined
    assert "weighted_consensus" in combined
    assert "best_reward_select" in combined
    assert "selected_loco_operator" in combined
    assert "no LLM call" in combined
    assert "no new candidate generation" in combined
    assert "no test-feedback tuning" in combined
    assert "not a final objective-value performance claim" in combined


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

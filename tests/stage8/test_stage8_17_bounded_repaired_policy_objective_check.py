import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
CONFIG = ROOT / "configs" / "stage8_17_bounded_repaired_policy_objective_check.yaml"
STAGE8_16_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_16"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_17"
OBJECTIVE_TRACE = OUTPUT_DIR / "objective_trace.jsonl"
METHOD_SUMMARY = OUTPUT_DIR / "method_summary.json"
PANEL_SUMMARY = OUTPUT_DIR / "panel_summary.json"
WIN_LOSS = OUTPUT_DIR / "win_loss_report.json"
POLICY_BRANCH = OUTPUT_DIR / "policy_branch_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
OBJECTIVE_REPORT = OUTPUT_DIR / "objective_check_report.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_17_bounded_repaired_policy_objective_check.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_17_self_check_report.md"
README = ROOT / "README.md"


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_stage8_17_runs_bounded_repaired_policy_objective_check(tmp_path) -> None:
    from loco.coordination.bounded_repaired_policy_objective_check import (
        run_stage8_17_bounded_repaired_policy_objective_check,
    )

    report = run_stage8_17_bounded_repaired_policy_objective_check(
        stage8_16_alignment_report_path=STAGE8_16_DIR / "alignment_repair_report.json",
        stage8_16_feature_report_path=STAGE8_16_DIR
        / "reward_reliability_feature_report.json",
        stage8_16_branch_report_path=STAGE8_16_DIR
        / "policy_branch_alignment_report.json",
        stage8_16_fe_ledger_path=STAGE8_16_DIR / "fe_ledger.json",
        stage8_16_runtime_boundary_path=STAGE8_16_DIR / "runtime_boundary.json",
        stage8_16_next_route_path=STAGE8_16_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.17"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.16"
    assert report["check_scope"] == "bounded_train_side_repaired_policy_objective_check"
    assert report["repair_policy_name"] == "reward_trust_gated_coordination_v1"
    assert report["stage8_16_policy_executed"] is True
    assert report["objective_loop_executed"] is True
    assert report["new_objective_evaluation_used"] is True
    assert report["bounded_panel_executed"] is True
    assert report["official_cec2013_panel_run"] is False
    assert report["not_full_25_run_panel"] is True
    assert report["baseline_comparison_made"] is True
    assert report["method_count"] == 6
    assert report["case_count"] == 8
    assert report["objective_step_count_per_case"] == 4
    assert report["trace_row_count"] == 192
    assert report["FE_total"] > 0
    assert report["policy_branch_report_written"] is True
    assert report["win_loss_report_written"] is True

    assert report["repaired_vs_stage8_11_generalized_policy"]["loss"] == 0
    assert report["repaired_vs_best_reward_select"]["loss"] <= 2
    assert report["minimum_branch_coverage_count"] >= 1
    assert report["bounded_check_promising"] is True
    assert report["run_full_25_run_panel_next"] is False
    assert report["recommended_next_stage"] == "Stage 8.18"
    assert report["recommended_next_work"] == "cec2013_f13_f14_repaired_policy_resmoke"

    for flag in [
        "llm_call_used",
        "new_llm_candidate_generation_used",
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
    method_summary = json.loads((tmp_path / "method_summary.json").read_text())
    panel_summary = json.loads((tmp_path / "panel_summary.json").read_text())
    win_loss = json.loads((tmp_path / "win_loss_report.json").read_text())
    branch = json.loads((tmp_path / "policy_branch_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert len(trace_rows) == 192
    assert method_summary["stage"] == "8.17"
    assert panel_summary["case_count"] == 8
    assert win_loss["repaired_vs_stage8_11_generalized_policy"]["loss"] == 0
    assert win_loss["repaired_vs_best_reward_select"]["loss"] <= 2
    assert branch["branch_counts"]["trust_best_reward"] >= 1
    assert branch["branch_counts"]["weighted_safety"] >= 1
    assert branch["branch_counts"]["simple_safety"] >= 1
    assert branch["branch_counts"]["shrinkage_repair"] >= 1
    assert branch["all_repair_branches_exercised"] is True
    assert ledger["FE_total"] == report["FE_total"]
    assert ledger["objective_loop_executed"] is True
    assert ledger["new_objective_evaluation_used"] is True
    assert boundary["forbidden_behaviors"]["official_cec2013_panel_run"] is False
    assert boundary["forbidden_behaviors"]["selected_operator_revision"] is False
    assert route["next_stage"] == "Stage 8.18"
    assert route["run_full_25_run_panel_next"] is False


def test_stage8_17_committed_artifacts_docs_and_readme_record_objective_check() -> None:
    required = [
        CONFIG,
        OBJECTIVE_TRACE,
        METHOD_SUMMARY,
        PANEL_SUMMARY,
        WIN_LOSS,
        POLICY_BRANCH,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        OBJECTIVE_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(OBJECTIVE_REPORT.read_text(encoding="utf-8"))
    win_loss = json.loads(WIN_LOSS.read_text(encoding="utf-8"))
    branch = json.loads(POLICY_BRANCH.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))
    trace_rows = _read_jsonl(OBJECTIVE_TRACE)

    assert report["stage"] == "8.17"
    assert report["status"] == "PASS"
    assert report["bounded_check_promising"] is True
    assert win_loss["repaired_vs_stage8_11_generalized_policy"]["loss"] == 0
    assert branch["all_repair_branches_exercised"] is True
    assert ledger["FE_total"] == report["FE_total"]
    assert len(trace_rows) == report["trace_row_count"]
    assert route["next_stage"] == "Stage 8.18"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.18 PASS`" in combined
    assert "Stage 8.17   bounded train-side repaired-policy objective check" in combined
    assert "reward_trust_gated_coordination_v1" in combined
    assert "bounded_check_promising = true" in combined
    assert "not a SOTA claim" in combined
    assert "not a final objective-value performance claim" in combined

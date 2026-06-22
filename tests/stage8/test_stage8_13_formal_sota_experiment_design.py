import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_13_formal_sota_experiment_design.yaml"
STAGE8_12_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_12"
STAGE7_4_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_4"
STAGE7_5_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_5"
STAGE7_6_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_6"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_13"
DESIGN_REPORT = OUTPUT_DIR / "formal_sota_experiment_design.json"
BUDGET_LOCK = OUTPUT_DIR / "budget_lock.json"
FUNCTION_SCOPE = OUTPUT_DIR / "function_scope_lock.json"
COMPARATOR_LOCK = OUTPUT_DIR / "comparator_admissibility_lock.json"
STATISTICAL_PLAN = OUTPUT_DIR / "statistical_reporting_plan.json"
CLAIM_GATE = OUTPUT_DIR / "claim_gate.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_13_formal_sota_experiment_design.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_13_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_13_locks_formal_cec2013_sota_experiment_design(tmp_path) -> None:
    from loco.coordination.formal_sota_experiment_design import (
        run_stage8_13_formal_sota_experiment_design,
    )

    report = run_stage8_13_formal_sota_experiment_design(
        stage8_12_panel_report_path=STAGE8_12_DIR / "official_like_panel_report.json",
        stage8_12_sota_gap_path=STAGE8_12_DIR / "sota_gap_report.json",
        stage8_12_same_budget_path=STAGE8_12_DIR / "same_budget_report.json",
        stage8_12_strong_baseline_path=STAGE8_12_DIR / "strong_baseline_report.json",
        stage8_12_fe_ledger_path=STAGE8_12_DIR / "fe_ledger.json",
        stage8_12_runtime_boundary_path=STAGE8_12_DIR / "runtime_boundary.json",
        stage8_12_next_route_path=STAGE8_12_DIR / "next_route_decision.json",
        stage7_4_cec2013_decision_path=STAGE7_4_DIR / "cec2013_panel_decision.json",
        stage7_5_sota_protocol_path=STAGE7_5_DIR / "sota_protocol_report.json",
        stage7_5_claim_contract_path=STAGE7_5_DIR / "benchmark_claim_contract.json",
        stage7_6_comparator_audit_path=STAGE7_6_DIR
        / "reported_results_comparator_audit_report.json",
        stage7_6_comparator_registry_path=STAGE7_6_DIR
        / "reported_results_comparator_registry.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.13"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.12"
    assert report["design_scope"] == "formal_cec2013_sota_experiment_design_and_budget_lock"
    assert report["policy_name"] == "regime_safe_adaptive_shrinkage_v1"
    assert report["formal_experiment_design_locked"] is True
    assert report["official_cec2013_setting_locked"] is True
    assert report["benchmark_suite"] == "CEC2013_LSGO"
    assert report["dimension"] == 1000
    assert report["official_function_count"] == 15
    assert report["function_ids"] == [f"F{i}" for i in range(1, 16)]
    assert report["overlap_focus_function_ids"] == ["F13", "F14"]
    assert report["run_count"] == 25
    assert report["max_fe"] == 3000000
    assert report["checkpoints"] == [120000, 600000, 3000000]
    assert report["primary_ranking_statistic"] == "median_at_3000000_fe"
    assert report["statistics"] == ["best", "median", "worst", "mean", "std"]
    assert report["same_budget_required"] is True
    assert report["all_extra_fe_counted"] is True
    assert report["reported_results_are_audit_only"] is True
    assert report["direct_comparator_sources"] == ["HCC"]
    assert report["background_only_sources"] == ["OEDG"]
    assert report["claim_tier_locked"] == "T1_then_T2_then_T3_after_runs"
    assert report["full_sota_claim_allowed_now"] is False
    assert report["official_benchmark_claim_ready"] is False
    assert report["formal_execution_ready"] is True
    assert report["recommended_next_stage"] == "Stage 8.14"
    assert report["recommended_next_work"] == "execute_formal_cec2013_same_budget_panel"
    assert report["FE_total"] == 0
    assert report["inherited_stage8_12_FE_total"] == 0
    assert report["inherited_stage8_11_FE_total"] == 1512

    for flag in [
        "llm_call_used",
        "new_candidate_generation_used",
        "selected_operator_revision_used",
        "evolution_search_used",
        "objective_loop_executed",
        "new_objective_evaluation_used",
        "official_cec2013_panel_run",
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

    budget = json.loads((tmp_path / "budget_lock.json").read_text())
    function_scope = json.loads((tmp_path / "function_scope_lock.json").read_text())
    comparator = json.loads((tmp_path / "comparator_admissibility_lock.json").read_text())
    stats = json.loads((tmp_path / "statistical_reporting_plan.json").read_text())
    claim_gate = json.loads((tmp_path / "claim_gate.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert budget["stage"] == "8.13"
    assert budget["stage8_13_FE_total"] == 0
    assert budget["formal_run_budget_per_function_per_seed"] == 3000000
    assert budget["total_planned_official_runs"] == 375
    assert budget["total_planned_max_fe"] == 1125000000
    assert budget["same_budget_across_methods"] is True
    assert budget["all_extra_fe_counted"] is True

    assert function_scope["full_function_ids"] == [f"F{i}" for i in range(1, 16)]
    assert function_scope["overlap_focus_function_ids"] == ["F13", "F14"]
    assert function_scope["f13_f14_only_not_full_sota"] is True
    assert function_scope["full_suite_required_for_t3"] is True

    assert comparator["direct_comparator_count"] == 1
    assert comparator["direct_comparator_sources"] == ["HCC"]
    assert comparator["background_only_sources"] == ["OEDG"]
    assert comparator["reported_results_use_policy"] == "audit_only_not_runtime_feedback"
    assert comparator["same_setting_required_for_direct_comparison"] is True

    assert stats["run_count"] == 25
    assert stats["primary_ranking_statistic"] == "median_at_3000000_fe"
    assert stats["checkpoint_fe"] == [120000, 600000, 3000000]
    assert stats["paired_test_plan"] == "wilcoxon_signed_rank_on_per_function_final_values"
    assert stats["multiple_comparison_control"] == "holm_bonferroni"
    assert stats["failure_honest_reporting_required"] is True

    assert claim_gate["full_sota_claim_allowed_now"] is False
    assert claim_gate["allow_t1_overlap_focus_after_f13_f14_runs"] is True
    assert claim_gate["allow_t3_full_sota_only_after_full_suite_same_budget_runs"] is True
    assert claim_gate["blocked_claim_reason"] == "formal official CEC2013 same-budget panel not executed yet"

    assert ledger["FE_total"] == 0
    assert ledger["new_objective_evaluation_used"] is False
    assert boundary["official_cec2013_panel_run"] is False
    assert boundary["not_sota_claim"] is True
    assert route["next_stage"] == "Stage 8.14"
    assert route["run_formal_cec2013_panel_next"] is True


def test_stage8_13_committed_artifacts_docs_and_readme_record_budget_lock() -> None:
    required = [
        CONFIG,
        DESIGN_REPORT,
        BUDGET_LOCK,
        FUNCTION_SCOPE,
        COMPARATOR_LOCK,
        STATISTICAL_PLAN,
        CLAIM_GATE,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(DESIGN_REPORT.read_text(encoding="utf-8"))
    budget = json.loads(BUDGET_LOCK.read_text(encoding="utf-8"))
    scope = json.loads(FUNCTION_SCOPE.read_text(encoding="utf-8"))
    stats = json.loads(STATISTICAL_PLAN.read_text(encoding="utf-8"))
    claim = json.loads(CLAIM_GATE.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.13"
    assert report["status"] == "PASS"
    assert report["formal_experiment_design_locked"] is True
    assert budget["total_planned_official_runs"] == 375
    assert scope["full_function_ids"] == [f"F{i}" for i in range(1, 16)]
    assert stats["failure_honest_reporting_required"] is True
    assert claim["full_sota_claim_allowed_now"] is False
    assert route["next_stage"] == "Stage 8.14"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.18 PASS`" in combined
    assert "Stage 8.12   official-like / SOTA-facing evidence gate               PASS" in combined
    assert "Stage 8.13   formal CEC2013 SOTA experiment design and budget lock    PASS" in combined
    assert "Stage 8.14   CEC2013 single-run smoke and route decision             PASS" in combined
    assert "function_ids = F1..F15" in combined
    assert "run_count = 25" in combined
    assert "MaxFEs = 3000000" in combined
    assert "total_planned_official_runs = 375" in combined
    assert "official CEC2013 same-budget panel not executed yet" in combined
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined

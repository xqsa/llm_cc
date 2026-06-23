import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
STAGE8_30_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_30"
OUTPUT_DIR = ROOT / "artifacts" / "analysis" / "stage8_31"
CONFIG = ROOT / "configs" / "stage8_31_behavior_distinct_checkpoint_failure_diagnosis.yaml"
REPORT = OUTPUT_DIR / "failure_diagnosis_report.json"
OVERCORRECTION = OUTPUT_DIR / "overcorrection_diagnosis.json"
CASE_DELTA_TABLE = OUTPUT_DIR / "case_delta_table.jsonl"
BRANCH_USAGE = OUTPUT_DIR / "branch_usage_diagnosis.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = (
    ROOT
    / "docs"
    / "stage8"
    / "stage8_31_behavior_distinct_checkpoint_failure_diagnosis.md"
)
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_31_self_check_report.md"
README = ROOT / "README.md"


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_stage8_31_diagnoses_stage8_30_overcorrection_without_new_objective_work(
    tmp_path,
) -> None:
    from loco.coordination.behavior_distinct_checkpoint_failure_diagnosis import (
        run_stage8_31_behavior_distinct_checkpoint_failure_diagnosis,
    )

    report = run_stage8_31_behavior_distinct_checkpoint_failure_diagnosis(
        stage8_30_checkpoint_report_path=STAGE8_30_DIR / "checkpoint_pilot_report.json",
        stage8_30_win_loss_path=STAGE8_30_DIR / "win_loss_report.json",
        stage8_30_method_summary_path=STAGE8_30_DIR / "method_summary.json",
        stage8_30_policy_branch_path=STAGE8_30_DIR / "policy_branch_report.json",
        stage8_30_fe_ledger_path=STAGE8_30_DIR / "fe_ledger.json",
        stage8_30_runtime_boundary_path=STAGE8_30_DIR / "runtime_boundary.json",
        stage8_30_next_route_path=STAGE8_30_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.31"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.30"
    assert (
        report["diagnosis_scope"]
        == "read_only_behavior_distinct_checkpoint_failure_diagnosis"
    )
    assert report["stage8_30_checkpoint_promising"] is False
    assert report["stage8_30_behavior_policy_vs_best_reward_select"] == {
        "win": 1,
        "tie": 2,
        "loss": 3,
    }
    assert report["stage8_30_behavior_policy_vs_best_baseline"] == {
        "win": 1,
        "tie": 2,
        "loss": 3,
    }
    assert report["overcorrection_confirmed"] is True
    assert report["overcorrection_type"] == "contribution_leader_break_overcorrection"
    assert report["policy_branch_collapse_confirmed"] is True
    assert report["best_reward_favored_loss_case_count"] == 3
    assert report["best_reward_favored_loss_case_count"] > report["win_case_count"]
    assert report["owner_proposal_select_count"] == 3600
    assert report["shrinkage_repair_count"] == 3600
    assert report["contribution_leader_count"] == 7200
    assert report["break_count"] == 7200
    assert report["trust_best_reward_count"] == 0
    assert report["preserve_count"] == 0
    assert report["best_reward_group_count"] == 0
    assert report["formal_25_run_recommended_now"] is False
    assert report["recommended_next_stage"] == "Stage 8.32"
    assert (
        report["recommended_next_work"]
        == "design_overcorrection_guard_or_conditional_owner_trust_repair"
    )
    assert report["FE_total"] == 0
    assert report["inherited_stage8_30_FE_total"] == 72030
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False

    for flag in [
        "llm_call_used",
        "new_candidate_generation_used",
        "new_llm_strategy_generation_used",
        "selected_policy_revision_used",
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

    overcorrection = json.loads((tmp_path / "overcorrection_diagnosis.json").read_text())
    branch = json.loads((tmp_path / "branch_usage_diagnosis.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())
    case_rows = _read_jsonl(tmp_path / "case_delta_table.jsonl")

    assert overcorrection["overcorrection_confirmed"] is True
    assert overcorrection["diagnostic_basis"]["branch_collapse"] is True
    assert overcorrection["diagnostic_basis"]["best_reward_trust_absent"] is True
    assert branch["contribution_leader_share"] == 1.0
    assert branch["break_share"] == 1.0
    assert branch["trust_best_reward_share"] == 0.0
    assert branch["preserve_share"] == 0.0
    assert ledger["FE_total"] == 0
    assert ledger["inherited_stage8_30_FE_total"] == 72030
    assert ledger["objective_loop_executed"] is False
    assert boundary["claim_scope"] == "Stage 8.30 failure diagnosis only"
    assert boundary["forbidden_behaviors"]["llm_call"] is False
    assert boundary["forbidden_behaviors"]["selected_policy_revision"] is False
    assert route["decision"] == "CONFIRM_OVERCORRECTION_DIAGNOSE_BEFORE_REPAIR"
    assert route["run_full_25_run_panel_next"] is False
    assert route["run_new_objective_next"] is False
    assert route["sota_claim_made"] is False
    assert len(case_rows) == 6
    assert sum(row["best_reward_favored_loss_case"] for row in case_rows) == 3


def test_stage8_31_committed_artifacts_docs_and_readme_record_diagnosis() -> None:
    required = [
        CONFIG,
        REPORT,
        OVERCORRECTION,
        CASE_DELTA_TABLE,
        BRANCH_USAGE,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    overcorrection = json.loads(OVERCORRECTION.read_text(encoding="utf-8"))
    branch = json.loads(BRANCH_USAGE.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))
    case_rows = _read_jsonl(CASE_DELTA_TABLE)

    assert report["stage"] == "8.31"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.30"
    assert report["overcorrection_confirmed"] is True
    assert report["policy_branch_collapse_confirmed"] is True
    assert report["formal_25_run_recommended_now"] is False
    assert overcorrection["overcorrection_type"] == "contribution_leader_break_overcorrection"
    assert branch["policy_trace_row_count"] == 7200
    assert branch["contribution_leader_count"] == 7200
    assert branch["break_count"] == 7200
    assert branch["trust_best_reward_count"] == 0
    assert branch["preserve_count"] == 0
    assert ledger["FE_total"] == 0
    assert ledger["new_objective_evaluation_used"] is False
    assert route["next_stage"] == "Stage 8.32"
    assert len(case_rows) == report["comparison_case_count"]

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.32 PASS`" in combined
    assert "Stage 8.31   failure-honest behavior-distinct checkpoint diagnosis" in combined
    assert "Stage 8.32   overcorrection guard / conditional owner-trust repair" in combined
    assert "overcorrection_confirmed = true" in combined
    assert "contribution_leader + break" in combined
    assert "trust_best_reward_count = 0" in combined
    assert "formal_25_run_recommended_now = false" in combined
    assert "not a SOTA claim" in combined
    assert "not a final objective-value performance claim" in combined

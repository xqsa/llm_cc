import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
STAGE8_34_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_34"
OUTPUT_DIR = ROOT / "artifacts" / "analysis" / "stage8_35"
CONFIG = ROOT / "configs" / "stage8_35_bounded_guarded_checkpoint_diagnosis.yaml"
REPORT = OUTPUT_DIR / "bounded_guarded_checkpoint_diagnosis_report.json"
CAUSES = OUTPUT_DIR / "one_of_six_less_loss_cause_report.json"
CASE_TABLE = OUTPUT_DIR / "case_diagnosis_table.jsonl"
BRANCH = OUTPUT_DIR / "guard_branch_diagnosis.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = (
    ROOT / "docs" / "stage8" / "stage8_35_bounded_guarded_checkpoint_diagnosis.md"
)
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_35_self_check_report.md"
README = ROOT / "README.md"


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_stage8_35_explains_why_stage8_34_only_gets_one_of_six_less_loss(
    tmp_path,
) -> None:
    from loco.coordination.bounded_guarded_checkpoint_diagnosis import (
        run_stage8_35_bounded_guarded_checkpoint_diagnosis,
    )

    report = run_stage8_35_bounded_guarded_checkpoint_diagnosis(
        stage8_34_checkpoint_report_path=STAGE8_34_DIR
        / "bounded_guarded_checkpoint_report.json",
        stage8_34_case_table_path=STAGE8_34_DIR / "guarded_case_delta_table.jsonl",
        stage8_34_win_loss_path=STAGE8_34_DIR / "win_loss_report.json",
        stage8_34_branch_report_path=STAGE8_34_DIR
        / "guarded_policy_branch_report.json",
        stage8_34_fe_ledger_path=STAGE8_34_DIR / "fe_ledger.json",
        stage8_34_runtime_boundary_path=STAGE8_34_DIR / "runtime_boundary.json",
        stage8_34_next_route_path=STAGE8_34_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.35"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.34"
    assert (
        report["diagnosis_scope"]
        == "failure_honest_bounded_guarded_checkpoint_diagnosis"
    )
    assert report["stage8_34_less_loss_case_count"] == 1
    assert report["stage8_34_comparison_case_count"] == 6
    assert report["stage8_34_less_loss_rate"] == 1 / 6
    assert report["stage8_34_checkpoint_promising"] is False
    assert report["root_cause_summary"] == (
        "guard fixes only the reliable-best-reward overcorrection case; most "
        "cases either remain tied or still need objective-level proposal repair"
    )
    assert report["primary_limitation"] == "limited_guard_applicability"
    assert report["secondary_limitation"] == "no_new_proposal_or_optimizer_signal"
    assert report["less_loss_case_explained"] is True
    assert report["remaining_loss_cases_explained"] is True
    assert report["formal_25_run_recommended_now"] is False
    assert report["recommended_next_stage"] == "Stage 8.36"
    assert report["recommended_next_work"] == (
        "proposal_quality_or_best_reward_reliability_repair_before_formal_panel"
    )
    assert report["FE_total"] == 0
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["cec_checkpoint_executed"] is False

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

    causes = json.loads((tmp_path / "one_of_six_less_loss_cause_report.json").read_text())
    case_rows = _read_jsonl(tmp_path / "case_diagnosis_table.jsonl")
    branch = json.loads((tmp_path / "guard_branch_diagnosis.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert causes["less_loss_case_count"] == 1
    assert causes["total_loss_case_count"] == 3
    assert causes["remaining_loss_case_count"] == 2
    assert causes["unchanged_case_count"] == 5
    assert causes["dominant_cause"] == "limited_guard_applicability"
    assert causes["formal_25_run_recommended_now"] is False
    assert len(case_rows) == 6
    assert sum(row["diagnosis_label"] == "explained_less_loss" for row in case_rows) == 1
    assert sum(row["diagnosis_label"] == "remaining_loss" for row in case_rows) == 2
    assert branch["trust_best_reward_share"] == 1 / 6
    assert branch["owner_proposal_select_share"] == 2 / 6
    assert ledger["FE_total"] == 0
    assert boundary["claim_scope"] == "Stage 8.34 failure diagnosis only"
    assert route["next_stage"] == "Stage 8.36"
    assert route["run_full_25_run_panel_next"] is False


def test_stage8_35_committed_artifacts_docs_and_readme_record_diagnosis() -> None:
    required = [
        CONFIG,
        REPORT,
        CAUSES,
        CASE_TABLE,
        BRANCH,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    causes = json.loads(CAUSES.read_text(encoding="utf-8"))
    branch = json.loads(BRANCH.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))
    case_rows = _read_jsonl(CASE_TABLE)

    assert report["stage"] == "8.35"
    assert report["status"] == "PASS"
    assert report["stage8_34_less_loss_case_count"] == 1
    assert causes["dominant_cause"] == "limited_guard_applicability"
    assert branch["trust_best_reward_count"] == 1
    assert ledger["FE_total"] == 0
    assert route["next_stage"] == "Stage 8.36"
    assert len(case_rows) == report["stage8_34_comparison_case_count"]

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.35 PASS`" in combined
    assert "Stage 8.35   failure-honest bounded guarded checkpoint diagnosis" in combined
    assert "1/6" in combined
    assert "limited_guard_applicability" in combined
    assert "formal_25_run_recommended_now = false" in combined
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined

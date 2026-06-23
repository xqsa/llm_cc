import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
STAGE8_30_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_30"
STAGE8_31_DIR = ROOT / "artifacts" / "analysis" / "stage8_31"
STAGE8_32_DIR = ROOT / "artifacts" / "analysis" / "stage8_32"
STAGE8_33_DIR = ROOT / "artifacts" / "analysis" / "stage8_33"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_34"
CONFIG = ROOT / "configs" / "stage8_34_bounded_guarded_policy_checkpoint.yaml"
REPORT = OUTPUT_DIR / "bounded_guarded_checkpoint_report.json"
CASE_TABLE = OUTPUT_DIR / "guarded_case_delta_table.jsonl"
WIN_LOSS = OUTPUT_DIR / "win_loss_report.json"
BRANCH = OUTPUT_DIR / "guarded_policy_branch_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_34_bounded_guarded_policy_checkpoint.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_34_self_check_report.md"
README = ROOT / "README.md"


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_stage8_34_replays_guarded_checkpoint_and_records_one_of_six_less_loss(
    tmp_path,
) -> None:
    from loco.coordination.bounded_guarded_policy_checkpoint import (
        run_stage8_34_bounded_guarded_policy_checkpoint,
    )

    report = run_stage8_34_bounded_guarded_policy_checkpoint(
        stage8_30_win_loss_path=STAGE8_30_DIR / "win_loss_report.json",
        stage8_31_case_delta_table_path=STAGE8_31_DIR / "case_delta_table.jsonl",
        stage8_32_policy_payload_path=STAGE8_32_DIR / "guarded_policy_payload.json",
        stage8_33_sanity_report_path=STAGE8_33_DIR
        / "static_guard_sanity_report.json",
        stage8_33_runtime_boundary_path=STAGE8_33_DIR / "runtime_boundary.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.34"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.33"
    assert report["checkpoint_scope"] == "bounded_guarded_policy_checkpoint_replay"
    assert report["repair_policy_id"] == "stage8_32_guarded_owner_trust_repair_v1"
    assert report["comparison_case_count"] == 6
    assert report["less_loss_case_count"] == 1
    assert report["less_loss_rate"] == 1 / 6
    assert report["unchanged_case_count"] == 5
    assert report["guarded_policy_vs_best_reward_select"] == {
        "win": 1,
        "tie": 2,
        "loss": 3,
    }
    assert report["guarded_policy_vs_best_baseline"] == {
        "win": 1,
        "tie": 2,
        "loss": 3,
    }
    assert report["checkpoint_promising"] is False
    assert report["formal_25_run_recommended_now"] is False
    assert report["recommended_next_stage"] == "Stage 8.35"
    assert report["recommended_next_work"] == (
        "failure_honest_bounded_guarded_checkpoint_diagnosis"
    )
    assert report["FE_total"] == 0
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["cec_checkpoint_executed"] is False
    assert report["not_full_25_run_panel"] is True

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

    case_rows = _read_jsonl(tmp_path / "guarded_case_delta_table.jsonl")
    win_loss = json.loads((tmp_path / "win_loss_report.json").read_text())
    branch = json.loads((tmp_path / "guarded_policy_branch_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert len(case_rows) == 6
    assert sum(row["less_loss_vs_stage8_30_behavior"] for row in case_rows) == 1
    less_loss_rows = [
        row for row in case_rows if row["less_loss_vs_stage8_30_behavior"]
    ]
    assert less_loss_rows[0]["function_id"] == "F13"
    assert less_loss_rows[0]["seed"] == 0
    assert less_loss_rows[0]["guarded_vs_best_reward_select_result"] == "loss"
    assert less_loss_rows[0]["guarded_vs_best_reward_select_delta"] < less_loss_rows[0][
        "stage8_30_behavior_vs_best_reward_select_delta"
    ]
    assert win_loss["comparison_case_count"] == 6
    assert win_loss["less_loss_case_count"] == 1
    assert win_loss["guarded_policy_vs_best_reward_select"]["loss"] == 3
    assert branch["guard_action_counts"]["trust_best_reward"] == 1
    assert branch["guard_action_counts"]["owner_proposal_select"] == 2
    assert branch["guard_action_counts"]["unchanged_or_inherited"] == 3
    assert ledger["FE_total"] == 0
    assert boundary["claim_scope"] == "bounded guarded-policy checkpoint replay only"
    assert route["next_stage"] == "Stage 8.35"
    assert route["run_full_25_run_panel_next"] is False


def test_stage8_34_committed_artifacts_docs_and_readme_record_checkpoint() -> None:
    required = [
        CONFIG,
        REPORT,
        CASE_TABLE,
        WIN_LOSS,
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
    win_loss = json.loads(WIN_LOSS.read_text(encoding="utf-8"))
    branch = json.loads(BRANCH.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))
    case_rows = _read_jsonl(CASE_TABLE)

    assert report["stage"] == "8.34"
    assert report["status"] == "PASS"
    assert report["less_loss_case_count"] == 1
    assert report["comparison_case_count"] == 6
    assert win_loss["less_loss_case_count"] == 1
    assert branch["guard_action_counts"]["trust_best_reward"] == 1
    assert ledger["FE_total"] == 0
    assert route["next_stage"] == "Stage 8.35"
    assert len(case_rows) == report["comparison_case_count"]

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.35 PASS`" in combined
    assert "Stage 8.34   bounded guarded-policy checkpoint" in combined
    assert "less_loss_case_count = 1" in combined
    assert "comparison_case_count = 6" in combined
    assert "checkpoint_promising = false" in combined
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined

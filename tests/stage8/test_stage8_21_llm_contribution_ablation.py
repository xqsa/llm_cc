import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
STAGE8_20_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_20"
OUTPUT_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_21"
CONFIG = ROOT / "configs" / "stage8_21_llm_contribution_ablation.yaml"
REPORT = OUTPUT_DIR / "llm_contribution_ablation_report.json"
POOL_SUMMARY = OUTPUT_DIR / "pool_summary.json"
POOL_CANDIDATE_TABLE = OUTPUT_DIR / "pool_candidate_table.jsonl"
WIN_LOSS_REPORT = OUTPUT_DIR / "win_loss_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_21_llm_contribution_ablation.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_21_self_check_report.md"
README = ROOT / "README.md"


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_stage8_21_runs_same_evaluator_pool_ablation_without_new_llm_calls(tmp_path) -> None:
    from loco.coordination.llm_contribution_ablation import (
        run_stage8_21_llm_contribution_ablation,
    )

    report = run_stage8_21_llm_contribution_ablation(
        stage8_20_report_path=STAGE8_20_DIR / "llm_reflective_search_report.json",
        stage8_20_accepted_candidates_path=STAGE8_20_DIR / "accepted_candidates.jsonl",
        stage8_20_evaluator_report_path=STAGE8_20_DIR / "candidate_evaluator_report.json",
        stage8_20_fe_ledger_path=STAGE8_20_DIR / "fe_ledger.json",
        stage8_20_runtime_boundary_path=STAGE8_20_DIR / "runtime_boundary.json",
        stage8_20_next_route_path=STAGE8_20_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.21"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.20"
    assert report["ablation_scope"] == "llm_vs_non_llm_contribution_ablation"
    assert report["stage8_20_selected_candidate_id"] == "stage8_20_round_candidate_8"
    assert report["llm_reflective_pool_evaluated"] is True
    assert report["non_llm_pools_evaluated"] is True
    assert report["same_train_side_evaluator_used"] is True
    assert report["pool_count"] >= 5
    assert report["llm_pool_best_rank"] == 1
    assert report["llm_pool_beats_non_llm_pool_best"] is True
    assert report["llm_pool_non_degenerate_candidate_count"] > 0
    assert report["llm_pool_train_objective_loss_count_vs_best_reward"] == 0
    assert report["llm_pool_train_objective_win_count_vs_best_reward"] >= 3
    assert report["new_llm_candidate_generation_used"] is False
    assert report["llm_call_used"] is False
    assert report["fake_llm_candidates_used"] is False
    assert report["validation_feedback_used"] is False
    assert report["test_feedback_used"] is False
    assert report["reported_results_used_as_runtime_feedback"] is False
    assert report["baseopt_modified"] is False
    assert report["not_sota_claim"] is True
    assert report["not_final_performance_claim"] is True

    pool_summary = json.loads((tmp_path / "pool_summary.json").read_text())
    candidate_rows = _jsonl(tmp_path / "pool_candidate_table.jsonl")
    win_loss = json.loads((tmp_path / "win_loss_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    pool_ids = {row["pool_id"] for row in pool_summary["pool_rows"]}
    assert {
        "llm_reflective_pool",
        "hand_designed_pool",
        "random_mutation_pool",
        "literature_inspired_pool",
        "stage8_16_human_repair_policy",
    }.issubset(pool_ids)
    assert any(row["origin"] == "llm_reflective_generated" for row in candidate_rows)
    assert any(row["origin"] != "llm_reflective_generated" for row in candidate_rows)
    assert win_loss["llm_reflective_pool"]["wins_vs_non_llm_pool_best"] >= 1
    assert ledger["FE_total"] == report["FE_total"]
    assert ledger["llm_call_used"] is False
    assert boundary["forbidden_behaviors"]["new_llm_candidate_generation"] is False
    assert route["next_stage"] == "Stage 8.22"
    assert route["allowed_next_work"] == "freeze_llm_origin_beat_best_reward_policy"


def test_stage8_21_committed_artifacts_docs_and_readme_record_contribution_ablation() -> None:
    required = [
        CONFIG,
        REPORT,
        POOL_SUMMARY,
        POOL_CANDIDATE_TABLE,
        WIN_LOSS_REPORT,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    boundary = json.loads(RUNTIME_BOUNDARY.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.21"
    assert report["status"] == "PASS"
    assert report["llm_pool_best_rank"] == 1
    assert report["llm_pool_beats_non_llm_pool_best"] is True
    assert ledger["FE_total"] == report["FE_total"]
    assert boundary["not_sota_claim"] is True
    assert boundary["not_final_performance_claim"] is True
    assert route["next_stage"] == "Stage 8.22"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.21 PASS`" in combined
    assert "Stage 8.21   LLM vs non-LLM contribution ablation" in combined
    assert "Stage 8.22" in combined
    assert "not a SOTA claim" in combined
    assert "not a final objective-value performance claim" in combined

import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
STAGE8_27_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_27"
OUTPUT_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_28"
CONFIG = ROOT / "configs" / "stage8_28_llm_vs_non_llm_ownership_strategy_ablation.yaml"
REPORT = OUTPUT_DIR / "llm_vs_non_llm_ownership_ablation_report.json"
POOL_SUMMARY = OUTPUT_DIR / "pool_summary.json"
CANDIDATE_TABLE = OUTPUT_DIR / "pool_candidate_table.jsonl"
WIN_LOSS = OUTPUT_DIR / "pool_win_loss_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_28_llm_vs_non_llm_ownership_strategy_ablation.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_28_self_check_report.md"
README = ROOT / "README.md"


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_stage8_28_compares_llm_pool_against_non_llm_pools(tmp_path) -> None:
    from loco.coordination.llm_vs_non_llm_ownership_strategy_ablation import (
        run_stage8_28_llm_vs_non_llm_ownership_strategy_ablation,
    )

    report = run_stage8_28_llm_vs_non_llm_ownership_strategy_ablation(
        stage8_27_report_path=STAGE8_27_DIR
        / "llm_reflective_ownership_strategy_search_report.json",
        stage8_27_accepted_strategies_path=STAGE8_27_DIR / "accepted_strategies.jsonl",
        stage8_27_evaluator_path=STAGE8_27_DIR / "strategy_evaluator_report.json",
        stage8_27_fe_ledger_path=STAGE8_27_DIR / "fe_ledger.json",
        stage8_27_runtime_boundary_path=STAGE8_27_DIR / "runtime_boundary.json",
        stage8_27_next_route_path=STAGE8_27_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.28"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.27"
    assert report["llm_vs_non_llm_ablation_executed"] is True
    assert report["pool_count"] == 4
    assert report["llm_pool_best_rank"] == 1
    assert report["llm_pool_beats_non_llm_pool_best"] is True
    assert report["best_pool_name"] == "llm_reflective_pool"
    assert report["selected_strategy_id"] == "stage8_27_1"
    assert report["selected_strategy_origin"] == "llm_reflective_generated"
    assert report["selected_strategy_not_equivalent_to_best_reward_select"] is True
    assert report["non_trust_branch_exercised"] is True
    assert report["ownership_or_linkage_decision_exercised"] is True
    assert report["FE_total"] == 0
    assert report["llm_call_used"] is False
    assert report["new_llm_strategy_generation_used"] is False
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["not_sota_claim"] is True
    assert report["not_final_performance_claim"] is True
    assert report["recommended_next_stage"] == "Stage 8.29"

    required = [
        "llm_vs_non_llm_ownership_ablation_report.json",
        "pool_summary.json",
        "pool_candidate_table.jsonl",
        "pool_win_loss_report.json",
        "fe_ledger.json",
        "runtime_boundary.json",
        "next_route_decision.json",
    ]
    for filename in required:
        assert (tmp_path / filename).is_file(), filename

    pool_summary = json.loads((tmp_path / "pool_summary.json").read_text())
    win_loss = json.loads((tmp_path / "pool_win_loss_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())
    rows = _jsonl(tmp_path / "pool_candidate_table.jsonl")

    assert pool_summary["pool_names"] == [
        "llm_reflective_pool",
        "hand_designed_pool",
        "random_mutation_pool",
        "literature_inspired_pool",
    ]
    assert pool_summary["llm_pool_best_rank"] == 1
    assert pool_summary["llm_pool_beats_non_llm_pool_best"] is True
    assert win_loss["llm_pool_vs_best_non_llm_pool"] == {"win": 1, "tie": 0, "loss": 0}
    assert any(row["pool_name"] == "llm_reflective_pool" for row in rows)
    assert any(row["pool_name"] == "literature_inspired_pool" for row in rows)
    assert ledger["FE_total"] == 0
    assert boundary["llm_call_used"] is False
    assert route["next_stage"] == "Stage 8.29"


def test_stage8_28_committed_artifacts_docs_and_readme_record_ablation() -> None:
    required = [
        CONFIG,
        REPORT,
        POOL_SUMMARY,
        CANDIDATE_TABLE,
        WIN_LOSS,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    pool_summary = json.loads(POOL_SUMMARY.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))
    rows = _jsonl(CANDIDATE_TABLE)

    assert report["stage"] == "8.28"
    assert report["status"] == "PASS"
    assert report["llm_pool_best_rank"] == 1
    assert report["llm_pool_beats_non_llm_pool_best"] is True
    assert pool_summary["best_pool_name"] == "llm_reflective_pool"
    assert ledger["FE_total"] == 0
    assert route["next_stage"] == "Stage 8.29"
    assert len(rows) >= 8

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.30 PASS`" in combined
    assert "Stage 8.28   LLM vs non-LLM ownership-strategy ablation" in combined
    assert "hand-designed" in combined
    assert "random mutation" in combined
    assert "literature-inspired" in combined
    assert "LLM-reflective" in combined
    assert "Stage 8.29" in combined
    assert "not a SOTA claim" in combined
    assert "not a final objective-value performance claim" in combined

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage4_0_train_only_search.yaml"
OUTPUT_DIR = ROOT / "artifacts" / "search" / "stage4_0"
FROZEN_POOL = (
    ROOT / "artifacts" / "candidates" / "stage3_6" / "frozen_candidate_pool.jsonl"
)
FAMILY_SPACE = ROOT / "configs" / "stage4_coordination_family_space.yaml"
SEARCH_TRACE = OUTPUT_DIR / "search_trace.jsonl"
PROMOTION_CANDIDATES = OUTPUT_DIR / "promotion_candidates.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
SEARCH_REPORT = OUTPUT_DIR / "search_report.json"
STAGE_DOC = ROOT / "docs" / "stage4" / "stage4_0_train_only_search.md"
SELF_CHECK = ROOT / "docs" / "stage4" / "stage4_0_self_check_report.md"
README = ROOT / "README.md"


def test_stage4_0_runs_train_only_search_without_forbidden_feedback(tmp_path) -> None:
    from loco.coordination.train_only_search import run_stage4_0_train_only_search

    report = run_stage4_0_train_only_search(
        frozen_pool_path=FROZEN_POOL,
        family_space_config_path=FAMILY_SPACE,
        output_dir=tmp_path,
        promotion_top_k=3,
    )

    assert report["stage"] == "4.0"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "3.6"
    assert report["candidate_count"] == 12
    assert report["promotion_candidate_count"] == 3
    assert report["allowed_split"] == "train"
    assert report["family_lock_stage"] == "3.7"
    assert report["candidate_pool_frozen"] is True
    assert report["train_only_search_executed"] is True
    assert report["validation_feedback_used"] is False
    assert report["test_feedback_used"] is False
    assert report["llm_call_used"] is False
    assert report["new_candidate_generation_used"] is False
    assert report["ast_execution_used"] is False
    assert report["objective_evaluation_used"] is False
    assert report["optimizer_generation_used"] is False
    assert report["baseopt_modified"] is False
    assert report["not_performance_claim"] is True

    trace_rows = _read_jsonl(tmp_path / "search_trace.jsonl")
    promotions = json.loads((tmp_path / "promotion_candidates.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())

    assert len(trace_rows) == 12
    assert len({row["candidate_id"] for row in trace_rows}) == 12
    assert all(row["split"] == "train" for row in trace_rows)
    assert all(row["target_scope"] == "shared_variables_only" for row in trace_rows)
    assert all(row["objective_evaluation_used"] is False for row in trace_rows)
    assert all(row["validation_feedback_used"] is False for row in trace_rows)
    assert all(row["test_feedback_used"] is False for row in trace_rows)
    assert all(row["not_performance_claim"] is True for row in trace_rows)
    assert trace_rows == sorted(
        trace_rows,
        key=lambda row: (-row["train_proxy_score"], row["candidate_id"]),
    )

    assert promotions["status"] == "PASS"
    assert promotions["promotion_top_k"] == 3
    assert len(promotions["promotion_candidates"]) == 3
    assert [row["rank"] for row in promotions["promotion_candidates"]] == [1, 2, 3]
    assert all(
        row["promotion_status"] == "VALIDATION_READY_NOT_SELECTED_FINAL"
        for row in promotions["promotion_candidates"]
    )

    assert ledger["status"] == "PASS"
    assert ledger["FE_total"] == (
        ledger["FE_grouping"]
        + ledger["FE_proposal"]
        + ledger["FE_coordination_extra"]
        + ledger["FE_repair"]
    )
    assert ledger["FE_total"] == 12
    assert ledger["budget_scope"] == "train_only_candidate_search"
    assert ledger["cross_candidate_evaluations_shared"] is False


def test_stage4_0_committed_artifacts_and_docs_record_boundaries() -> None:
    required = [
        CONFIG,
        SEARCH_TRACE,
        PROMOTION_CANDIDATES,
        FE_LEDGER,
        SEARCH_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(SEARCH_REPORT.read_text(encoding="utf-8"))
    trace_rows = _read_jsonl(SEARCH_TRACE)
    promotions = json.loads(PROMOTION_CANDIDATES.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["candidate_count"] == 12
    assert report["promotion_candidate_count"] == 3
    assert report["next_status"] == "READY_FOR_STAGE4_1_TRAIN_SEARCH_AUDIT"
    assert report["not_performance_claim"] is True
    assert len(trace_rows) == 12
    assert promotions["promotion_candidates"][0]["rank"] == 1
    assert ledger["FE_total"] == 12

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 4.0" in combined
    assert "train-only search" in combined
    assert "frozen coordination-candidate pool" in combined
    assert "Stage 3.7" in combined
    assert "no validation feedback" in combined
    assert "no test feedback" in combined
    assert "no objective evaluation" in combined
    assert "not a performance claim" in combined


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

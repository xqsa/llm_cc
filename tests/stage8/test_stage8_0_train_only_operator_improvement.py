import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_0_train_only_operator_improvement.yaml"
OUTPUT_DIR = ROOT / "artifacts" / "improvement" / "stage8_0"
FROZEN_POOL = (
    ROOT / "artifacts" / "candidates" / "stage3_6" / "frozen_candidate_pool.jsonl"
)
FAMILY_SPACE = ROOT / "configs" / "stage4_coordination_family_space.yaml"
TRACE = OUTPUT_DIR / "improvement_trace.jsonl"
CANDIDATES = OUTPUT_DIR / "improvement_candidates.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
REPORT = OUTPUT_DIR / "improvement_report.json"
ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_0_train_only_operator_improvement.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_0_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_0_runs_train_only_improvement_with_frozen_inputs(tmp_path) -> None:
    from loco.coordination.train_only_operator_improvement import (
        run_stage8_0_train_only_operator_improvement,
    )

    report = run_stage8_0_train_only_operator_improvement(
        frozen_pool_path=FROZEN_POOL,
        family_space_config_path=FAMILY_SPACE,
        output_dir=tmp_path,
        improvement_top_k=4,
    )

    assert report["stage"] == "8.0"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "7.6"
    assert report["candidate_pool_source_stage"] == "3.6"
    assert report["allowed_split"] == "train"
    assert report["frozen_candidate_pool_used"] is True
    assert report["comparator_contract_used"] is True
    assert report["train_only_improvement_executed"] is True
    assert report["validation_feedback_used"] is False
    assert report["test_feedback_used"] is False
    assert report["llm_call_used"] is False
    assert report["new_candidate_generation_used"] is False
    assert report["ast_execution_used"] is False
    assert report["objective_evaluation_used"] is False
    assert report["benchmark_execution_used"] is False
    assert report["reported_results_used_as_runtime_feedback"] is False
    assert report["optimizer_generation_used"] is False
    assert report["controller_generation_used"] is False
    assert report["scheduler_generation_used"] is False
    assert report["baseopt_modified"] is False
    assert report["not_performance_claim"] is True

    trace_rows = _read_jsonl(tmp_path / "improvement_trace.jsonl")
    candidates = json.loads((tmp_path / "improvement_candidates.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

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
        key=lambda row: (-row["improvement_score"], row["candidate_id"]),
    )

    assert candidates["status"] == "PASS"
    assert candidates["improvement_top_k"] == 4
    assert len(candidates["improvement_candidates"]) == 4
    assert [row["rank"] for row in candidates["improvement_candidates"]] == [
        1,
        2,
        3,
        4,
    ]
    assert all(
        row["improvement_status"] == "TRAIN_ONLY_RECORDED"
        for row in candidates["improvement_candidates"]
    )

    assert ledger["status"] == "PASS"
    assert ledger["FE_total"] == (
        ledger["FE_grouping"]
        + ledger["FE_proposal"]
        + ledger["FE_coordination_extra"]
        + ledger["FE_repair"]
    )
    assert ledger["FE_total"] == 12
    assert ledger["budget_scope"] == "train_only_operator_improvement"
    assert ledger["cross_candidate_evaluations_shared"] is False

    assert route["status"] == "PASS"
    assert route["next_stage"] == "Stage 8.1"
    assert route["allowed_next_work"] == "train_only_selection_or_audit"
    assert route["use_validation_feedback"] is False
    assert route["use_test_feedback"] is False
    assert route["sota_claim_made"] is False


def test_stage8_0_committed_artifacts_and_docs_record_boundaries() -> None:
    required = [
        CONFIG,
        TRACE,
        CANDIDATES,
        FE_LEDGER,
        REPORT,
        ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    trace_rows = _read_jsonl(TRACE)
    candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["candidate_count"] == 12
    assert report["improvement_candidate_count"] == 4
    assert report["next_status"] == "READY_FOR_STAGE8_1_TRAIN_ONLY_SELECTION_AUDIT"
    assert report["not_performance_claim"] is True
    assert len(trace_rows) == 12
    assert candidates["improvement_candidates"][0]["rank"] == 1
    assert ledger["FE_total"] == 12

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 8.0" in combined
    assert "train-only operator improvement" in combined
    assert "frozen Stage 3.6 candidate pool" in combined
    assert "Stage 7.6 comparator contract" in combined
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

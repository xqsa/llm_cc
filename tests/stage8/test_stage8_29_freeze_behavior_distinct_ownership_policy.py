import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
STAGE8_27_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_27"
STAGE8_28_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_28"
OUTPUT_DIR = ROOT / "artifacts" / "selected" / "stage8_29"
CONFIG = ROOT / "configs" / "stage8_29_freeze_behavior_distinct_ownership_policy.yaml"
FROZEN_POLICY = OUTPUT_DIR / "frozen_behavior_distinct_policy.json"
FROZEN_PAYLOAD = OUTPUT_DIR / "frozen_strategy_payload.json"
FREEZE_MANIFEST = OUTPUT_DIR / "freeze_manifest.json"
READINESS_PROTOCOL = OUTPUT_DIR / "cec_checkpoint_readiness_protocol.json"
FREEZE_REPORT = OUTPUT_DIR / "freeze_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_29_freeze_behavior_distinct_ownership_policy.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_29_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_29_freezes_exact_stage8_28_selected_strategy_without_revision(tmp_path) -> None:
    from loco.coordination.freeze_behavior_distinct_ownership_policy import (
        freeze_stage8_29_behavior_distinct_ownership_policy,
    )

    report = freeze_stage8_29_behavior_distinct_ownership_policy(
        stage8_27_report_path=STAGE8_27_DIR
        / "llm_reflective_ownership_strategy_search_report.json",
        stage8_27_accepted_strategies_path=STAGE8_27_DIR / "accepted_strategies.jsonl",
        stage8_27_evaluator_path=STAGE8_27_DIR / "strategy_evaluator_report.json",
        stage8_28_report_path=STAGE8_28_DIR
        / "llm_vs_non_llm_ownership_ablation_report.json",
        stage8_28_pool_summary_path=STAGE8_28_DIR / "pool_summary.json",
        stage8_28_candidate_table_path=STAGE8_28_DIR / "pool_candidate_table.jsonl",
        stage8_28_fe_ledger_path=STAGE8_28_DIR / "fe_ledger.json",
        stage8_28_runtime_boundary_path=STAGE8_28_DIR / "runtime_boundary.json",
        stage8_28_next_route_path=STAGE8_28_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.29"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.28"
    assert report["selected_strategy_id"] == "stage8_27_1"
    assert report["selected_strategy_origin"] == "llm_reflective_generated"
    assert report["frozen_policy_status"] == "FROZEN_FOR_CEC2013_F13_F14_CHECKPOINT_NOT_FINAL"
    assert report["frozen_strategy_payload_matches_stage8_27"] is True
    assert report["stage8_28_ablation_confirmed"] is True
    assert report["selected_strategy_not_equivalent_to_best_reward_select"] is True
    assert report["non_trust_branch_exercised"] is True
    assert report["ownership_or_linkage_decision_exercised"] is True
    assert report["FE_total"] == 0
    assert report["llm_call_used"] is False
    assert report["new_llm_strategy_generation_used"] is False
    assert report["selected_policy_revision_used"] is False
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["not_sota_claim"] is True
    assert report["not_final_performance_claim"] is True
    assert report["recommended_next_stage"] == "Stage 8.30"

    required = [
        "frozen_behavior_distinct_policy.json",
        "frozen_strategy_payload.json",
        "freeze_manifest.json",
        "cec_checkpoint_readiness_protocol.json",
        "freeze_report.json",
        "fe_ledger.json",
        "runtime_boundary.json",
        "next_route_decision.json",
    ]
    for filename in required:
        assert (tmp_path / filename).is_file(), filename

    frozen_policy = json.loads((tmp_path / "frozen_behavior_distinct_policy.json").read_text())
    payload = json.loads((tmp_path / "frozen_strategy_payload.json").read_text())
    manifest = json.loads((tmp_path / "freeze_manifest.json").read_text())
    readiness = json.loads(
        (tmp_path / "cec_checkpoint_readiness_protocol.json").read_text()
    )
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert frozen_policy["strategy_id"] == "stage8_27_1"
    assert payload["strategy_id"] == "stage8_27_1"
    assert manifest["frozen_strategy_payload_matches_stage8_27"] is True
    assert manifest["frozen_strategy_payload_sha256"] == frozen_policy[
        "frozen_strategy_payload_sha256"
    ]
    assert readiness["status"] == "READY_FOR_STAGE8_30_CEC2013_F13_F14_CHECKPOINT"
    assert ledger["FE_total"] == 0
    assert boundary["selected_policy_revision_used"] is False
    assert route["next_stage"] == "Stage 8.30"


def test_stage8_29_committed_artifacts_docs_and_readme_record_freeze() -> None:
    required = [
        CONFIG,
        FROZEN_POLICY,
        FROZEN_PAYLOAD,
        FREEZE_MANIFEST,
        READINESS_PROTOCOL,
        FREEZE_REPORT,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(FREEZE_REPORT.read_text(encoding="utf-8"))
    frozen_payload = json.loads(FROZEN_PAYLOAD.read_text(encoding="utf-8"))
    manifest = json.loads(FREEZE_MANIFEST.read_text(encoding="utf-8"))
    readiness = json.loads(READINESS_PROTOCOL.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.29"
    assert report["status"] == "PASS"
    assert report["selected_strategy_id"] == "stage8_27_1"
    assert frozen_payload["strategy_id"] == report["selected_strategy_id"]
    assert manifest["frozen_strategy_payload_matches_stage8_27"] is True
    assert readiness["status"] == "READY_FOR_STAGE8_30_CEC2013_F13_F14_CHECKPOINT"
    assert ledger["FE_total"] == 0
    assert route["next_stage"] == "Stage 8.30"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.35 PASS`" in combined
    assert "Stage 8.29   freeze behavior-distinct ownership policy" in combined
    assert "stage8_27_1" in combined
    assert "FROZEN_FOR_CEC2013_F13_F14_CHECKPOINT_NOT_FINAL" in combined
    assert "Stage 8.30" in combined
    assert "not a SOTA claim" in combined
    assert "not a final objective-value performance claim" in combined

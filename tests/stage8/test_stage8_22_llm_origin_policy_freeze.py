import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
STAGE8_20_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_20"
STAGE8_21_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_21"
OUTPUT_DIR = ROOT / "artifacts" / "selected" / "stage8_22"
CONFIG = ROOT / "configs" / "stage8_22_llm_origin_policy_freeze.yaml"
FROZEN_POLICY = OUTPUT_DIR / "frozen_policy.json"
FROZEN_POLICY_PAYLOAD = OUTPUT_DIR / "frozen_policy_payload.json"
FREEZE_MANIFEST = OUTPUT_DIR / "frozen_policy_manifest.json"
READINESS_PROTOCOL = OUTPUT_DIR / "cec2013_f13_f14_multiseed_readiness_protocol.json"
FREEZE_REPORT = OUTPUT_DIR / "freeze_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_22_llm_origin_policy_freeze.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_22_self_check_report.md"
README = ROOT / "README.md"


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_stage8_22_freezes_exact_llm_origin_policy_without_revision(tmp_path) -> None:
    from loco.coordination.llm_origin_policy_freeze import (
        freeze_stage8_22_llm_origin_policy,
    )

    report = freeze_stage8_22_llm_origin_policy(
        stage8_20_report_path=STAGE8_20_DIR / "llm_reflective_search_report.json",
        stage8_20_accepted_candidates_path=STAGE8_20_DIR / "accepted_candidates.jsonl",
        stage8_20_evaluator_report_path=STAGE8_20_DIR / "candidate_evaluator_report.json",
        stage8_20_fe_ledger_path=STAGE8_20_DIR / "fe_ledger.json",
        stage8_20_runtime_boundary_path=STAGE8_20_DIR / "runtime_boundary.json",
        stage8_21_report_path=STAGE8_21_DIR / "llm_contribution_ablation_report.json",
        stage8_21_pool_summary_path=STAGE8_21_DIR / "pool_summary.json",
        stage8_21_candidate_table_path=STAGE8_21_DIR / "pool_candidate_table.jsonl",
        stage8_21_fe_ledger_path=STAGE8_21_DIR / "fe_ledger.json",
        stage8_21_runtime_boundary_path=STAGE8_21_DIR / "runtime_boundary.json",
        stage8_21_next_route_path=STAGE8_21_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.22"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.21"
    assert report["selected_candidate_id"] == "stage8_20_round_candidate_8"
    assert report["selected_candidate_origin"] == "llm_reflective_generated"
    assert report["freeze_status"] == "FROZEN_FOR_CEC2013_F13_F14_MULTISEED_NOT_FINAL"
    assert report["frozen_policy_payload_matches_stage8_20"] is True
    assert report["stage8_21_contribution_ablation_confirmed"] is True
    assert report["candidate_count"] == 1
    assert report["FE_total"] == 0
    assert report["next_stage"] == "Stage 8.23"
    assert report["llm_call_used"] is False
    assert report["new_candidate_generation_used"] is False
    assert report["selected_policy_revision_used"] is False
    assert report["objective_evaluation_used"] is False
    assert report["validation_feedback_used"] is False
    assert report["test_feedback_used"] is False
    assert report["reported_results_used_as_runtime_feedback"] is False
    assert report["baseopt_modified"] is False
    assert report["not_sota_claim"] is True
    assert report["not_final_performance_claim"] is True

    frozen_policy = json.loads((tmp_path / "frozen_policy.json").read_text())
    frozen_payload = json.loads((tmp_path / "frozen_policy_payload.json").read_text())
    manifest = json.loads((tmp_path / "frozen_policy_manifest.json").read_text())
    protocol = json.loads(
        (tmp_path / "cec2013_f13_f14_multiseed_readiness_protocol.json").read_text()
    )
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())
    accepted = _jsonl(STAGE8_20_DIR / "accepted_candidates.jsonl")
    source_payload = next(
        row["policy_payload"]
        for row in accepted
        if row["candidate_id"] == "stage8_20_round_candidate_8"
    )

    assert frozen_policy["candidate_id"] == report["selected_candidate_id"]
    assert frozen_policy["family"] == "ShrinkageWhenUnstable"
    assert frozen_policy["target_scope"] == "shared_variables_only"
    assert frozen_policy["rules"] == source_payload["rules"]
    assert frozen_policy["freeze_status"] == report["freeze_status"]
    assert frozen_payload == source_payload
    assert manifest["frozen_policy_payload_sha256"]
    assert manifest["source_stage8_20_candidate_row_sha256"]
    assert manifest["source_stage8_21_report_sha256"]
    assert manifest["frozen_policy_payload_matches_stage8_20"] is True
    assert protocol["status"] == "READY_FOR_STAGE8_23_CEC2013_F13_F14_MULTISEED_PILOT"
    assert protocol["selected_candidate_id"] == report["selected_candidate_id"]
    assert protocol["allowed_next_use"] == "CEC2013 F13/F14 multiseed pilot only"
    assert ledger["FE_total"] == 0
    assert ledger["llm_call_used"] is False
    assert boundary["forbidden_behaviors"]["selected_policy_revision"] is False
    assert route["next_stage"] == "Stage 8.23"
    assert route["allowed_next_work"] == "cec2013_f13_f14_multiseed_pilot"


def test_stage8_22_committed_artifacts_docs_and_readme_record_policy_freeze() -> None:
    required = [
        CONFIG,
        FROZEN_POLICY,
        FROZEN_POLICY_PAYLOAD,
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
    frozen_payload = json.loads(FROZEN_POLICY_PAYLOAD.read_text(encoding="utf-8"))
    manifest = json.loads(FREEZE_MANIFEST.read_text(encoding="utf-8"))
    protocol = json.loads(READINESS_PROTOCOL.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.22"
    assert report["status"] == "PASS"
    assert report["selected_candidate_id"] == "stage8_20_round_candidate_8"
    assert frozen_payload["policy_id"] == report["selected_candidate_id"]
    assert manifest["frozen_policy_payload_matches_stage8_20"] is True
    assert protocol["status"] == "READY_FOR_STAGE8_23_CEC2013_F13_F14_MULTISEED_PILOT"
    assert ledger["FE_total"] == 0
    assert route["next_stage"] == "Stage 8.23"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.27 PASS`" in combined
    assert "Stage 8.22   freeze LLM-origin beat-best_reward policy" in combined
    assert "stage8_20_round_candidate_8" in combined
    assert "FROZEN_FOR_CEC2013_F13_F14_MULTISEED_NOT_FINAL" in combined
    assert "Stage 8.23" in combined
    assert "not a SOTA claim" in combined
    assert "not a final objective-value performance claim" in combined

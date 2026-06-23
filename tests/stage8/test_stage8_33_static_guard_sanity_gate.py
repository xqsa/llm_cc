import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
STAGE8_32_DIR = ROOT / "artifacts" / "analysis" / "stage8_32"
OUTPUT_DIR = ROOT / "artifacts" / "analysis" / "stage8_33"
CONFIG = ROOT / "configs" / "stage8_33_static_guard_sanity_gate.yaml"
REPORT = OUTPUT_DIR / "static_guard_sanity_report.json"
DECISION_MATRIX = OUTPUT_DIR / "guard_decision_matrix.jsonl"
COLLAPSE_AUDIT = OUTPUT_DIR / "collapse_audit_report.json"
BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_33_static_guard_sanity_gate.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_33_self_check_report.md"
README = ROOT / "README.md"


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_stage8_33_static_guard_sanity_checks_guard_without_checkpoint_or_25run(
    tmp_path,
) -> None:
    from loco.coordination.static_guard_sanity_gate import (
        run_stage8_33_static_guard_sanity_gate,
    )

    report = run_stage8_33_static_guard_sanity_gate(
        stage8_32_repair_design_path=STAGE8_32_DIR / "repair_design_report.json",
        stage8_32_policy_payload_path=STAGE8_32_DIR / "guarded_policy_payload.json",
        stage8_32_guard_spec_path=STAGE8_32_DIR / "overcorrection_guard_spec.json",
        stage8_32_static_coverage_path=STAGE8_32_DIR
        / "static_guard_coverage_report.json",
        stage8_32_fe_ledger_path=STAGE8_32_DIR / "fe_ledger.json",
        stage8_32_runtime_boundary_path=STAGE8_32_DIR / "runtime_boundary.json",
        stage8_32_next_route_path=STAGE8_32_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.33"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.32"
    assert report["sanity_scope"] == "static_guard_sanity_only"
    assert report["repair_policy_id"] == "stage8_32_guarded_owner_trust_repair_v1"
    assert report["guard_not_collapsed"] is True
    assert report["reliable_best_reward_preserves_trust"] is True
    assert report["misleading_conflict_breaks_only_when_guarded"] is True
    assert report["unguarded_break_detected"] is False
    assert report["always_contribution_leader_break_detected"] is False
    assert report["allow_bounded_checkpoint_next"] is True
    assert report["run_full_25_run_panel_next"] is False
    assert report["formal_25_run_recommended_now"] is False
    assert report["FE_total"] == 0
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["cec_checkpoint_executed"] is False
    assert report["recommended_next_stage"] == "Stage 8.34"
    assert report["recommended_next_work"] == "bounded_guarded_policy_checkpoint"

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

    matrix_rows = _read_jsonl(tmp_path / "guard_decision_matrix.jsonl")
    collapse = json.loads((tmp_path / "collapse_audit_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert len(matrix_rows) >= 4
    by_fixture = {row["fixture_id"]: row for row in matrix_rows}
    assert by_fixture["best_reward_reliable_preserve"]["decision"][
        "coordination_action"
    ] == "trust_best_reward"
    assert by_fixture["best_reward_reliable_preserve"]["decision"][
        "linkage_decision"
    ] == "preserve"
    assert by_fixture["strong_owner_conflict_best_reward_misleading"]["decision"][
        "coordination_action"
    ] == "owner_proposal_select"
    assert by_fixture["strong_owner_conflict_best_reward_misleading"]["decision"][
        "linkage_decision"
    ] == "break"
    assert collapse["always_contribution_leader_break_detected"] is False
    assert collapse["unguarded_break_detected"] is False
    assert collapse["guard_not_collapsed"] is True
    assert ledger["FE_total"] == 0
    assert boundary["cec_checkpoint_executed"] is False
    assert boundary["formal_25_run_panel_executed"] is False
    assert boundary["forbidden_behaviors"]["cec_checkpoint_execution"] is False
    assert route["next_stage"] == "Stage 8.34"
    assert route["run_full_25_run_panel_next"] is False
    assert route["allow_bounded_checkpoint_next"] is True


def test_stage8_33_committed_artifacts_docs_and_readme_record_static_sanity() -> None:
    required = [
        CONFIG,
        REPORT,
        DECISION_MATRIX,
        COLLAPSE_AUDIT,
        FE_LEDGER,
        BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    collapse = json.loads(COLLAPSE_AUDIT.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))
    matrix_rows = _read_jsonl(DECISION_MATRIX)

    assert report["stage"] == "8.33"
    assert report["status"] == "PASS"
    assert report["guard_not_collapsed"] is True
    assert report["reliable_best_reward_preserves_trust"] is True
    assert report["misleading_conflict_breaks_only_when_guarded"] is True
    assert report["allow_bounded_checkpoint_next"] is True
    assert collapse["always_contribution_leader_break_detected"] is False
    assert ledger["FE_total"] == 0
    assert boundary["objective_loop_executed"] is False
    assert route["next_stage"] == "Stage 8.34"
    assert len(matrix_rows) >= 4

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.35 PASS`" in combined
    assert "Stage 8.33   static guard sanity or bounded checkpoint gate" in combined
    assert "guard_not_collapsed = true" in combined
    assert "reliable_best_reward_preserves_trust = true" in combined
    assert "misleading_conflict_breaks_only_when_guarded = true" in combined
    assert "run_full_25_run_panel_next = false" in combined
    assert "cec_checkpoint_executed = false" in combined
    assert "allow_bounded_checkpoint_next = true" in combined
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined

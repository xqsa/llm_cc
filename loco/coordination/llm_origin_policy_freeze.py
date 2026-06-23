"""Stage 8.22 LLM-origin policy freeze.

This stage freezes the Stage 8.20 LLM-origin policy that Stage 8.21 confirmed
as the best pool candidate. It performs no objective evaluation and does not
revise the policy.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "8.22"
PASS_STATUS = "PASS"
FROZEN_POLICY_SCHEMA_VERSION = "loco.stage8_22_frozen_policy.v1"
MANIFEST_SCHEMA_VERSION = "loco.stage8_22_frozen_policy_manifest.v1"
PROTOCOL_SCHEMA_VERSION = "loco.stage8_22_cec2013_f13_f14_readiness_protocol.v1"
REPORT_SCHEMA_VERSION = "loco.stage8_22_freeze_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_22_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_22_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_22_next_route_decision.v1"
FREEZE_STATUS = "FROZEN_FOR_CEC2013_F13_F14_MULTISEED_NOT_FINAL"
NEXT_STAGE = "Stage 8.23"
NEXT_WORK = "cec2013_f13_f14_multiseed_pilot"


def freeze_stage8_22_llm_origin_policy(
    *,
    stage8_20_report_path: Path | str,
    stage8_20_accepted_candidates_path: Path | str,
    stage8_20_evaluator_report_path: Path | str,
    stage8_20_fe_ledger_path: Path | str,
    stage8_20_runtime_boundary_path: Path | str,
    stage8_21_report_path: Path | str,
    stage8_21_pool_summary_path: Path | str,
    stage8_21_candidate_table_path: Path | str,
    stage8_21_fe_ledger_path: Path | str,
    stage8_21_runtime_boundary_path: Path | str,
    stage8_21_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Freeze the selected LLM-origin policy for the F13/F14 multiseed pilot."""

    stage8_20_report = _read_json(Path(stage8_20_report_path))
    stage8_20_evaluator = _read_json(Path(stage8_20_evaluator_report_path))
    stage8_20_fe_ledger = _read_json(Path(stage8_20_fe_ledger_path))
    stage8_20_boundary = _read_json(Path(stage8_20_runtime_boundary_path))
    stage8_21_report = _read_json(Path(stage8_21_report_path))
    stage8_21_pool_summary = _read_json(Path(stage8_21_pool_summary_path))
    stage8_21_fe_ledger = _read_json(Path(stage8_21_fe_ledger_path))
    stage8_21_boundary = _read_json(Path(stage8_21_runtime_boundary_path))
    stage8_21_route = _read_json(Path(stage8_21_next_route_path))
    accepted_rows = _read_jsonl(Path(stage8_20_accepted_candidates_path))
    candidate_table_rows = _read_jsonl(Path(stage8_21_candidate_table_path))

    _validate_inputs(
        stage8_20_report=stage8_20_report,
        stage8_20_evaluator=stage8_20_evaluator,
        stage8_20_fe_ledger=stage8_20_fe_ledger,
        stage8_20_boundary=stage8_20_boundary,
        stage8_21_report=stage8_21_report,
        stage8_21_pool_summary=stage8_21_pool_summary,
        stage8_21_fe_ledger=stage8_21_fe_ledger,
        stage8_21_boundary=stage8_21_boundary,
        stage8_21_route=stage8_21_route,
    )

    selected_candidate_id = str(stage8_20_report["selected_candidate_id"])
    selected_row = _selected_accepted_row(accepted_rows, selected_candidate_id)
    selected_pool_row = _selected_pool_candidate_row(
        candidate_table_rows, selected_candidate_id
    )
    policy_payload = dict(selected_row["policy_payload"])
    frozen_policy = _build_frozen_policy(
        policy_payload=policy_payload,
        stage8_20_report=stage8_20_report,
        stage8_21_report=stage8_21_report,
        selected_pool_row=selected_pool_row,
    )
    manifest = _build_manifest(
        frozen_policy=frozen_policy,
        policy_payload=policy_payload,
        source_candidate_row=selected_row,
        stage8_20_report=stage8_20_report,
        stage8_20_evaluator=stage8_20_evaluator,
        stage8_20_fe_ledger=stage8_20_fe_ledger,
        stage8_21_report=stage8_21_report,
        stage8_21_pool_summary=stage8_21_pool_summary,
        stage8_21_fe_ledger=stage8_21_fe_ledger,
    )
    protocol = _build_protocol(manifest)
    ledger = _build_fe_ledger(
        inherited_stage8_20_fe_total=int(stage8_20_fe_ledger["FE_total"]),
        inherited_stage8_21_fe_total=int(stage8_21_fe_ledger["FE_total"]),
    )
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    report = _build_report(
        frozen_policy=frozen_policy,
        manifest=manifest,
        protocol=protocol,
        ledger=ledger,
        route=route,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "frozen_policy.json", frozen_policy)
    _write_json(output_path / "frozen_policy_payload.json", policy_payload)
    _write_json(output_path / "frozen_policy_manifest.json", manifest)
    _write_json(
        output_path / "cec2013_f13_f14_multiseed_readiness_protocol.json", protocol
    )
    _write_json(output_path / "freeze_report.json", report)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    *,
    stage8_20_report: Mapping[str, Any],
    stage8_20_evaluator: Mapping[str, Any],
    stage8_20_fe_ledger: Mapping[str, Any],
    stage8_20_boundary: Mapping[str, Any],
    stage8_21_report: Mapping[str, Any],
    stage8_21_pool_summary: Mapping[str, Any],
    stage8_21_fe_ledger: Mapping[str, Any],
    stage8_21_boundary: Mapping[str, Any],
    stage8_21_route: Mapping[str, Any],
) -> None:
    if stage8_20_report.get("stage") != "8.20" or stage8_20_report.get("status") != "PASS":
        raise ValueError("Stage 8.22 requires a passing Stage 8.20 report.")
    if stage8_20_report.get("selected_candidate_origin") != "llm_reflective_generated":
        raise ValueError("Stage 8.22 requires an LLM-origin Stage 8.20 selection.")
    if stage8_20_evaluator.get("selected_candidate_id") != stage8_20_report.get(
        "selected_candidate_id"
    ):
        raise ValueError("Stage 8.20 evaluator/report selection mismatch.")
    if stage8_20_report.get("selected_candidate_not_equivalent_to_best_reward") is not True:
        raise ValueError("Stage 8.22 requires non-degenerate Stage 8.20 evidence.")
    if int(stage8_20_report.get("train_objective_loss_count_vs_best_reward", -1)) != 0:
        raise ValueError("Stage 8.22 requires zero-loss Stage 8.20 train evidence.")
    if stage8_20_boundary.get("real_llm_api_called") is not True:
        raise ValueError("Stage 8.22 requires real LLM API evidence from Stage 8.20.")

    if stage8_21_report.get("stage") != "8.21" or stage8_21_report.get("status") != "PASS":
        raise ValueError("Stage 8.22 requires a passing Stage 8.21 report.")
    if stage8_21_report.get("stage8_20_selected_candidate_id") != stage8_20_report.get(
        "selected_candidate_id"
    ):
        raise ValueError("Stage 8.21 did not confirm the Stage 8.20 candidate.")
    if stage8_21_report.get("llm_pool_best_rank") != 1:
        raise ValueError("Stage 8.22 requires Stage 8.21 LLM pool rank 1.")
    if stage8_21_report.get("llm_pool_beats_non_llm_pool_best") is not True:
        raise ValueError("Stage 8.22 requires LLM pool contribution evidence.")
    if stage8_21_pool_summary.get("same_train_side_evaluator_used") is not True:
        raise ValueError("Stage 8.22 requires same-evaluator Stage 8.21 evidence.")
    if stage8_21_boundary.get("new_llm_candidate_generation_used") is not False:
        raise ValueError("Stage 8.21 boundary must forbid new LLM generation.")
    if stage8_21_route.get("next_stage") != "Stage 8.22":
        raise ValueError("Stage 8.22 requires the Stage 8.21 next-route decision.")
    if int(stage8_20_fe_ledger.get("FE_total", -1)) <= 0:
        raise ValueError("Stage 8.22 requires Stage 8.20 FE evidence.")
    if int(stage8_21_fe_ledger.get("FE_total", -1)) <= 0:
        raise ValueError("Stage 8.22 requires Stage 8.21 FE evidence.")


def _selected_accepted_row(
    accepted_rows: Sequence[Mapping[str, Any]], selected_candidate_id: str
) -> Mapping[str, Any]:
    matches = [
        row
        for row in accepted_rows
        if str(row.get("candidate_id")) == selected_candidate_id
        and row.get("origin") == "llm_reflective_generated"
        and row.get("decision") == "accepted"
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one accepted LLM candidate: {selected_candidate_id}")
    row = matches[0]
    if row.get("fake_llm_candidate") is not False:
        raise ValueError("Stage 8.22 refuses fake LLM candidates.")
    if row.get("target_scope") != "shared_variables_only":
        raise ValueError("Frozen policy must target shared variables only.")
    return row


def _selected_pool_candidate_row(
    candidate_rows: Sequence[Mapping[str, Any]], selected_candidate_id: str
) -> Mapping[str, Any]:
    matches = [
        row
        for row in candidate_rows
        if str(row.get("candidate_id")) == selected_candidate_id
        and row.get("pool_id") == "llm_reflective_pool"
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one Stage 8.21 LLM-pool candidate row: {selected_candidate_id}"
        )
    return matches[0]


def _build_frozen_policy(
    *,
    policy_payload: Mapping[str, Any],
    stage8_20_report: Mapping[str, Any],
    stage8_21_report: Mapping[str, Any],
    selected_pool_row: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": FROZEN_POLICY_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "8.20",
        "candidate_id": str(policy_payload["policy_id"]),
        "policy_id": str(policy_payload["policy_id"]),
        "freeze_status": FREEZE_STATUS,
        "origin": str(policy_payload["origin"]),
        "family": str(policy_payload["family"]),
        "target_scope": "shared_variables_only",
        "features": list(policy_payload["features"]),
        "memory": list(policy_payload.get("memory", [])),
        "rules": list(policy_payload["rules"]),
        "stage8_20_train_objective_win_count_vs_best_reward": int(
            stage8_20_report["train_objective_win_count_vs_best_reward"]
        ),
        "stage8_20_train_objective_loss_count_vs_best_reward": int(
            stage8_20_report["train_objective_loss_count_vs_best_reward"]
        ),
        "stage8_21_llm_pool_best_rank": int(stage8_21_report["llm_pool_best_rank"]),
        "stage8_21_llm_pool_beats_non_llm_pool_best": bool(
            stage8_21_report["llm_pool_beats_non_llm_pool_best"]
        ),
        "mean_delta_vs_best_reward": float(selected_pool_row["mean_delta_vs_best_reward"]),
        "branch_counts": dict(selected_pool_row["branch_counts"]),
        "non_trust_best_reward_branch_exercised": bool(
            selected_pool_row["non_trust_best_reward_branch_exercised"]
        ),
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "selected_policy_revision_used": False,
        "objective_evaluation_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_manifest(
    *,
    frozen_policy: Mapping[str, Any],
    policy_payload: Mapping[str, Any],
    source_candidate_row: Mapping[str, Any],
    stage8_20_report: Mapping[str, Any],
    stage8_20_evaluator: Mapping[str, Any],
    stage8_20_fe_ledger: Mapping[str, Any],
    stage8_21_report: Mapping[str, Any],
    stage8_21_pool_summary: Mapping[str, Any],
    stage8_21_fe_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "source_stage": "8.21",
        "selected_candidate_id": str(frozen_policy["candidate_id"]),
        "selected_candidate_origin": str(frozen_policy["origin"]),
        "selected_candidate_family": str(frozen_policy["family"]),
        "freeze_status": FREEZE_STATUS,
        "frozen_policy_payload_matches_stage8_20": True,
        "stage8_21_contribution_ablation_confirmed": True,
        "candidate_count": 1,
        "source_stage8_20_candidate_row_sha256": _fingerprint_payload(
            source_candidate_row
        ),
        "source_stage8_20_report_sha256": _fingerprint_payload(stage8_20_report),
        "source_stage8_20_evaluator_sha256": _fingerprint_payload(stage8_20_evaluator),
        "source_stage8_20_fe_ledger_sha256": _fingerprint_payload(
            stage8_20_fe_ledger
        ),
        "source_stage8_21_report_sha256": _fingerprint_payload(stage8_21_report),
        "source_stage8_21_pool_summary_sha256": _fingerprint_payload(
            stage8_21_pool_summary
        ),
        "source_stage8_21_fe_ledger_sha256": _fingerprint_payload(
            stage8_21_fe_ledger
        ),
        "frozen_policy_sha256": _fingerprint_payload(frozen_policy),
        "frozen_policy_payload_sha256": _fingerprint_payload(policy_payload),
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "selected_policy_revision_used": False,
        "objective_evaluation_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_protocol(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "READY_FOR_STAGE8_23_CEC2013_F13_F14_MULTISEED_PILOT",
        "selected_candidate_id": str(manifest["selected_candidate_id"]),
        "frozen_policy_sha256": str(manifest["frozen_policy_sha256"]),
        "frozen_policy_payload_sha256": str(manifest["frozen_policy_payload_sha256"]),
        "allowed_next_use": "CEC2013 F13/F14 multiseed pilot only",
        "benchmark_scope": "CEC2013 F13/F14 only before full F1-F15 escalation",
        "run_count_policy": "multiseed pilot before formal 25-run panel",
        "base_optimizer_policy": "BaseOpt must remain fixed",
        "no_policy_revision": True,
        "no_llm_call": True,
        "no_new_candidate_generation": True,
        "no_validation_feedback": True,
        "no_test_feedback": True,
        "no_reported_results_runtime_feedback": True,
        "no_baseopt_modification": True,
        "no_optimizer_generation": True,
        "no_controller_scheduler_generation": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(
    *, inherited_stage8_20_fe_total: int, inherited_stage8_21_fe_total: int
) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "budget_scope": "llm_origin_policy_freeze",
        "inherited_stage8_20_FE_total": inherited_stage8_20_fe_total,
        "inherited_stage8_21_FE_total": inherited_stage8_21_fe_total,
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "all_extra_fe_counted": True,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "claim_scope": "freeze LLM-origin policy for CEC2013 F13/F14 multiseed pilot",
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "fake_llm_candidates_used": False,
        "forbidden_behaviors": {
            "selected_policy_revision": False,
            "new_llm_candidate_generation": False,
            "fake_llm_candidate_generation": False,
            "evolution_search": False,
            "validation_feedback": False,
            "test_feedback": False,
            "reported_results_runtime_feedback": False,
            "baseopt_modification": False,
            "optimizer_generation": False,
            "controller_scheduler_generation": False,
        },
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_next_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "decision": "ROUTE_TO_CEC2013_F13_F14_MULTISEED_PILOT",
        "next_stage": NEXT_STAGE,
        "allowed_next_work": NEXT_WORK,
        "next_route": NEXT_WORK,
        "run_full_25_run_panel_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    frozen_policy: Mapping[str, Any],
    manifest: Mapping[str, Any],
    protocol: Mapping[str, Any],
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "source_stage": "8.21",
        "selected_candidate_id": str(frozen_policy["candidate_id"]),
        "selected_candidate_origin": str(frozen_policy["origin"]),
        "selected_candidate_family": str(frozen_policy["family"]),
        "freeze_status": FREEZE_STATUS,
        "frozen_policy_payload_matches_stage8_20": bool(
            manifest["frozen_policy_payload_matches_stage8_20"]
        ),
        "stage8_21_contribution_ablation_confirmed": bool(
            manifest["stage8_21_contribution_ablation_confirmed"]
        ),
        "candidate_count": 1,
        "cec2013_f13_f14_multiseed_ready": protocol["status"]
        == "READY_FOR_STAGE8_23_CEC2013_F13_F14_MULTISEED_PILOT",
        "FE_total": int(ledger["FE_total"]),
        "next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "selected_policy_revision_used": False,
        "objective_evaluation_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _fingerprint_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

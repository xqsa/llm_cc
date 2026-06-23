"""Stage 8.29 behavior-distinct ownership policy freeze.

This stage freezes the exact Stage 8.28-selected ownership-aware strategy
payload for the next CEC2013 F13/F14 checkpoint. It performs no objective
evaluation, makes no LLM call, and does not revise the selected strategy.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "8.29"
PASS_STATUS = "PASS"
FROZEN_POLICY_SCHEMA_VERSION = "loco.stage8_29_frozen_behavior_distinct_policy.v1"
MANIFEST_SCHEMA_VERSION = "loco.stage8_29_freeze_manifest.v1"
PROTOCOL_SCHEMA_VERSION = "loco.stage8_29_cec_checkpoint_readiness_protocol.v1"
REPORT_SCHEMA_VERSION = "loco.stage8_29_freeze_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_29_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_29_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_29_next_route_decision.v1"
FREEZE_STATUS = "FROZEN_FOR_CEC2013_F13_F14_CHECKPOINT_NOT_FINAL"
NEXT_STAGE = "Stage 8.30"
NEXT_WORK = "cec2013_f13_f14_behavior_distinct_policy_checkpoint"


def freeze_stage8_29_behavior_distinct_ownership_policy(
    *,
    stage8_27_report_path: Path | str,
    stage8_27_accepted_strategies_path: Path | str,
    stage8_27_evaluator_path: Path | str,
    stage8_28_report_path: Path | str,
    stage8_28_pool_summary_path: Path | str,
    stage8_28_candidate_table_path: Path | str,
    stage8_28_fe_ledger_path: Path | str,
    stage8_28_runtime_boundary_path: Path | str,
    stage8_28_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Freeze the behavior-distinct Stage 8.28 selected ownership strategy."""

    stage8_27_report = _read_json(Path(stage8_27_report_path))
    stage8_27_evaluator = _read_json(Path(stage8_27_evaluator_path))
    stage8_28_report = _read_json(Path(stage8_28_report_path))
    stage8_28_pool_summary = _read_json(Path(stage8_28_pool_summary_path))
    stage8_28_fe_ledger = _read_json(Path(stage8_28_fe_ledger_path))
    stage8_28_boundary = _read_json(Path(stage8_28_runtime_boundary_path))
    stage8_28_route = _read_json(Path(stage8_28_next_route_path))
    accepted_rows = _read_jsonl(Path(stage8_27_accepted_strategies_path))
    candidate_rows = _read_jsonl(Path(stage8_28_candidate_table_path))

    _validate_inputs(
        stage8_27_report=stage8_27_report,
        stage8_27_evaluator=stage8_27_evaluator,
        stage8_28_report=stage8_28_report,
        stage8_28_pool_summary=stage8_28_pool_summary,
        stage8_28_fe_ledger=stage8_28_fe_ledger,
        stage8_28_boundary=stage8_28_boundary,
        stage8_28_route=stage8_28_route,
    )

    selected_strategy_id = str(stage8_28_report["selected_strategy_id"])
    accepted_row = _selected_accepted_strategy_row(accepted_rows, selected_strategy_id)
    candidate_row = _selected_pool_candidate_row(candidate_rows, selected_strategy_id)
    strategy_payload = dict(accepted_row["strategy_payload"])
    frozen_policy = _build_frozen_policy(
        strategy_payload=strategy_payload,
        stage8_27_report=stage8_27_report,
        stage8_28_report=stage8_28_report,
        candidate_row=candidate_row,
    )
    manifest = _build_manifest(
        frozen_policy=frozen_policy,
        strategy_payload=strategy_payload,
        source_strategy_row=accepted_row,
        source_candidate_row=candidate_row,
        stage8_27_report=stage8_27_report,
        stage8_27_evaluator=stage8_27_evaluator,
        stage8_28_report=stage8_28_report,
        stage8_28_pool_summary=stage8_28_pool_summary,
        stage8_28_fe_ledger=stage8_28_fe_ledger,
    )
    protocol = _build_readiness_protocol(manifest)
    ledger = _build_fe_ledger(
        inherited_stage8_27_fe_total=int(stage8_27_report["FE_total"]),
        inherited_stage8_28_fe_total=int(stage8_28_fe_ledger["FE_total"]),
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
    _write_json(output_path / "frozen_behavior_distinct_policy.json", frozen_policy)
    _write_json(output_path / "frozen_strategy_payload.json", strategy_payload)
    _write_json(output_path / "freeze_manifest.json", manifest)
    _write_json(output_path / "cec_checkpoint_readiness_protocol.json", protocol)
    _write_json(output_path / "freeze_report.json", report)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    *,
    stage8_27_report: Mapping[str, Any],
    stage8_27_evaluator: Mapping[str, Any],
    stage8_28_report: Mapping[str, Any],
    stage8_28_pool_summary: Mapping[str, Any],
    stage8_28_fe_ledger: Mapping[str, Any],
    stage8_28_boundary: Mapping[str, Any],
    stage8_28_route: Mapping[str, Any],
) -> None:
    if stage8_27_report.get("stage") != "8.27" or stage8_27_report.get("status") != "PASS":
        raise ValueError("Stage 8.29 requires a passing Stage 8.27 report.")
    if stage8_27_report.get("real_llm_api_called") is not True:
        raise ValueError("Stage 8.29 requires real Stage 8.27 LLM evidence.")
    if stage8_27_report.get("selected_strategy_origin") != "llm_reflective_generated":
        raise ValueError("Stage 8.29 requires an LLM-reflective Stage 8.27 strategy.")
    if stage8_27_report.get("selected_strategy_not_equivalent_to_best_reward_select") is not True:
        raise ValueError("Stage 8.29 requires behavior-distinct Stage 8.27 evidence.")
    if stage8_27_evaluator.get("selected_strategy_id") != stage8_27_report.get(
        "selected_strategy_id"
    ):
        raise ValueError("Stage 8.27 evaluator/report selection mismatch.")
    if int(stage8_27_evaluator.get("train_side_loss_count_vs_best_reward", -1)) != 0:
        raise ValueError("Stage 8.29 requires zero-loss Stage 8.27 train evidence.")

    if stage8_28_report.get("stage") != "8.28" or stage8_28_report.get("status") != "PASS":
        raise ValueError("Stage 8.29 requires a passing Stage 8.28 report.")
    if stage8_28_report.get("selected_strategy_id") != stage8_27_report.get(
        "selected_strategy_id"
    ):
        raise ValueError("Stage 8.28 did not select the Stage 8.27 chosen strategy.")
    if stage8_28_report.get("selected_strategy_origin") != "llm_reflective_generated":
        raise ValueError("Stage 8.29 requires an LLM-origin Stage 8.28 selection.")
    if stage8_28_report.get("llm_pool_best_rank") != 1:
        raise ValueError("Stage 8.29 requires Stage 8.28 LLM pool rank 1.")
    if stage8_28_report.get("llm_pool_beats_non_llm_pool_best") is not True:
        raise ValueError("Stage 8.29 requires Stage 8.28 LLM contribution evidence.")
    if stage8_28_report.get("selected_strategy_not_equivalent_to_best_reward_select") is not True:
        raise ValueError("Stage 8.29 requires non-equivalent Stage 8.28 selection.")
    if stage8_28_report.get("non_trust_branch_exercised") is not True:
        raise ValueError("Stage 8.29 requires non-trust branch coverage.")
    if stage8_28_report.get("ownership_or_linkage_decision_exercised") is not True:
        raise ValueError("Stage 8.29 requires ownership/linkage decision coverage.")
    if stage8_28_pool_summary.get("best_strategy_id") != stage8_28_report.get(
        "selected_strategy_id"
    ):
        raise ValueError("Stage 8.28 pool summary/report selection mismatch.")
    if stage8_28_pool_summary.get("best_pool_name") != "llm_reflective_pool":
        raise ValueError("Stage 8.29 requires an LLM-reflective best pool.")
    if int(stage8_28_fe_ledger.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.29 requires Stage 8.28 FE_total = 0.")
    if stage8_28_boundary.get("new_llm_strategy_generation_used") is not False:
        raise ValueError("Stage 8.28 boundary must forbid new LLM generation.")
    if stage8_28_boundary.get("objective_loop_executed") is not False:
        raise ValueError("Stage 8.28 boundary must forbid objective loop execution.")
    if stage8_28_route.get("next_stage") != "Stage 8.29":
        raise ValueError("Stage 8.29 requires the Stage 8.28 next-route decision.")


def _selected_accepted_strategy_row(
    accepted_rows: Sequence[Mapping[str, Any]], selected_strategy_id: str
) -> Mapping[str, Any]:
    matches = [
        row
        for row in accepted_rows
        if str(row.get("strategy_id")) == selected_strategy_id
        and row.get("origin") == "llm_reflective_generated"
        and row.get("decision") == "accepted"
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one accepted LLM strategy: {selected_strategy_id}")
    row = matches[0]
    payload = row.get("strategy_payload")
    if not isinstance(payload, Mapping):
        raise ValueError("Accepted strategy row is missing strategy_payload.")
    if payload.get("strategy_id") != selected_strategy_id:
        raise ValueError("Accepted strategy row/payload id mismatch.")
    return row


def _selected_pool_candidate_row(
    candidate_rows: Sequence[Mapping[str, Any]], selected_strategy_id: str
) -> Mapping[str, Any]:
    matches = [
        row
        for row in candidate_rows
        if str(row.get("strategy_id")) == selected_strategy_id
        and row.get("pool_name") == "llm_reflective_pool"
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one Stage 8.28 LLM-pool strategy row: {selected_strategy_id}"
        )
    row = matches[0]
    if row.get("gate_passed") is not True:
        raise ValueError("Frozen Stage 8.29 strategy must pass the Stage 8.28 gate.")
    return row


def _build_frozen_policy(
    *,
    strategy_payload: Mapping[str, Any],
    stage8_27_report: Mapping[str, Any],
    stage8_28_report: Mapping[str, Any],
    candidate_row: Mapping[str, Any],
) -> dict[str, Any]:
    payload_hash = _fingerprint_payload(strategy_payload)
    return {
        "schema_version": FROZEN_POLICY_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "8.28",
        "strategy_id": str(strategy_payload["strategy_id"]),
        "origin": str(strategy_payload["origin"]),
        "family": str(strategy_payload["family"]),
        "freeze_status": FREEZE_STATUS,
        "frozen_policy_status": FREEZE_STATUS,
        "frozen_strategy_payload_sha256": payload_hash,
        "rules": list(strategy_payload["rules"]),
        "stage8_27_real_llm_api_called": bool(stage8_27_report["real_llm_api_called"]),
        "stage8_27_raw_llm_strategy_count": int(stage8_27_report["raw_llm_strategy_count"]),
        "stage8_27_accepted_strategy_count": int(
            stage8_27_report["accepted_strategy_count"]
        ),
        "stage8_27_train_side_win_count_vs_best_reward": int(
            stage8_27_report["train_side_win_count_vs_best_reward"]
        ),
        "stage8_27_train_side_loss_count_vs_best_reward": int(
            stage8_27_report["train_side_loss_count_vs_best_reward"]
        ),
        "stage8_28_llm_pool_best_rank": int(stage8_28_report["llm_pool_best_rank"]),
        "stage8_28_llm_pool_beats_non_llm_pool_best": bool(
            stage8_28_report["llm_pool_beats_non_llm_pool_best"]
        ),
        "mean_delta_vs_best_reward": float(candidate_row["mean_delta_vs_best_reward"]),
        "win_count_vs_best_reward": int(candidate_row["win_count_vs_best_reward"]),
        "loss_count_vs_best_reward": int(candidate_row["loss_count_vs_best_reward"]),
        "selected_strategy_not_equivalent_to_best_reward_select": bool(
            candidate_row["not_equivalent_to_best_reward_select"]
        ),
        "non_trust_branch_exercised": bool(candidate_row["non_trust_branch_exercised"]),
        "ownership_or_linkage_decision_exercised": bool(
            candidate_row["ownership_or_linkage_decision_exercised"]
        ),
        "llm_call_used": False,
        "new_llm_strategy_generation_used": False,
        "selected_policy_revision_used": False,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
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
    strategy_payload: Mapping[str, Any],
    source_strategy_row: Mapping[str, Any],
    source_candidate_row: Mapping[str, Any],
    stage8_27_report: Mapping[str, Any],
    stage8_27_evaluator: Mapping[str, Any],
    stage8_28_report: Mapping[str, Any],
    stage8_28_pool_summary: Mapping[str, Any],
    stage8_28_fe_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "source_stage": "8.28",
        "selected_strategy_id": str(frozen_policy["strategy_id"]),
        "selected_strategy_origin": str(frozen_policy["origin"]),
        "selected_strategy_family": str(frozen_policy["family"]),
        "frozen_policy_status": FREEZE_STATUS,
        "freeze_status": FREEZE_STATUS,
        "frozen_strategy_payload_matches_stage8_27": True,
        "stage8_28_ablation_confirmed": True,
        "stage8_27_source_strategy_row_sha256": _fingerprint_payload(
            source_strategy_row
        ),
        "stage8_28_source_candidate_row_sha256": _fingerprint_payload(
            source_candidate_row
        ),
        "stage8_27_report_sha256": _fingerprint_payload(stage8_27_report),
        "stage8_27_evaluator_sha256": _fingerprint_payload(stage8_27_evaluator),
        "stage8_28_report_sha256": _fingerprint_payload(stage8_28_report),
        "stage8_28_pool_summary_sha256": _fingerprint_payload(stage8_28_pool_summary),
        "stage8_28_fe_ledger_sha256": _fingerprint_payload(stage8_28_fe_ledger),
        "frozen_policy_sha256": _fingerprint_payload(frozen_policy),
        "frozen_strategy_payload_sha256": _fingerprint_payload(strategy_payload),
        "llm_call_used": False,
        "new_llm_strategy_generation_used": False,
        "selected_policy_revision_used": False,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_readiness_protocol(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PROTOCOL_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "READY_FOR_STAGE8_30_CEC2013_F13_F14_CHECKPOINT",
        "selected_strategy_id": str(manifest["selected_strategy_id"]),
        "selected_strategy_origin": str(manifest["selected_strategy_origin"]),
        "frozen_policy_status": FREEZE_STATUS,
        "frozen_policy_sha256": str(manifest["frozen_policy_sha256"]),
        "frozen_strategy_payload_sha256": str(
            manifest["frozen_strategy_payload_sha256"]
        ),
        "allowed_next_use": "CEC2013 F13/F14 checkpoint only before formal 25-run panel",
        "benchmark_scope": "CEC2013 F13/F14 checkpoint",
        "run_count_policy": "single checkpoint before formal 25-run panel",
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
    *, inherited_stage8_27_fe_total: int, inherited_stage8_28_fe_total: int
) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "budget_scope": "behavior_distinct_ownership_policy_freeze",
        "inherited_stage8_27_FE_total": inherited_stage8_27_fe_total,
        "inherited_stage8_28_FE_total": inherited_stage8_28_fe_total,
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
        "new_llm_strategy_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "claim_scope": "freeze behavior-distinct ownership-aware LLM-origin strategy",
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": False,
        "new_llm_strategy_generation_used": False,
        "fake_llm_strategies_used": False,
        "selected_policy_revision_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "forbidden_behaviors": {
            "selected_policy_revision": False,
            "new_llm_strategy_generation": False,
            "fake_llm_strategy_generation": False,
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
        "decision": "ROUTE_TO_CEC2013_F13_F14_BEHAVIOR_DISTINCT_POLICY_CHECKPOINT",
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
        "source_stage": "8.28",
        "selected_strategy_id": str(frozen_policy["strategy_id"]),
        "selected_strategy_origin": str(frozen_policy["origin"]),
        "selected_strategy_family": str(frozen_policy["family"]),
        "frozen_policy_status": FREEZE_STATUS,
        "frozen_strategy_payload_matches_stage8_27": bool(
            manifest["frozen_strategy_payload_matches_stage8_27"]
        ),
        "stage8_28_ablation_confirmed": bool(
            manifest["stage8_28_ablation_confirmed"]
        ),
        "selected_strategy_not_equivalent_to_best_reward_select": bool(
            frozen_policy["selected_strategy_not_equivalent_to_best_reward_select"]
        ),
        "non_trust_branch_exercised": bool(
            frozen_policy["non_trust_branch_exercised"]
        ),
        "ownership_or_linkage_decision_exercised": bool(
            frozen_policy["ownership_or_linkage_decision_exercised"]
        ),
        "cec_checkpoint_ready": protocol["status"]
        == "READY_FOR_STAGE8_30_CEC2013_F13_F14_CHECKPOINT",
        "FE_total": int(ledger["FE_total"]),
        "next_stage": route["next_stage"],
        "recommended_next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
        "llm_call_used": False,
        "new_llm_strategy_generation_used": False,
        "selected_policy_revision_used": False,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
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

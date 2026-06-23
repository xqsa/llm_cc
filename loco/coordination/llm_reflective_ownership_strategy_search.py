"""Stage 8.27 real LLM-reflective ownership-aware strategy search."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from loco.coordination.ownership_aware_strategy_dsl import (
    PROGRAM_SCHEMA_VERSION,
    evaluate_strategy_program,
    load_strategy_program,
)
from loco.llm.api_candidate_generator import _parse_json_object
from loco.llm.provider_client import (
    ChatCompletionResult,
    LLMClientConfig,
    call_chat_completion,
    load_llm_config_from_env,
)


STAGE = "8.27"
RAW_BATCH_SCHEMA_VERSION = "loco.stage8_27_raw_strategy_batch.v1"
REPORT_SCHEMA_VERSION = "loco.stage8_27_llm_reflective_ownership_search_report.v1"
API_PREFLIGHT_SCHEMA_VERSION = "loco.stage8_27_api_preflight_report.v1"
PROMPT_CONTEXT_SCHEMA_VERSION = "loco.stage8_27_reflection_prompt_context.v1"
ROUND_SCHEMA_VERSION = "loco.stage8_27_reflection_round.v1"
STATIC_AUDIT_SCHEMA_VERSION = "loco.stage8_27_static_audit_report.v1"
EVALUATOR_SCHEMA_VERSION = "loco.stage8_27_strategy_evaluator_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_27_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_27_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_27_next_route_decision.v1"

PASS_STATUS = "PASS"
BLOCKED_STATUS = "BLOCKED_NEEDS_REAL_LLM_API"


def run_stage8_27_llm_reflective_ownership_strategy_search(
    *,
    stage8_26_report_path: Path | str,
    stage8_26_manifest_path: Path | str,
    stage8_26_equivalence_path: Path | str,
    stage8_26_fe_ledger_path: Path | str,
    stage8_26_runtime_boundary_path: Path | str,
    stage8_26_next_route_path: Path | str,
    output_dir: Path | str,
    env_path: Path | str,
    reflection_round_count: int = 2,
    strategy_count_per_round: int = 6,
    temperature: float = 0.35,
    chat_caller: Callable[..., ChatCompletionResult] | None = None,
    injected_provider_is_test_double: bool = False,
) -> dict[str, Any]:
    """Run Stage 8.27 or honestly block if a real LLM API is unavailable."""

    report8_26 = _read_json(Path(stage8_26_report_path))
    manifest8_26 = _read_json(Path(stage8_26_manifest_path))
    equivalence8_26 = _read_json(Path(stage8_26_equivalence_path))
    ledger8_26 = _read_json(Path(stage8_26_fe_ledger_path))
    boundary8_26 = _read_json(Path(stage8_26_runtime_boundary_path))
    route8_26 = _read_json(Path(stage8_26_next_route_path))
    _validate_stage8_26_inputs(
        report=report8_26,
        manifest=manifest8_26,
        equivalence=equivalence8_26,
        ledger=ledger8_26,
        boundary=boundary8_26,
        route=route8_26,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    prompt_context = _build_prompt_context(
        manifest=manifest8_26,
        report=report8_26,
        strategy_count_per_round=strategy_count_per_round,
        reflection_round_count=reflection_round_count,
    )
    _write_json(output_path / "reflection_prompt_context.json", prompt_context)

    preflight, config = _build_api_preflight(
        env_path=Path(env_path),
        injected_provider_is_test_double=injected_provider_is_test_double,
    )
    _write_json(output_path / "api_preflight_report.json", preflight)
    if chat_caller is None and not preflight["real_llm_api_available"]:
        return _write_blocked_outputs(
            output_path=output_path,
            preflight=preflight,
            prompt_context=prompt_context,
            inherited_stage8_26_fe_total=int(ledger8_26["FE_total"]),
        )

    caller = chat_caller
    llm_call_used = False
    real_llm_api_called = False
    if caller is None:
        if config is None:
            return _write_blocked_outputs(
                output_path=output_path,
                preflight=preflight,
                prompt_context=prompt_context,
                inherited_stage8_26_fe_total=int(ledger8_26["FE_total"]),
            )

        def caller(*, messages: Sequence[Mapping[str, str]], temperature: float) -> ChatCompletionResult:
            return call_chat_completion(config, messages=messages, temperature=temperature)

        llm_call_used = True
        real_llm_api_called = True

    try:
        execution = _run_reflection_loop(
            chat_caller=caller,
            prompt_context=prompt_context,
            reflection_round_count=reflection_round_count,
            strategy_count_per_round=strategy_count_per_round,
            temperature=temperature,
            llm_call_used=llm_call_used,
            real_llm_api_called=real_llm_api_called,
            unit_test_injected_provider_used=injected_provider_is_test_double,
            inherited_stage8_26_fe_total=int(ledger8_26["FE_total"]),
        )
    except Exception as exc:
        preflight = dict(preflight) | {
            "status": BLOCKED_STATUS,
            "real_llm_api_available": False,
            "call_error": str(exc),
        }
        _write_json(output_path / "api_preflight_report.json", preflight)
        return _write_blocked_outputs(
            output_path=output_path,
            preflight=preflight,
            prompt_context=prompt_context,
            inherited_stage8_26_fe_total=int(ledger8_26["FE_total"]),
        )

    for filename, payload in execution["json_artifacts"].items():
        _write_json(output_path / filename, payload)
    for filename, rows in execution["jsonl_artifacts"].items():
        _write_jsonl(output_path / filename, rows)
    _write_json(output_path / "llm_reflective_ownership_strategy_search_report.json", execution["report"])
    return execution["report"]


def _validate_stage8_26_inputs(
    *,
    report: Mapping[str, Any],
    manifest: Mapping[str, Any],
    equivalence: Mapping[str, Any],
    ledger: Mapping[str, Any],
    boundary: Mapping[str, Any],
    route: Mapping[str, Any],
) -> None:
    if report.get("stage") != "8.26" or report.get("status") != "PASS":
        raise ValueError("Stage 8.27 requires a passing Stage 8.26 report.")
    if report.get("behavior_equivalence_checker_implemented") is not True:
        raise ValueError("Stage 8.27 requires the Stage 8.26 checker.")
    if manifest.get("strategy_program_schema_version") != PROGRAM_SCHEMA_VERSION:
        raise ValueError("Stage 8.27 requires the Stage 8.26 strategy schema.")
    if equivalence.get("not_equivalent_to_best_reward_select") is not True:
        raise ValueError("Stage 8.27 requires a behavior-distinct Stage 8.26 gate.")
    if int(ledger.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.27 expects zero-FE Stage 8.26 input.")
    if boundary.get("llm_call_used") is not False:
        raise ValueError("Stage 8.27 refuses LLM-tainted Stage 8.26 input.")
    if route.get("next_stage") != "Stage 8.27":
        raise ValueError("Stage 8.27 requires the Stage 8.26 route.")


def _build_prompt_context(
    *,
    manifest: Mapping[str, Any],
    report: Mapping[str, Any],
    strategy_count_per_round: int,
    reflection_round_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": PROMPT_CONTEXT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "READY",
        "source_stage": "8.26",
        "prompt_scope": "ownership_aware_strategy_program_generation",
        "strategy_program_schema_version": manifest["strategy_program_schema_version"],
        "allowed_outputs": list(manifest["allowed_outputs"]),
        "allowed_coordination_actions": list(manifest["allowed_coordination_actions"]),
        "behavior_equivalence_guards": list(manifest["behavior_equivalence_guards"]),
        "stage8_26_selected_strategy_id": report["selected_strategy_id"],
        "strategy_count_per_round": int(strategy_count_per_round),
        "reflection_round_count": int(reflection_round_count),
        "output_schema": RAW_BATCH_SCHEMA_VERSION,
        "fake_llm_strategies_forbidden": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_api_preflight(
    *, env_path: Path, injected_provider_is_test_double: bool
) -> tuple[dict[str, Any], LLMClientConfig | None]:
    if injected_provider_is_test_double:
        return (
            {
                "schema_version": API_PREFLIGHT_SCHEMA_VERSION,
                "stage": STAGE,
                "status": "UNIT_TEST_PROVIDER_INJECTED",
                "real_llm_api_available": False,
                "unit_test_injected_provider_used": True,
                "missing_or_invalid": [],
                "secret_redacted": True,
            },
            None,
        )
    try:
        config = load_llm_config_from_env(env_path)
    except ValueError as exc:
        message = str(exc)
        missing = [
            key
            for key in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"]
            if key in message
        ] or ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"]
        return (
            {
                "schema_version": API_PREFLIGHT_SCHEMA_VERSION,
                "stage": STAGE,
                "status": BLOCKED_STATUS,
                "real_llm_api_available": False,
                "unit_test_injected_provider_used": False,
                "missing_or_invalid": missing,
                "secret_redacted": True,
            },
            None,
        )
    return (
        {
            "schema_version": API_PREFLIGHT_SCHEMA_VERSION,
            "stage": STAGE,
            "status": "READY",
            "real_llm_api_available": True,
            "unit_test_injected_provider_used": False,
            "base_url_host_known": True,
            "model": config.model,
            "wire_api": config.wire_api,
            "reasoning_effort": config.reasoning_effort,
            "missing_or_invalid": [],
            "secret_redacted": True,
        },
        config,
    )


def _write_blocked_outputs(
    *,
    output_path: Path,
    preflight: Mapping[str, Any],
    prompt_context: Mapping[str, Any],
    inherited_stage8_26_fe_total: int,
) -> dict[str, Any]:
    static_audit = _build_static_audit([])
    evaluator = _build_empty_evaluator()
    ledger = _build_fe_ledger(
        status=BLOCKED_STATUS,
        inherited_stage8_26_fe_total=inherited_stage8_26_fe_total,
        llm_call_used=False,
        real_llm_api_called=False,
    )
    boundary = _build_runtime_boundary(
        status=BLOCKED_STATUS,
        llm_call_used=False,
        real_llm_api_called=False,
        unit_test_injected_provider_used=False,
        fake_llm_strategies_used=False,
    )
    route = _build_blocked_route()
    report = _build_report(
        status=BLOCKED_STATUS,
        round_rows=[],
        raw_rows=[],
        accepted_rows=[],
        evaluator=evaluator,
        ledger=ledger,
        route=route,
        llm_call_used=False,
        real_llm_api_called=False,
        unit_test_injected_provider_used=False,
        fake_llm_strategies_used=False,
    ) | {
        "blocked_reason": "real LLM API credentials or call availability missing",
        "api_preflight_status": preflight["status"],
        "next_route": "WAIT_FOR_REAL_LLM_API",
    }
    _write_jsonl(output_path / "reflection_rounds.jsonl", [])
    _write_jsonl(output_path / "raw_llm_strategies.jsonl", [])
    _write_jsonl(output_path / "accepted_strategies.jsonl", [])
    _write_jsonl(output_path / "rejected_strategies.jsonl", [])
    _write_json(output_path / "static_audit_report.json", static_audit)
    _write_json(output_path / "strategy_evaluator_report.json", evaluator)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    _write_json(output_path / "llm_reflective_ownership_strategy_search_report.json", report)
    if not (output_path / "reflection_prompt_context.json").is_file():
        _write_json(output_path / "reflection_prompt_context.json", prompt_context)
    return report


def _run_reflection_loop(
    *,
    chat_caller: Callable[..., ChatCompletionResult],
    prompt_context: Mapping[str, Any],
    reflection_round_count: int,
    strategy_count_per_round: int,
    temperature: float,
    llm_call_used: bool,
    real_llm_api_called: bool,
    unit_test_injected_provider_used: bool,
    inherited_stage8_26_fe_total: int,
) -> dict[str, Any]:
    round_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    accepted_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    previous_feedback: dict[str, Any] = {"evaluated_strategy_count": 0}

    for round_index in range(1, reflection_round_count + 1):
        messages = _round_messages(
            prompt_context=prompt_context,
            round_index=round_index,
            strategy_count_per_round=strategy_count_per_round,
            previous_feedback=previous_feedback,
        )
        result = chat_caller(messages=messages, temperature=temperature)
        batch = _parse_json_object(result.content)
        strategies = _parse_raw_strategy_batch(batch)
        round_raw = 0
        round_accept = 0
        round_reject = 0
        for index, payload in enumerate(strategies):
            round_raw += 1
            raw_row = {
                "schema_version": "loco.stage8_27_raw_strategy_log.v1",
                "stage": STAGE,
                "round_index": round_index,
                "strategy_index": index,
                "strategy_payload": payload,
                "decision": "raw",
            }
            raw_rows.append(raw_row)
            try:
                program = load_strategy_program(payload)
            except ValueError as exc:
                rejected_rows.append(
                    raw_row | {"decision": "rejected", "reject_reason": str(exc)}
                )
                round_reject += 1
                continue
            accepted_rows.append(
                raw_row
                | {
                    "decision": "accepted",
                    "strategy_id": program.strategy_id,
                    "origin": program.origin,
                    "family": program.family,
                }
            )
            round_accept += 1

        evaluator = _evaluate_accepted_rows(accepted_rows)
        previous_feedback = {
            "evaluated_strategy_count": evaluator["evaluated_strategy_count"],
            "selected_strategy_id": evaluator.get("selected_strategy_id"),
            "failure_summary": evaluator.get("failure_summary", []),
        }
        round_rows.append(
            {
                "schema_version": ROUND_SCHEMA_VERSION,
                "stage": STAGE,
                "round_index": round_index,
                "raw_strategy_count": round_raw,
                "accepted_strategy_count": round_accept,
                "rejected_strategy_count": round_reject,
                "feedback_from_previous_round": (
                    {"evaluated_strategy_count": 0}
                    if round_index == 1
                    else previous_feedback
                ),
                "provider_model": result.provenance.get("model"),
                "secret_redacted": True,
                "unit_test_injected_provider_used": unit_test_injected_provider_used,
            }
        )

    static_audit = _build_static_audit(accepted_rows)
    evaluator = _evaluate_accepted_rows(accepted_rows)
    status = PASS_STATUS if evaluator.get("selected_strategy_id") else "FAIL"
    ledger = _build_fe_ledger(
        status=status,
        inherited_stage8_26_fe_total=inherited_stage8_26_fe_total,
        llm_call_used=llm_call_used,
        real_llm_api_called=real_llm_api_called,
    )
    boundary = _build_runtime_boundary(
        status=status,
        llm_call_used=llm_call_used,
        real_llm_api_called=real_llm_api_called,
        unit_test_injected_provider_used=unit_test_injected_provider_used,
        fake_llm_strategies_used=False,
    )
    route = _build_pass_route() if status == PASS_STATUS else _build_failed_route()
    report = _build_report(
        status=status,
        round_rows=round_rows,
        raw_rows=raw_rows,
        accepted_rows=accepted_rows,
        evaluator=evaluator,
        ledger=ledger,
        route=route,
        llm_call_used=llm_call_used,
        real_llm_api_called=real_llm_api_called,
        unit_test_injected_provider_used=unit_test_injected_provider_used,
        fake_llm_strategies_used=False,
    )
    return {
        "report": report,
        "json_artifacts": {
            "static_audit_report.json": static_audit,
            "strategy_evaluator_report.json": evaluator,
            "fe_ledger.json": ledger,
            "runtime_boundary.json": boundary,
            "next_route_decision.json": route,
        },
        "jsonl_artifacts": {
            "reflection_rounds.jsonl": round_rows,
            "raw_llm_strategies.jsonl": raw_rows,
            "accepted_strategies.jsonl": accepted_rows,
            "rejected_strategies.jsonl": rejected_rows,
        },
    }


def _round_messages(
    *,
    prompt_context: Mapping[str, Any],
    round_index: int,
    strategy_count_per_round: int,
    previous_feedback: Mapping[str, Any],
) -> list[dict[str, str]]:
    system = (
        "You design bounded LOCO-LSGO ownership-aware coordination strategy "
        "programs. Return JSON only. Do not generate optimizers, schedulers, "
        "controllers, DE, CMA-ES, PSO, SHADE, or benchmark objectives."
    )
    user = {
        "task": "Generate ownership-aware shared-variable coordination strategy programs.",
        "stage": STAGE,
        "round_index": round_index,
        "strategy_count": strategy_count_per_round,
        "allowed_outputs": prompt_context["allowed_outputs"],
        "allowed_coordination_actions": prompt_context["allowed_coordination_actions"],
        "behavior_equivalence_guards": prompt_context["behavior_equivalence_guards"],
        "previous_feedback": dict(previous_feedback),
        "required_output_schema": {
            "schema_version": RAW_BATCH_SCHEMA_VERSION,
            "stage": STAGE,
            "strategies": [
                {
                    "schema_version": PROGRAM_SCHEMA_VERSION,
                    "strategy_id": "stage8_27_example",
                    "origin": "llm_reflective_generated",
                    "family": "ownership_aware_conflict_guard",
                    "rules": [
                        {
                            "condition": "conflicting_overlap AND high_owner_regret",
                            "shared_variable_owner": "contribution_leader",
                            "allow_multi_assignment": False,
                            "linkage_decision": "break",
                            "coordination_action": "owner_proposal_select",
                            "fallback_repair_action": "shrinkage_repair",
                        }
                    ],
                }
            ],
        },
        "instruction": "Return JSON only, with no markdown and no explanation.",
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, indent=2, sort_keys=True)},
    ]


def _parse_raw_strategy_batch(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if payload.get("schema_version") != RAW_BATCH_SCHEMA_VERSION:
        raise ValueError("unsupported Stage 8.27 raw strategy batch schema")
    if payload.get("stage") != STAGE:
        raise ValueError("raw strategy batch must declare stage 8.27")
    strategies = payload.get("strategies")
    if not isinstance(strategies, list):
        raise ValueError("raw strategy batch must contain strategies list")
    return [dict(strategy) for strategy in strategies]


def _evaluate_accepted_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    candidate_rows = []
    for row in rows:
        program = load_strategy_program(row["strategy_payload"])
        evaluation = evaluate_strategy_program(program)
        candidate_rows.append(
            {
                "strategy_id": program.strategy_id,
                "origin": program.origin,
                "family": program.family,
                "gate_passed": evaluation["gate_passed"],
                "not_equivalent_to_best_reward_select": evaluation[
                    "behavior_equivalence_report"
                ]["not_equivalent_to_best_reward_select"],
                "non_trust_branch_exercised": evaluation["branch_coverage_report"][
                    "non_trust_branch_exercised"
                ],
                "ownership_or_linkage_decision_exercised": evaluation[
                    "ownership_decision_coverage_report"
                ]["ownership_or_linkage_decision_exercised"],
                "win_count_vs_best_reward": evaluation["train_side_win_loss_report"][
                    "win_count_vs_best_reward"
                ],
                "loss_count_vs_best_reward": evaluation["train_side_win_loss_report"][
                    "loss_count_vs_best_reward"
                ],
                "mean_delta_vs_best_reward": evaluation["train_side_win_loss_report"][
                    "mean_delta_vs_best_reward"
                ],
            }
        )
    passing = [row for row in candidate_rows if bool(row["gate_passed"])]
    selected = (
        sorted(
            passing,
            key=lambda row: (
                int(row["loss_count_vs_best_reward"]),
                -int(row["win_count_vs_best_reward"]),
                float(row["mean_delta_vs_best_reward"]),
                str(row["strategy_id"]),
            ),
        )[0]
        if passing
        else None
    )
    return {
        "schema_version": EVALUATOR_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS if selected else "FAIL",
        "evaluated_strategy_count": len(candidate_rows),
        "candidate_rows": candidate_rows,
        "selected_strategy_id": None if selected is None else selected["strategy_id"],
        "selected_strategy_origin": None if selected is None else selected["origin"],
        "selected_strategy_family": None if selected is None else selected["family"],
        "selected_strategy_not_equivalent_to_best_reward_select": bool(
            selected and selected["not_equivalent_to_best_reward_select"]
        ),
        "non_trust_branch_exercised": bool(
            selected and selected["non_trust_branch_exercised"]
        ),
        "ownership_or_linkage_decision_exercised": bool(
            selected and selected["ownership_or_linkage_decision_exercised"]
        ),
        "train_side_win_count_vs_best_reward": (
            0 if selected is None else int(selected["win_count_vs_best_reward"])
        ),
        "train_side_loss_count_vs_best_reward": (
            0 if selected is None else int(selected["loss_count_vs_best_reward"])
        ),
        "failure_summary": [
            row["strategy_id"] for row in candidate_rows if not bool(row["gate_passed"])
        ][:5],
        "FE_total": 0,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_static_audit(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    families = sorted({str(row.get("family")) for row in rows if row.get("family")})
    return {
        "schema_version": STATIC_AUDIT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS if rows else BLOCKED_STATUS,
        "accepted_strategy_count": len(rows),
        "strategy_family_count": len(families),
        "strategy_families": families,
        "fake_llm_strategies_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_empty_evaluator() -> dict[str, Any]:
    return {
        "schema_version": EVALUATOR_SCHEMA_VERSION,
        "stage": STAGE,
        "status": BLOCKED_STATUS,
        "evaluated_strategy_count": 0,
        "candidate_rows": [],
        "selected_strategy_id": None,
        "selected_strategy_origin": None,
        "selected_strategy_not_equivalent_to_best_reward_select": False,
        "non_trust_branch_exercised": False,
        "ownership_or_linkage_decision_exercised": False,
        "train_side_win_count_vs_best_reward": 0,
        "train_side_loss_count_vs_best_reward": 0,
        "FE_total": 0,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(
    *,
    status: str,
    inherited_stage8_26_fe_total: int,
    llm_call_used: bool,
    real_llm_api_called: bool,
) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": status,
        "budget_scope": "llm_reflective_ownership_strategy_search",
        "inherited_stage8_26_FE_total": int(inherited_stage8_26_fe_total),
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": bool(llm_call_used),
        "real_llm_api_called": bool(real_llm_api_called),
        "all_extra_fe_counted": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary(
    *,
    status: str,
    llm_call_used: bool,
    real_llm_api_called: bool,
    unit_test_injected_provider_used: bool,
    fake_llm_strategies_used: bool,
) -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": status,
        "claim_scope": "real LLM reflective ownership-aware strategy search",
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": bool(llm_call_used),
        "real_llm_api_called": bool(real_llm_api_called),
        "unit_test_injected_provider_used": bool(unit_test_injected_provider_used),
        "new_llm_strategy_generation_used": bool(real_llm_api_called),
        "fake_llm_strategies_used": bool(fake_llm_strategies_used),
        "selected_policy_revision_used": False,
        "evolution_search_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_pass_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "decision": "ROUTE_TO_STAGE8_28_LLM_VS_NON_LLM_ABLATION",
        "next_stage": "Stage 8.28",
        "allowed_next_work": "llm_vs_non_llm_ownership_strategy_ablation",
        "run_cec_checkpoint_next": False,
        "run_full_25_run_panel_next": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_failed_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "FAIL",
        "decision": "REPAIR_STAGE8_27_PROMPT_OR_EVALUATOR",
        "next_stage": "Stage 8.27",
        "allowed_next_work": "repair_llm_reflective_ownership_strategy_search",
        "next_route": "REPAIR_STAGE8_27",
        "run_full_25_run_panel_next": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_blocked_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": BLOCKED_STATUS,
        "decision": "WAIT_FOR_REAL_LLM_API",
        "next_stage": "Stage 8.27",
        "allowed_next_work": "provide_real_llm_api_and_rerun_stage8_27",
        "next_route": "WAIT_FOR_REAL_LLM_API",
        "run_full_25_run_panel_next": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    status: str,
    round_rows: Sequence[Mapping[str, Any]],
    raw_rows: Sequence[Mapping[str, Any]],
    accepted_rows: Sequence[Mapping[str, Any]],
    evaluator: Mapping[str, Any],
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
    llm_call_used: bool,
    real_llm_api_called: bool,
    unit_test_injected_provider_used: bool,
    fake_llm_strategies_used: bool,
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": status,
        "source_stage": "8.26",
        "execution_scope": "real_llm_reflective_ownership_aware_strategy_search",
        "reflection_round_count": len(round_rows),
        "raw_llm_strategy_count": len(raw_rows),
        "accepted_strategy_count": len(accepted_rows),
        "selected_strategy_id": evaluator.get("selected_strategy_id"),
        "selected_strategy_origin": evaluator.get("selected_strategy_origin"),
        "selected_strategy_not_equivalent_to_best_reward_select": evaluator.get(
            "selected_strategy_not_equivalent_to_best_reward_select"
        ),
        "non_trust_branch_exercised": evaluator.get("non_trust_branch_exercised"),
        "ownership_or_linkage_decision_exercised": evaluator.get(
            "ownership_or_linkage_decision_exercised"
        ),
        "train_side_win_count_vs_best_reward": evaluator.get(
            "train_side_win_count_vs_best_reward"
        ),
        "train_side_loss_count_vs_best_reward": evaluator.get(
            "train_side_loss_count_vs_best_reward"
        ),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": bool(llm_call_used),
        "real_llm_api_called": bool(real_llm_api_called),
        "new_llm_strategy_generation_used": bool(real_llm_api_called),
        "unit_test_injected_provider_used": bool(unit_test_injected_provider_used),
        "fake_llm_strategies_used": bool(fake_llm_strategies_used),
        "FE_total": int(ledger["FE_total"]),
        "recommended_next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
        "selected_policy_revision_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )

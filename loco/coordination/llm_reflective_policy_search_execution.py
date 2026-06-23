"""Stage 8.20 LLM-reflective coordination policy search execution.

This stage executes the Stage 8.19 design lock when a real LLM API is
available. If the API is unavailable, it writes an honest blocked artifact set
instead of fabricating LLM candidates. Unit tests may inject a provider to
exercise the execution path; that path is explicitly marked as a test double
and is not treated as a real LLM API call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from loco.conflict.conflict_state import GroupProposal, SharedVariableConflictState
from loco.coordination.baselines import (
    AverageConsensus,
    BestRewardSelection,
    CoordinationResult,
    WeightedConsensus,
)
from loco.llm.api_candidate_generator import _parse_json_object
from loco.llm.provider_client import (
    ChatCompletionResult,
    LLMClientConfig,
    call_chat_completion,
    load_llm_config_from_env,
)


STAGE = "8.20"
RAW_BATCH_SCHEMA_VERSION = "loco.stage8_20_raw_policy_batch.v1"
POLICY_SCHEMA_VERSION = "loco.stage8_20_coordination_policy_program.v1"
REPORT_SCHEMA_VERSION = "loco.stage8_20_llm_reflective_search_report.v1"
API_PREFLIGHT_SCHEMA_VERSION = "loco.stage8_20_api_preflight_report.v1"
PROMPT_CONTEXT_SCHEMA_VERSION = "loco.stage8_20_reflection_prompt_context.v1"
ROUND_SCHEMA_VERSION = "loco.stage8_20_reflection_round.v1"
CANDIDATE_LOG_SCHEMA_VERSION = "loco.stage8_20_candidate_log.v1"
STATIC_AUDIT_SCHEMA_VERSION = "loco.stage8_20_static_audit_report.v1"
EVALUATOR_SCHEMA_VERSION = "loco.stage8_20_candidate_evaluator_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_20_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_20_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_20_next_route_decision.v1"

PASS_STATUS = "PASS"
BLOCKED_STATUS = "BLOCKED_NEEDS_REAL_LLM_API"
NEXT_PASS_STAGE = "Stage 8.21"
NEXT_PASS_WORK = "llm_vs_non_llm_contribution_ablation"


@dataclass(frozen=True)
class _PolicyProgram:
    policy_id: str
    origin: str
    family: str
    target_scope: str
    features: tuple[str, ...]
    memory: tuple[str, ...]
    rules: tuple[Mapping[str, str], ...]
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class _TrainCase:
    case_id: str
    regime: str
    initial_value: float
    target_value: float
    proposals: tuple[float, ...]
    rewards: tuple[float, ...]
    bounds: tuple[float, float] = (-100.0, 100.0)
    variable_id: int = 7


def run_stage8_20_llm_reflective_policy_search_execution(
    *,
    stage8_19_design_path: Path | str,
    stage8_19_prompt_contract_path: Path | str,
    stage8_19_dsl_contract_path: Path | str,
    stage8_19_ablation_plan_path: Path | str,
    stage8_19_gate_path: Path | str,
    stage8_19_fe_ledger_path: Path | str,
    stage8_19_runtime_boundary_path: Path | str,
    stage8_19_next_route_path: Path | str,
    output_dir: Path | str,
    env_path: Path | str,
    reflection_round_count: int | None = None,
    candidate_count_per_round: int = 12,
    temperature: float = 0.35,
    chat_caller: Callable[..., ChatCompletionResult] | None = None,
    injected_provider_is_test_double: bool = False,
) -> dict[str, Any]:
    """Run or honestly block Stage 8.20."""

    design = _read_json(Path(stage8_19_design_path))
    prompt_contract = _read_json(Path(stage8_19_prompt_contract_path))
    dsl_contract = _read_json(Path(stage8_19_dsl_contract_path))
    ablation_plan = _read_json(Path(stage8_19_ablation_plan_path))
    gate = _read_json(Path(stage8_19_gate_path))
    fe_ledger_819 = _read_json(Path(stage8_19_fe_ledger_path))
    runtime_boundary = _read_json(Path(stage8_19_runtime_boundary_path))
    next_route = _read_json(Path(stage8_19_next_route_path))
    _validate_stage8_19_inputs(
        design=design,
        prompt_contract=prompt_contract,
        dsl_contract=dsl_contract,
        ablation_plan=ablation_plan,
        gate=gate,
        fe_ledger=fe_ledger_819,
        runtime_boundary=runtime_boundary,
        next_route=next_route,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    rounds_required = int(
        reflection_round_count
        or prompt_contract.get("minimum_reflection_round_count", 2)
    )
    prompt_context = _build_prompt_context(
        design=design,
        prompt_contract=prompt_contract,
        dsl_contract=dsl_contract,
        gate=gate,
        candidate_count_per_round=candidate_count_per_round,
        reflection_round_count=rounds_required,
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
            inherited_stage8_19_fe_total=int(fe_ledger_819["FE_total"]),
        )

    caller = chat_caller
    real_llm_api_called = False
    llm_call_used = False
    if caller is None:
        if config is None:
            return _write_blocked_outputs(
                output_path=output_path,
                preflight=preflight,
                prompt_context=prompt_context,
                inherited_stage8_19_fe_total=int(fe_ledger_819["FE_total"]),
            )

        def caller(*, messages: Sequence[Mapping[str, str]], temperature: float) -> ChatCompletionResult:
            return call_chat_completion(config, messages=messages, temperature=temperature)

        real_llm_api_called = True
        llm_call_used = True

    try:
        execution = _run_reflection_loop(
            chat_caller=caller,
            prompt_context=prompt_context,
            dsl_contract=dsl_contract,
            gate=gate,
            reflection_round_count=rounds_required,
            candidate_count_per_round=candidate_count_per_round,
            temperature=float(temperature),
            unit_test_injected_provider_used=bool(injected_provider_is_test_double),
            real_llm_api_called=real_llm_api_called,
            llm_call_used=llm_call_used,
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
            inherited_stage8_19_fe_total=int(fe_ledger_819["FE_total"]),
        )

    for filename, payload in execution["json_artifacts"].items():
        _write_json(output_path / filename, payload)
    for filename, rows in execution["jsonl_artifacts"].items():
        _write_jsonl(output_path / filename, rows)

    report = _build_pass_report(
        execution=execution,
        inherited_stage8_19_fe_total=int(fe_ledger_819["FE_total"]),
    )
    _write_json(output_path / "llm_reflective_search_report.json", report)
    return report


def _validate_stage8_19_inputs(
    *,
    design: Mapping[str, Any],
    prompt_contract: Mapping[str, Any],
    dsl_contract: Mapping[str, Any],
    ablation_plan: Mapping[str, Any],
    gate: Mapping[str, Any],
    fe_ledger: Mapping[str, Any],
    runtime_boundary: Mapping[str, Any],
    next_route: Mapping[str, Any],
) -> None:
    if design.get("stage") != "8.19" or design.get("status") != "PASS":
        raise ValueError("Stage 8.20 requires a passing Stage 8.19 design report.")
    if design.get("required_future_llm_call") is not True:
        raise ValueError("Stage 8.19 must require a future LLM call.")
    if prompt_contract.get("real_llm_api_required_for_execution") is not True:
        raise ValueError("Stage 8.20 requires the Stage 8.19 real-API contract.")
    if prompt_contract.get("fake_llm_candidates_forbidden") is not True:
        raise ValueError("Stage 8.20 refuses fake LLM candidate contracts.")
    if dsl_contract.get("target_scope") != "shared_variables_only":
        raise ValueError("Stage 8.20 only accepts shared-variable policy DSL.")
    if ablation_plan.get("llm_vs_non_llm_ablation_required") is not True:
        raise ValueError("Stage 8.20 requires the LLM contribution ablation plan.")
    if gate.get("win_count_vs_best_reward_select_min") != 1:
        raise ValueError("Stage 8.20 requires the beat-best_reward gate.")
    if int(fe_ledger.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.20 requires zero-FE Stage 8.19 design input.")
    if runtime_boundary.get("required_future_behaviors", {}).get(
        "real_llm_api_call_for_execution"
    ) is not True:
        raise ValueError("Stage 8.19 runtime boundary did not require real LLM.")
    if next_route.get("next_stage") != "Stage 8.20":
        raise ValueError("Stage 8.20 requires the Stage 8.19 next-route decision.")


def _build_prompt_context(
    *,
    design: Mapping[str, Any],
    prompt_contract: Mapping[str, Any],
    dsl_contract: Mapping[str, Any],
    gate: Mapping[str, Any],
    candidate_count_per_round: int,
    reflection_round_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": PROMPT_CONTEXT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "READY",
        "source_stage": "8.19",
        "prompt_scope": prompt_contract["prompt_scope"],
        "design_scope": design["design_scope"],
        "failure_patterns_used": list(prompt_contract["failure_patterns_used"]),
        "allowed_features": list(dsl_contract["allowed_features"]),
        "allowed_actions": list(dsl_contract["allowed_actions"]),
        "allowed_memory": list(dsl_contract["allowed_memory"]),
        "forbidden_capabilities": list(dsl_contract["forbidden_capabilities"]),
        "candidate_count_per_round": int(candidate_count_per_round),
        "reflection_round_count": int(reflection_round_count),
        "beat_best_reward_gate": {
            "win_count_vs_best_reward_select_min": int(
                gate["win_count_vs_best_reward_select_min"]
            ),
            "loss_count_vs_best_reward_select_max": int(
                gate["loss_count_vs_best_reward_select_max"]
            ),
            "non_trust_best_reward_branch_exercised_required": bool(
                gate["non_trust_best_reward_branch_exercised_required"]
            ),
        },
        "output_schema": RAW_BATCH_SCHEMA_VERSION,
        "fake_llm_candidates_forbidden": True,
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
        ]
        if not missing:
            missing = ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"]
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
    inherited_stage8_19_fe_total: int,
) -> dict[str, Any]:
    empty_static = _build_static_audit_report([], [])
    empty_evaluator = _build_empty_evaluator_report()
    ledger = _build_fe_ledger(
        status=BLOCKED_STATUS,
        trace_rows=[],
        llm_call_used=False,
        real_llm_api_called=False,
        inherited_stage8_19_fe_total=inherited_stage8_19_fe_total,
    )
    boundary = _build_runtime_boundary(
        status=BLOCKED_STATUS,
        objective_loop_executed=False,
        new_objective_evaluation_used=False,
        llm_call_used=False,
        real_llm_api_called=False,
        unit_test_injected_provider_used=False,
    )
    route = _build_blocked_route()
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": BLOCKED_STATUS,
        "source_stage": "8.19",
        "execution_scope": "llm_reflective_coordination_policy_search_execution",
        "blocked_reason": "real LLM API credentials or call availability missing",
        "llm_call_used": False,
        "real_llm_api_called": False,
        "new_llm_candidate_generation_used": False,
        "unit_test_injected_provider_used": False,
        "fake_llm_candidates_used": False,
        "reflection_round_count": 0,
        "raw_llm_candidate_count": 0,
        "quality_pass_candidate_count": 0,
        "coordination_family_count": 0,
        "selected_candidate_id": None,
        "selected_candidate_origin": None,
        "selected_candidate_not_equivalent_to_best_reward": False,
        "non_trust_best_reward_branch_exercised": False,
        "train_objective_win_count_vs_best_reward": 0,
        "train_objective_loss_count_vs_best_reward": 0,
        "objective_evaluator_feedback_used": False,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "FE_total": 0,
        "api_preflight_status": preflight["status"],
        "next_route": "WAIT_FOR_REAL_LLM_API",
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }
    _write_jsonl(output_path / "reflection_rounds.jsonl", [])
    _write_jsonl(output_path / "raw_llm_candidates.jsonl", [])
    _write_jsonl(output_path / "accepted_candidates.jsonl", [])
    _write_jsonl(output_path / "rejected_candidates.jsonl", [])
    _write_json(output_path / "static_audit_report.json", empty_static)
    _write_json(output_path / "candidate_evaluator_report.json", empty_evaluator)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    _write_json(output_path / "llm_reflective_search_report.json", report)
    if not (output_path / "reflection_prompt_context.json").is_file():
        _write_json(output_path / "reflection_prompt_context.json", prompt_context)
    return report


def _run_reflection_loop(
    *,
    chat_caller: Callable[..., ChatCompletionResult],
    prompt_context: Mapping[str, Any],
    dsl_contract: Mapping[str, Any],
    gate: Mapping[str, Any],
    reflection_round_count: int,
    candidate_count_per_round: int,
    temperature: float,
    unit_test_injected_provider_used: bool,
    real_llm_api_called: bool,
    llm_call_used: bool,
) -> dict[str, Any]:
    raw_rows: list[dict[str, Any]] = []
    accepted_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    round_rows: list[dict[str, Any]] = []
    previous_feedback: dict[str, Any] = {"evaluated_candidate_count": 0}

    for round_index in range(1, reflection_round_count + 1):
        messages = _round_messages(
            prompt_context=prompt_context,
            round_index=round_index,
            candidate_count_per_round=candidate_count_per_round,
            previous_feedback=previous_feedback,
        )
        result = chat_caller(messages=messages, temperature=temperature)
        batch = _parse_json_object(result.content)
        policies = _parse_raw_policy_batch(batch)
        round_raw_count = 0
        round_accept_count = 0
        round_reject_count = 0
        for index, policy_payload in enumerate(policies):
            round_raw_count += 1
            raw_row = _candidate_row(
                round_index=round_index,
                candidate_index=index,
                policy_payload=policy_payload,
                decision="raw",
            )
            raw_rows.append(raw_row)
            try:
                policy = _load_policy_program(policy_payload)
                _audit_policy(policy, dsl_contract)
            except ValueError as exc:
                rejected_rows.append(
                    raw_row
                    | {
                        "decision": "rejected",
                        "reject_reason": str(exc),
                    }
                )
                round_reject_count += 1
                continue
            accepted_rows.append(
                raw_row
                | {
                    "decision": "accepted",
                    "policy_id": policy.policy_id,
                    "family": policy.family,
                    "origin": policy.origin,
                    "action_set": _policy_action_set(policy),
                }
            )
            round_accept_count += 1

        current_eval = _evaluate_policies(
            [_load_policy_program(row["policy_payload"]) for row in accepted_rows]
        )
        previous_feedback = {
            "evaluated_candidate_count": current_eval["evaluated_candidate_count"],
            "best_candidate_id": current_eval.get("selected_candidate_id"),
            "best_candidate_delta_vs_best_reward": current_eval.get(
                "selected_candidate_delta_vs_best_reward"
            ),
            "failure_summary": current_eval.get("failure_summary", []),
        }
        round_rows.append(
            {
                "schema_version": ROUND_SCHEMA_VERSION,
                "stage": STAGE,
                "round_index": round_index,
                "raw_candidate_count": round_raw_count,
                "accepted_candidate_count": round_accept_count,
                "rejected_candidate_count": round_reject_count,
                "feedback_from_previous_round": (
                    {"evaluated_candidate_count": 0}
                    if round_index == 1
                    else previous_feedback
                ),
                "provider_model": result.provenance.get("model"),
                "secret_redacted": True,
                "unit_test_injected_provider_used": unit_test_injected_provider_used,
            }
        )

    accepted_policies = [_load_policy_program(row["policy_payload"]) for row in accepted_rows]
    static_audit = _build_static_audit_report(accepted_rows, rejected_rows)
    evaluator = _evaluate_policies(accepted_policies)
    gate_pass = _gate_passes(evaluator=evaluator, gate=gate, static_audit=static_audit)
    status = PASS_STATUS if gate_pass else "FAIL"
    trace_rows = evaluator["evaluation_trace_rows"]
    ledger = _build_fe_ledger(
        status=status,
        trace_rows=trace_rows,
        llm_call_used=llm_call_used,
        real_llm_api_called=real_llm_api_called,
        inherited_stage8_19_fe_total=0,
    )
    boundary = _build_runtime_boundary(
        status=status,
        objective_loop_executed=True,
        new_objective_evaluation_used=True,
        llm_call_used=llm_call_used,
        real_llm_api_called=real_llm_api_called,
        unit_test_injected_provider_used=unit_test_injected_provider_used,
    )
    route = _build_pass_route() if gate_pass else _build_failed_route()
    evaluator = dict(evaluator)
    evaluator.pop("evaluation_trace_rows")
    evaluator["status"] = status
    return {
        "status": status,
        "round_rows": round_rows,
        "raw_rows": raw_rows,
        "accepted_rows": accepted_rows,
        "rejected_rows": rejected_rows,
        "static_audit": static_audit,
        "evaluator": evaluator,
        "ledger": ledger,
        "boundary": boundary,
        "route": route,
        "trace_rows": trace_rows,
        "llm_call_used": llm_call_used,
        "real_llm_api_called": real_llm_api_called,
        "unit_test_injected_provider_used": unit_test_injected_provider_used,
        "json_artifacts": {
            "static_audit_report.json": static_audit,
            "candidate_evaluator_report.json": evaluator,
            "fe_ledger.json": ledger,
            "runtime_boundary.json": boundary,
            "next_route_decision.json": route,
        },
        "jsonl_artifacts": {
            "reflection_rounds.jsonl": round_rows,
            "raw_llm_candidates.jsonl": raw_rows,
            "accepted_candidates.jsonl": accepted_rows,
            "rejected_candidates.jsonl": rejected_rows,
            "candidate_evaluation_trace.jsonl": trace_rows,
        },
    }


def _round_messages(
    *,
    prompt_context: Mapping[str, Any],
    round_index: int,
    candidate_count_per_round: int,
    previous_feedback: Mapping[str, Any],
) -> list[dict[str, str]]:
    system = (
        "You design bounded LOCO-LSGO shared-variable coordination policy "
        "programs only. Do not generate optimizers, schedulers, controllers, "
        "BaseOpt changes, benchmark objectives, or validation/test feedback. "
        "Return JSON only, with no markdown and no explanatory prose."
    )
    user = {
        "round_index": round_index,
        "candidate_count": candidate_count_per_round,
        "required_output_schema": RAW_BATCH_SCHEMA_VERSION,
        "policy_schema": POLICY_SCHEMA_VERSION,
        "allowed_actions": prompt_context["allowed_actions"],
        "allowed_features": prompt_context["allowed_features"],
        "failure_patterns": prompt_context["failure_patterns_used"],
        "previous_feedback": dict(previous_feedback),
        "required_json_skeleton": {
            "schema_version": RAW_BATCH_SCHEMA_VERSION,
            "stage": STAGE,
            "source": {
                "provider": "deepseek",
                "model": "deepseek-v4-pro",
                "captured_by": "Stage 8.20 LLM-reflective policy search",
            },
            "policies": [
                {
                    "schema_version": POLICY_SCHEMA_VERSION,
                    "policy_id": "stage8_20_round_candidate_unique_id",
                    "origin": "llm_reflective_generated",
                    "family": "short_descriptive_family_name",
                    "target_scope": "shared_variables_only",
                    "features": list(prompt_context["allowed_features"]),
                    "memory": ["recent_best_reward_regret"],
                    "rules": [
                        {
                            "condition": "best_reward_trustworthy",
                            "action": "trust_best_reward",
                        },
                        {
                            "condition": "low_reward_margin",
                            "action": "weighted_consensus",
                        },
                        {"condition": "always", "action": "simple_consensus"},
                    ],
                    "forbidden_capabilities_used": [],
                }
            ],
        },
        "hard_requirements": [
            "Return JSON only.",
            "The top-level object must contain schema_version, stage, source, and policies.",
            "Each policy must contain schema_version, policy_id, origin, family, target_scope, features, memory, rules, and forbidden_capabilities_used.",
            "Every rule must contain condition and action.",
            "Use only allowed actions and allowed features.",
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, sort_keys=True)},
    ]


def _parse_raw_policy_batch(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if payload.get("schema_version") != RAW_BATCH_SCHEMA_VERSION:
        raise ValueError("unsupported Stage 8.20 raw policy batch schema_version")
    if payload.get("stage") != STAGE:
        raise ValueError("Stage 8.20 raw policy batch stage must be 8.20")
    policies = payload.get("policies")
    if not isinstance(policies, list) or not policies:
        raise ValueError("Stage 8.20 raw policy batch must contain policies.")
    return policies


def _load_policy_program(payload: Mapping[str, Any]) -> _PolicyProgram:
    if payload.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise ValueError("unsupported Stage 8.20 policy schema_version")
    policy_id = _require_str(payload, "policy_id")
    origin = _require_str(payload, "origin")
    family = _require_str(payload, "family")
    target_scope = _require_str(payload, "target_scope")
    features = payload.get("features")
    memory = payload.get("memory", [])
    rules = payload.get("rules")
    if not isinstance(features, list) or not all(isinstance(v, str) for v in features):
        raise ValueError("policy features must be a list of strings")
    if not isinstance(memory, list) or not all(isinstance(v, str) for v in memory):
        raise ValueError("policy memory must be a list of strings")
    if not isinstance(rules, list) or not rules:
        raise ValueError("policy rules must be a non-empty list")
    for rule in rules:
        if not isinstance(rule, Mapping):
            raise ValueError("policy rule must be a mapping")
        _require_str(rule, "condition")
        _require_str(rule, "action")
    return _PolicyProgram(
        policy_id=policy_id,
        origin=origin,
        family=family,
        target_scope=target_scope,
        features=tuple(features),
        memory=tuple(memory),
        rules=tuple(rules),
        payload=dict(payload),
    )


def _audit_policy(policy: _PolicyProgram, dsl_contract: Mapping[str, Any]) -> None:
    allowed_features = set(map(str, dsl_contract["allowed_features"]))
    allowed_actions = set(map(str, dsl_contract["allowed_actions"]))
    allowed_memory = set(map(str, dsl_contract["allowed_memory"]))
    forbidden = set(map(str, dsl_contract["forbidden_capabilities"]))
    if policy.origin != "llm_reflective_generated":
        raise ValueError("policy origin must be llm_reflective_generated")
    if policy.target_scope != "shared_variables_only":
        raise ValueError("policy target_scope must be shared_variables_only")
    unknown_features = sorted(set(policy.features) - allowed_features)
    if unknown_features:
        raise ValueError(f"unknown policy features: {unknown_features}")
    unknown_memory = sorted(set(policy.memory) - allowed_memory)
    if unknown_memory:
        raise ValueError(f"unknown policy memory: {unknown_memory}")
    actions = _policy_action_set(policy)
    unknown_actions = sorted(set(actions) - allowed_actions)
    if unknown_actions:
        raise ValueError(f"unknown policy actions: {unknown_actions}")
    forbidden_used = set(map(str, policy.payload.get("forbidden_capabilities_used", [])))
    if forbidden_used & forbidden:
        raise ValueError("policy uses forbidden capabilities")


def _policy_action_set(policy: _PolicyProgram) -> list[str]:
    return sorted({str(rule["action"]) for rule in policy.rules})


def _candidate_row(
    *,
    round_index: int,
    candidate_index: int,
    policy_payload: Mapping[str, Any],
    decision: str,
) -> dict[str, Any]:
    return {
        "schema_version": CANDIDATE_LOG_SCHEMA_VERSION,
        "stage": STAGE,
        "round_index": int(round_index),
        "candidate_index": int(candidate_index),
        "candidate_id": str(policy_payload.get("policy_id", f"candidate_{candidate_index}")),
        "decision": decision,
        "policy_payload": dict(policy_payload),
        "origin": policy_payload.get("origin"),
        "target_scope": policy_payload.get("target_scope"),
        "fake_llm_candidate": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_static_audit_report(
    accepted_rows: Sequence[Mapping[str, Any]],
    rejected_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    families = sorted({str(row.get("family")) for row in accepted_rows})
    return {
        "schema_version": STATIC_AUDIT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "raw_candidate_count": len(accepted_rows) + len(rejected_rows),
        "quality_pass_candidate_count": len(accepted_rows),
        "rejected_candidate_count": len(rejected_rows),
        "coordination_family_count": len(families),
        "coordination_families": families,
        "fake_llm_candidates_used": False,
        "static_audit_required": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _evaluate_policies(policies: Sequence[_PolicyProgram]) -> dict[str, Any]:
    cases = _train_cases()
    trace_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for policy in policies:
        branch_counts: dict[str, int] = {}
        wins = ties = losses = 0
        final_deltas = []
        for case in cases:
            best_reward_value, best_reward_objective = _run_baseline_case(case)
            policy_value, branch = _run_policy_case(policy, case)
            policy_objective = _objective(policy_value, case.target_value)
            delta = round(policy_objective - best_reward_objective, 12)
            result = _compare(policy_objective, best_reward_objective)
            wins += int(result == "win")
            ties += int(result == "tie")
            losses += int(result == "loss")
            final_deltas.append(delta)
            branch_counts[branch] = branch_counts.get(branch, 0) + 1
            trace_rows.append(
                {
                    "schema_version": "loco.stage8_20_candidate_evaluation_trace.v1",
                    "stage": STAGE,
                    "candidate_id": policy.policy_id,
                    "case_id": case.case_id,
                    "regime": case.regime,
                    "policy_branch": branch,
                    "policy_value": round(policy_value, 12),
                    "best_reward_value": round(best_reward_value, 12),
                    "policy_objective": round(policy_objective, 12),
                    "best_reward_objective": round(best_reward_objective, 12),
                    "delta_vs_best_reward": delta,
                    "result_vs_best_reward": result,
                    "FE_grouping": 0,
                    "FE_proposal": 1,
                    "FE_coordination_extra": 0,
                    "FE_repair": 0,
                    "FE_global_objective": 2,
                    "FE_total": 3,
                    "objective_loop_executed": True,
                    "new_objective_evaluation_used": True,
                    "validation_feedback_used": False,
                    "test_feedback_used": False,
                    "reported_results_used_as_runtime_feedback": False,
                    "not_sota_claim": True,
                    "not_final_performance_claim": True,
                }
            )
        summary_rows.append(
            {
                "candidate_id": policy.policy_id,
                "origin": policy.origin,
                "family": policy.family,
                "win_count_vs_best_reward": wins,
                "tie_count_vs_best_reward": ties,
                "loss_count_vs_best_reward": losses,
                "mean_delta_vs_best_reward": round(float(np.mean(final_deltas)), 12),
                "branch_counts": branch_counts,
                "non_trust_best_reward_branch_exercised": any(
                    branch != "trust_best_reward" and count > 0
                    for branch, count in branch_counts.items()
                ),
            }
        )
    if not summary_rows:
        return _build_empty_evaluator_report() | {"evaluation_trace_rows": []}
    selected = sorted(
        summary_rows,
        key=lambda row: (
            int(row["loss_count_vs_best_reward"]),
            -int(row["win_count_vs_best_reward"]),
            float(row["mean_delta_vs_best_reward"]),
            str(row["candidate_id"]),
        ),
    )[0]
    return {
        "schema_version": EVALUATOR_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "evaluated_candidate_count": len(summary_rows),
        "case_count": len(cases),
        "candidate_rows": summary_rows,
        "selected_candidate_id": selected["candidate_id"],
        "selected_candidate_origin": selected["origin"],
        "selected_candidate_family": selected["family"],
        "selected_candidate_not_equivalent_to_best_reward": bool(
            selected["non_trust_best_reward_branch_exercised"]
        ),
        "non_trust_best_reward_branch_exercised": bool(
            selected["non_trust_best_reward_branch_exercised"]
        ),
        "train_objective_win_count_vs_best_reward": int(
            selected["win_count_vs_best_reward"]
        ),
        "train_objective_loss_count_vs_best_reward": int(
            selected["loss_count_vs_best_reward"]
        ),
        "selected_candidate_delta_vs_best_reward": selected[
            "mean_delta_vs_best_reward"
        ],
        "failure_summary": [
            row["candidate_id"]
            for row in summary_rows
            if int(row["loss_count_vs_best_reward"]) > 0
        ][:5],
        "objective_evaluator_feedback_used": True,
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "evaluation_trace_rows": trace_rows,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_empty_evaluator_report() -> dict[str, Any]:
    return {
        "schema_version": EVALUATOR_SCHEMA_VERSION,
        "stage": STAGE,
        "status": BLOCKED_STATUS,
        "evaluated_candidate_count": 0,
        "case_count": 0,
        "candidate_rows": [],
        "selected_candidate_id": None,
        "selected_candidate_origin": None,
        "selected_candidate_not_equivalent_to_best_reward": False,
        "non_trust_best_reward_branch_exercised": False,
        "train_objective_win_count_vs_best_reward": 0,
        "train_objective_loss_count_vs_best_reward": 0,
        "objective_evaluator_feedback_used": False,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _train_cases() -> list[_TrainCase]:
    return [
        _TrainCase(
            "trusted_best_reward",
            "trusted_best_reward",
            10.0,
            6.0,
            (6.0, 8.0, 9.0),
            (0.95, 0.54, 0.5),
        ),
        _TrainCase(
            "low_margin_weighted",
            "low_margin_weighted",
            10.0,
            7.828330638956526,
            (7.0, 8.0, 8.5),
            (0.71, 0.7, 0.69),
        ),
        _TrainCase(
            "direction_conflict_simple",
            "direction_conflict_simple",
            10.0,
            10.666666666666666,
            (6.5, 12.5, 13.0),
            (0.82, 0.68, 0.66),
        ),
        _TrainCase(
            "oversized_best_reward_shrinkage",
            "oversized_best_reward_shrinkage",
            10.0,
            -23.514622004318745,
            (-160.0, 8.5, 9.0),
            (0.94, 0.7, 0.69),
        ),
    ]


def _run_baseline_case(case: _TrainCase) -> tuple[float, float]:
    state = _state(case)
    value = BestRewardSelection().coordinate(state).coordinated_value
    return float(value), _objective(value, case.target_value)


def _run_policy_case(policy: _PolicyProgram, case: _TrainCase) -> tuple[float, str]:
    state = _state(case)
    features = _case_features(case)
    action = "simple_consensus"
    for rule in policy.rules:
        condition = str(rule["condition"])
        if _condition_matches(condition, features):
            action = str(rule["action"])
            break
    if action == "trust_best_reward":
        value = BestRewardSelection().coordinate(state).coordinated_value
    elif action == "weighted_consensus":
        value = WeightedConsensus(temperature=1.0).coordinate(state).coordinated_value
    elif action == "simple_consensus":
        value = AverageConsensus().coordinate(state).coordinated_value
    elif action == "damp_best_reward":
        best = BestRewardSelection().coordinate(state).coordinated_value
        value = state.current_value + 0.5 * (best - state.current_value)
    elif action == "shrinkage_repair":
        weighted = WeightedConsensus(temperature=1.0).coordinate(state).coordinated_value
        value = state.current_value + 0.5 * (weighted - state.current_value)
    elif action == "reject_unstable_best_reward":
        value = AverageConsensus().coordinate(state).coordinated_value
    else:
        raise ValueError(f"unsupported policy action: {action}")
    return state.clip(float(value)), action


def _case_features(case: _TrainCase) -> dict[str, Any]:
    return {
        "best_reward_trustworthy": case.regime == "trusted_best_reward",
        "low_reward_margin": case.regime == "low_margin_weighted",
        "direction_inconsistent": case.regime == "direction_conflict_simple",
        "oversized_best_reward": case.regime == "oversized_best_reward_shrinkage",
        "best_reward_outlier": case.regime == "oversized_best_reward_shrinkage",
        "high_proposal_dispersion": case.regime
        in {"direction_conflict_simple", "oversized_best_reward_shrinkage"},
        "high_reward_concentration": case.regime == "trusted_best_reward",
        "reward_margin": {
            "trusted_best_reward": 0.8,
            "low_margin_weighted": 0.05,
            "direction_conflict_simple": 0.2,
            "oversized_best_reward_shrinkage": 0.3,
        }[case.regime],
        "reward_concentration": 0.7 if case.regime == "trusted_best_reward" else 0.35,
        "conflict_intensity": (
            0.75
            if case.regime
            in {"direction_conflict_simple", "oversized_best_reward_shrinkage"}
            else 0.2
        ),
        "proposal_dispersion": (
            0.8
            if case.regime
            in {"direction_conflict_simple", "oversized_best_reward_shrinkage"}
            else 0.25
        ),
        "direction_consistency": (
            0.9
            if case.regime in {"trusted_best_reward", "low_margin_weighted"}
            else 0.15
        ),
        "shared_variable_oscillation": (
            0.8
            if case.regime
            in {"direction_conflict_simple", "oversized_best_reward_shrinkage"}
            else 0.1
        ),
        "recent_best_reward_regret": (
            0.8
            if case.regime
            in {"direction_conflict_simple", "oversized_best_reward_shrinkage"}
            else 0.05
        ),
        "always": True,
    }


def _condition_matches(condition: str, features: Mapping[str, Any]) -> bool:
    normalized = " ".join(condition.strip().split())
    if not normalized:
        return False
    if normalized.lower() == "always":
        return True
    or_parts = _split_condition(normalized, "OR")
    return any(_and_condition_matches(part, features) for part in or_parts)


def _and_condition_matches(condition: str, features: Mapping[str, Any]) -> bool:
    and_parts = _split_condition(condition, "AND")
    return all(_atomic_condition_matches(part, features) for part in and_parts)


def _split_condition(condition: str, operator: str) -> list[str]:
    marker = f" {operator.lower()} "
    lower = condition.lower()
    parts: list[str] = []
    start = 0
    while True:
        index = lower.find(marker, start)
        if index < 0:
            parts.append(condition[start:].strip())
            return parts
        parts.append(condition[start:index].strip())
        start = index + len(marker)


def _atomic_condition_matches(condition: str, features: Mapping[str, Any]) -> bool:
    text = condition.strip()
    lowered = text.lower()
    if lowered == "always":
        return True
    if lowered.startswith("high "):
        value = _feature_value(text[5:].strip(), features)
        return value >= 0.5
    if lowered.startswith("low "):
        value = _feature_value(text[4:].strip(), features)
        return value < 0.5
    for operator in ["<=", ">=", "<", ">"]:
        if operator in text:
            left, right = text.split(operator, 1)
            value = _feature_value(left.strip(), features)
            threshold = float(right.strip())
            if operator == "<=":
                return value <= threshold
            if operator == ">=":
                return value >= threshold
            if operator == "<":
                return value < threshold
            return value > threshold
    value = features.get(text)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) >= 0.5
    return False


def _feature_value(name: str, features: Mapping[str, Any]) -> float:
    value = features.get(name)
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _state(case: _TrainCase) -> SharedVariableConflictState:
    return SharedVariableConflictState.from_group_proposals(
        variable_id=case.variable_id,
        current_value=case.initial_value,
        bounds=case.bounds,
        proposals=[
            GroupProposal(index + 1, case.variable_id, value, reward)
            for index, (value, reward) in enumerate(zip(case.proposals, case.rewards))
        ],
        diagnostics={"stage": STAGE, "case_id": case.case_id, "split": "train"},
    )


def _objective(value: float, target: float) -> float:
    return float((float(value) - float(target)) ** 2)


def _compare(candidate: float, reference: float) -> str:
    delta = candidate - reference
    if delta < -1e-12:
        return "win"
    if delta > 1e-12:
        return "loss"
    return "tie"


def _gate_passes(
    *,
    evaluator: Mapping[str, Any],
    gate: Mapping[str, Any],
    static_audit: Mapping[str, Any],
) -> bool:
    return (
        int(static_audit["quality_pass_candidate_count"]) >= 8
        and int(static_audit["coordination_family_count"]) >= 4
        and evaluator.get("selected_candidate_origin") == "llm_reflective_generated"
        and evaluator.get("selected_candidate_not_equivalent_to_best_reward") is True
        and evaluator.get("non_trust_best_reward_branch_exercised") is True
        and int(evaluator.get("train_objective_win_count_vs_best_reward", 0))
        >= int(gate["win_count_vs_best_reward_select_min"])
        and int(evaluator.get("train_objective_loss_count_vs_best_reward", 0))
        <= int(gate["loss_count_vs_best_reward_select_max"])
    )


def _build_fe_ledger(
    *,
    status: str,
    trace_rows: Sequence[Mapping[str, Any]],
    llm_call_used: bool,
    real_llm_api_called: bool,
    inherited_stage8_19_fe_total: int,
) -> dict[str, Any]:
    totals = {
        key: sum(int(row.get(key, 0)) for row in trace_rows)
        for key in [
            "FE_grouping",
            "FE_proposal",
            "FE_coordination_extra",
            "FE_repair",
            "FE_global_objective",
            "FE_total",
        ]
    }
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": status,
        "budget_scope": "llm_reflective_policy_search_execution",
        "inherited_stage8_19_FE_total": int(inherited_stage8_19_fe_total),
        **totals,
        "all_extra_fe_counted": True,
        "objective_loop_executed": bool(trace_rows),
        "new_objective_evaluation_used": bool(trace_rows),
        "llm_call_used": bool(llm_call_used),
        "real_llm_api_called": bool(real_llm_api_called),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary(
    *,
    status: str,
    objective_loop_executed: bool,
    new_objective_evaluation_used: bool,
    llm_call_used: bool,
    real_llm_api_called: bool,
    unit_test_injected_provider_used: bool,
) -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": status,
        "claim_scope": "LLM-reflective policy search execution gate",
        "objective_loop_executed": bool(objective_loop_executed),
        "new_objective_evaluation_used": bool(new_objective_evaluation_used),
        "llm_call_used": bool(llm_call_used),
        "real_llm_api_called": bool(real_llm_api_called),
        "unit_test_injected_provider_used": bool(unit_test_injected_provider_used),
        "forbidden_behaviors": {
            "fake_llm_candidate_generation": False,
            "selected_operator_revision": False,
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


def _build_pass_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "decision": "ROUTE_TO_LLM_CONTRIBUTION_ABLATION",
        "next_stage": NEXT_PASS_STAGE,
        "allowed_next_work": NEXT_PASS_WORK,
        "next_route": NEXT_PASS_WORK,
        "run_full_25_run_panel_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_failed_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "FAIL",
        "decision": "RETURN_TO_LLM_REFLECTION_REPAIR",
        "next_stage": "Stage 8.20",
        "allowed_next_work": "repair_llm_reflective_policy_search_prompt_or_evaluator",
        "next_route": "REPAIR_STAGE8_20",
        "run_full_25_run_panel_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_blocked_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": BLOCKED_STATUS,
        "decision": "WAIT_FOR_REAL_LLM_API",
        "next_stage": "Stage 8.20",
        "allowed_next_work": "provide_real_llm_api_and_rerun_stage8_20",
        "next_route": "WAIT_FOR_REAL_LLM_API",
        "run_full_25_run_panel_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_pass_report(
    *, execution: Mapping[str, Any], inherited_stage8_19_fe_total: int
) -> dict[str, Any]:
    static_audit = execution["static_audit"]
    evaluator = execution["evaluator"]
    ledger = execution["ledger"]
    route = execution["route"]
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": execution["status"],
        "source_stage": "8.19",
        "execution_scope": "llm_reflective_coordination_policy_search_execution",
        "reflection_round_count": len(execution["round_rows"]),
        "raw_llm_candidate_count": len(execution["raw_rows"]),
        "quality_pass_candidate_count": int(
            static_audit["quality_pass_candidate_count"]
        ),
        "coordination_family_count": int(static_audit["coordination_family_count"]),
        "selected_candidate_id": evaluator.get("selected_candidate_id"),
        "selected_candidate_origin": evaluator.get("selected_candidate_origin"),
        "selected_candidate_not_equivalent_to_best_reward": evaluator.get(
            "selected_candidate_not_equivalent_to_best_reward"
        ),
        "non_trust_best_reward_branch_exercised": evaluator.get(
            "non_trust_best_reward_branch_exercised"
        ),
        "train_objective_win_count_vs_best_reward": evaluator.get(
            "train_objective_win_count_vs_best_reward"
        ),
        "train_objective_loss_count_vs_best_reward": evaluator.get(
            "train_objective_loss_count_vs_best_reward"
        ),
        "objective_evaluator_feedback_used": evaluator.get(
            "objective_evaluator_feedback_used"
        ),
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "llm_call_used": bool(execution["llm_call_used"]),
        "real_llm_api_called": bool(execution["real_llm_api_called"]),
        "new_llm_candidate_generation_used": bool(execution["real_llm_api_called"]),
        "unit_test_injected_provider_used": bool(
            execution["unit_test_injected_provider_used"]
        ),
        "fake_llm_candidates_used": False,
        "FE_total": int(ledger["FE_total"]),
        "inherited_stage8_19_FE_total": int(inherited_stage8_19_fe_total),
        "next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
        "selected_operator_revision_used": False,
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


def _require_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"policy field must be a non-empty string: {key}")
    return value


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

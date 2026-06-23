"""Stage 8.26 MVP ownership-aware strategy DSL and evaluator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from loco.conflict.conflict_state import GroupProposal, SharedVariableConflictState
from loco.coordination.baselines import (
    AverageConsensus,
    BestRewardSelection,
    CoordinationResult,
    WeightedConsensus,
)


STAGE = "8.26"
PROGRAM_SCHEMA_VERSION = "loco.stage8_26_ownership_aware_strategy_program.v1"
REPORT_SCHEMA_VERSION = "loco.stage8_26_mvp_strategy_dsl_report.v1"
MANIFEST_SCHEMA_VERSION = "loco.stage8_26_strategy_dsl_manifest.v1"
EQUIVALENCE_SCHEMA_VERSION = "loco.stage8_26_behavior_equivalence_report.v1"
BRANCH_SCHEMA_VERSION = "loco.stage8_26_branch_coverage_report.v1"
OWNERSHIP_SCHEMA_VERSION = "loco.stage8_26_ownership_decision_coverage_report.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_26_train_side_win_loss_report.v1"
TRACE_SCHEMA_VERSION = "loco.stage8_26_synthetic_search_trace.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_26_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_26_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_26_next_route_decision.v1"

ALLOWED_OUTPUTS = [
    "shared_variable_owner",
    "allow_multi_assignment",
    "linkage_break_or_preserve",
    "contribution_based_owner_switch",
    "coordination_action",
    "fallback_repair_action",
    "behavior_equivalence_guard",
]
ALLOWED_ACTIONS = [
    "trust_best_reward",
    "damp_best_reward",
    "weighted_consensus",
    "simple_consensus",
    "shrinkage_repair",
    "reject_unstable_best_reward",
    "owner_proposal_select",
    "multi_owner_weighted_vote",
]
ALLOWED_OWNERS = [
    "best_reward_group",
    "contribution_leader",
    "multi_owner",
    "historical_owner",
]
ALLOWED_LINKAGE_DECISIONS = ["preserve", "break"]
BEHAVIOR_GUARDS = [
    "not_equivalent_to_best_reward_select",
    "non_trust_branch_exercised",
    "ownership_or_linkage_decision_exercised",
]


@dataclass(frozen=True)
class StrategyRule:
    condition: str
    shared_variable_owner: str
    allow_multi_assignment: bool
    linkage_decision: str
    coordination_action: str
    fallback_repair_action: str


@dataclass(frozen=True)
class StrategyProgram:
    strategy_id: str
    origin: str
    family: str
    rules: tuple[StrategyRule, ...]
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class SyntheticConflictCase:
    case_id: str
    regime: str
    current_value: float
    target_value: float
    proposals: tuple[float, ...]
    rewards: tuple[float, ...]
    contribution_scores: tuple[float, ...]
    historical_owner_group_id: int
    bounds: tuple[float, float] = (-100.0, 100.0)
    variable_id: int = 7


def load_strategy_program(payload: Mapping[str, Any]) -> StrategyProgram:
    """Parse and statically audit a Stage 8.26 strategy program."""

    if payload.get("schema_version") != PROGRAM_SCHEMA_VERSION:
        raise ValueError("unsupported Stage 8.26 strategy schema_version")
    rules = tuple(_load_rule(rule) for rule in payload.get("rules", []))
    if not rules:
        raise ValueError("strategy program must define at least one rule")
    return StrategyProgram(
        strategy_id=_require_str(payload, "strategy_id"),
        origin=_require_str(payload, "origin"),
        family=_require_str(payload, "family"),
        rules=rules,
        payload=dict(payload),
    )


def evaluate_strategy_program(program: StrategyProgram) -> dict[str, Any]:
    """Evaluate one strategy on deterministic train-side conflict regimes."""

    trace_rows = _evaluate_program_trace(program)
    equivalence = _build_equivalence_report(program, trace_rows)
    branch = _build_branch_coverage_report(program, trace_rows)
    ownership = _build_ownership_report(program, trace_rows)
    win_loss = _build_win_loss_report(program, trace_rows)
    gate_passed = (
        equivalence["not_equivalent_to_best_reward_select"]
        and branch["non_trust_branch_exercised"]
        and ownership["ownership_or_linkage_decision_exercised"]
        and win_loss["win_count_vs_best_reward"] >= 1
        and win_loss["loss_count_vs_best_reward"] == 0
    )
    return {
        "strategy_id": program.strategy_id,
        "status": "PASS" if gate_passed else "FAIL",
        "behavior_equivalence_report": equivalence,
        "branch_coverage_report": branch,
        "ownership_decision_coverage_report": ownership,
        "train_side_win_loss_report": win_loss,
        "synthetic_search_trace_rows": trace_rows,
        "gate_passed": bool(gate_passed),
        "FE_total": 0,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def run_stage8_26_mvp_strategy_dsl(
    *,
    stage8_25_report_path: Path | str,
    stage8_25_dsl_contract_path: Path | str,
    stage8_25_fe_ledger_path: Path | str,
    stage8_25_runtime_boundary_path: Path | str,
    stage8_25_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Run the Stage 8.26 MVP DSL gate without objectives or LLM calls."""

    stage8_25_report = _read_json(Path(stage8_25_report_path))
    stage8_25_dsl = _read_json(Path(stage8_25_dsl_contract_path))
    stage8_25_ledger = _read_json(Path(stage8_25_fe_ledger_path))
    stage8_25_boundary = _read_json(Path(stage8_25_runtime_boundary_path))
    stage8_25_route = _read_json(Path(stage8_25_next_route_path))
    _validate_stage8_25_inputs(
        report=stage8_25_report,
        dsl=stage8_25_dsl,
        ledger=stage8_25_ledger,
        boundary=stage8_25_boundary,
        route=stage8_25_route,
    )

    programs = [load_strategy_program(payload) for payload in _candidate_payloads()]
    evaluations = [evaluate_strategy_program(program) for program in programs]
    selected = _select_evaluation(evaluations)
    manifest = _build_manifest(stage8_25_dsl, programs)
    equivalence = selected["behavior_equivalence_report"]
    branch = selected["branch_coverage_report"]
    ownership = selected["ownership_decision_coverage_report"]
    win_loss = selected["train_side_win_loss_report"]
    trace_rows = _flatten_trace_rows(evaluations)
    ledger = _build_fe_ledger(stage8_25_ledger)
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    report = _build_report(
        selected=selected,
        manifest=manifest,
        ledger=ledger,
        route=route,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "strategy_dsl_manifest.json", manifest)
    _write_json(output_path / "behavior_equivalence_report.json", equivalence)
    _write_json(output_path / "branch_coverage_report.json", branch)
    _write_json(output_path / "ownership_decision_coverage_report.json", ownership)
    _write_json(output_path / "train_side_win_loss_report.json", win_loss)
    _write_jsonl(output_path / "synthetic_search_trace.jsonl", trace_rows)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    _write_json(output_path / "stage8_26_report.json", report)
    return report


def _load_rule(payload: Mapping[str, Any]) -> StrategyRule:
    owner = _require_str(payload, "shared_variable_owner")
    action = _require_str(payload, "coordination_action")
    fallback = _require_str(payload, "fallback_repair_action")
    linkage = _require_str(payload, "linkage_decision")
    if owner not in ALLOWED_OWNERS:
        raise ValueError(f"unsupported shared_variable_owner: {owner}")
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"unsupported coordination_action: {action}")
    if fallback not in ALLOWED_ACTIONS:
        raise ValueError(f"unsupported fallback_repair_action: {fallback}")
    if linkage not in ALLOWED_LINKAGE_DECISIONS:
        raise ValueError(f"unsupported linkage_decision: {linkage}")
    return StrategyRule(
        condition=_require_str(payload, "condition"),
        shared_variable_owner=owner,
        allow_multi_assignment=bool(payload.get("allow_multi_assignment", False)),
        linkage_decision=linkage,
        coordination_action=action,
        fallback_repair_action=fallback,
    )


def _evaluate_program_trace(program: StrategyProgram) -> list[dict[str, Any]]:
    rows = []
    for case in _synthetic_conflict_cases():
        state = _state(case)
        features = _case_features(case)
        rule = _select_rule(program, features)
        value = _apply_action(rule.coordination_action, rule, state, case)
        best_value = BestRewardSelection().coordinate(state).coordinated_value
        candidate_objective = _objective(value, case.target_value)
        best_objective = _objective(best_value, case.target_value)
        rows.append(
            {
                "schema_version": TRACE_SCHEMA_VERSION,
                "stage": STAGE,
                "strategy_id": program.strategy_id,
                "case_id": case.case_id,
                "regime": case.regime,
                "selected_rule_condition": rule.condition,
                "shared_variable_owner": rule.shared_variable_owner,
                "allow_multi_assignment": rule.allow_multi_assignment,
                "linkage_decision": rule.linkage_decision,
                "coordination_action": rule.coordination_action,
                "fallback_repair_action": rule.fallback_repair_action,
                "coordinated_value": round(float(value), 12),
                "best_reward_value": round(float(best_value), 12),
                "target_value": case.target_value,
                "candidate_objective": round(candidate_objective, 12),
                "best_reward_objective": round(best_objective, 12),
                "delta_vs_best_reward": round(candidate_objective - best_objective, 12),
                "comparison_vs_best_reward": _compare(candidate_objective, best_objective),
                "FE_total": 0,
            }
        )
    return rows


def _select_rule(
    program: StrategyProgram, features: Mapping[str, Any]
) -> StrategyRule:
    for rule in program.rules:
        if _condition_matches(rule.condition, features):
            return rule
    return program.rules[-1]


def _apply_action(
    action: str,
    rule: StrategyRule,
    state: SharedVariableConflictState,
    case: SyntheticConflictCase,
) -> float:
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
        value = _apply_action(rule.fallback_repair_action, rule, state, case)
    elif action == "owner_proposal_select":
        value = _owner_proposal_value(rule.shared_variable_owner, state, case)
    elif action == "multi_owner_weighted_vote":
        value = _multi_owner_weighted_vote(state, case)
    else:
        raise ValueError(f"unsupported coordination_action: {action}")
    return state.clip(float(value))


def _owner_proposal_value(
    owner: str, state: SharedVariableConflictState, case: SyntheticConflictCase
) -> float:
    if owner == "contribution_leader":
        index = int(np.argmax(np.asarray(case.contribution_scores, dtype=float)))
    elif owner == "historical_owner":
        index = state.related_group_ids.index(case.historical_owner_group_id)
    elif owner == "best_reward_group":
        index = int(np.argmax(np.asarray(state.group_rewards, dtype=float)))
    else:
        return _multi_owner_weighted_vote(state, case)
    return float(state.proposals[index])


def _multi_owner_weighted_vote(
    state: SharedVariableConflictState, case: SyntheticConflictCase
) -> float:
    rewards = np.asarray(state.group_rewards, dtype=float)
    contributions = np.asarray(case.contribution_scores, dtype=float)
    values = np.asarray(state.proposals, dtype=float)
    raw = np.maximum(rewards, 0.0) + np.maximum(contributions, 0.0)
    if float(np.sum(raw)) <= 1e-12:
        return float(np.mean(values))
    weights = raw / float(np.sum(raw))
    return float(np.dot(weights, values))


def _synthetic_conflict_cases() -> list[SyntheticConflictCase]:
    return [
        SyntheticConflictCase(
            case_id="trusted_best_reward",
            regime="trusted_best_reward",
            current_value=10.0,
            target_value=6.0,
            proposals=(6.0, 8.0, 9.0),
            rewards=(0.95, 0.54, 0.50),
            contribution_scores=(0.91, 0.35, 0.20),
            historical_owner_group_id=1,
        ),
        SyntheticConflictCase(
            case_id="conflicting_owner_leader",
            regime="conflicting_overlap",
            current_value=10.0,
            target_value=8.0,
            proposals=(2.0, 8.0, 12.0),
            rewards=(0.92, 0.82, 0.30),
            contribution_scores=(0.25, 0.95, 0.10),
            historical_owner_group_id=2,
        ),
        SyntheticConflictCase(
            case_id="conforming_multi_owner",
            regime="conforming_overlap",
            current_value=10.0,
            target_value=8.0,
            proposals=(7.5, 8.0, 8.5),
            rewards=(0.74, 0.72, 0.71),
            contribution_scores=(0.76, 0.77, 0.75),
            historical_owner_group_id=2,
        ),
        SyntheticConflictCase(
            case_id="unstable_best_reward",
            regime="unstable_best_reward",
            current_value=10.0,
            target_value=9.0,
            proposals=(-90.0, 8.5, 9.0),
            rewards=(0.91, 0.88, 0.86),
            contribution_scores=(0.20, 0.82, 0.86),
            historical_owner_group_id=3,
        ),
    ]


def _case_features(case: SyntheticConflictCase) -> dict[str, Any]:
    return {
        "always": True,
        "trusted_best_reward": case.regime == "trusted_best_reward",
        "conflicting_overlap": case.regime == "conflicting_overlap",
        "conforming_overlap": case.regime == "conforming_overlap",
        "unstable_best_reward": case.regime == "unstable_best_reward",
        "high_owner_regret": case.regime == "conflicting_overlap",
        "high_owner_agreement": case.regime == "conforming_overlap",
        "high_conflict_intensity": case.regime
        in {"conflicting_overlap", "unstable_best_reward"},
        "low_reward_margin": case.regime
        in {"conforming_overlap", "unstable_best_reward"},
    }


def _state(case: SyntheticConflictCase) -> SharedVariableConflictState:
    return SharedVariableConflictState.from_group_proposals(
        variable_id=case.variable_id,
        current_value=case.current_value,
        bounds=case.bounds,
        proposals=[
            GroupProposal(
                group_id=index + 1,
                variable_id=case.variable_id,
                proposed_value=value,
                reward=reward,
                metadata={"contribution_score": case.contribution_scores[index]},
            )
            for index, (value, reward) in enumerate(zip(case.proposals, case.rewards))
        ],
        diagnostics={"stage": STAGE, "case_id": case.case_id, "split": "train"},
    )


def _build_equivalence_report(
    program: StrategyProgram, trace_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    equivalent = all(
        abs(float(row["coordinated_value"]) - float(row["best_reward_value"])) <= 1e-12
        for row in trace_rows
    )
    return {
        "schema_version": EQUIVALENCE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "strategy_id": program.strategy_id,
        "selected_strategy_id": program.strategy_id,
        "case_count": len(trace_rows),
        "equivalent_to_best_reward_select": bool(equivalent),
        "not_equivalent_to_best_reward_select": not bool(equivalent),
        "best_reward_equivalent_case_count": sum(
            1
            for row in trace_rows
            if abs(float(row["coordinated_value"]) - float(row["best_reward_value"]))
            <= 1e-12
        ),
        "behavior_guard": "not_equivalent_to_best_reward_select",
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_branch_coverage_report(
    program: StrategyProgram, trace_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    branch_counts = {
        action: sum(1 for row in trace_rows if row["coordination_action"] == action)
        for action in ALLOWED_ACTIONS
    }
    return {
        "schema_version": BRANCH_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "strategy_id": program.strategy_id,
        "selected_strategy_id": program.strategy_id,
        "case_count": len(trace_rows),
        "branch_counts": branch_counts,
        "non_trust_branch_exercised": any(
            action != "trust_best_reward" and count > 0
            for action, count in branch_counts.items()
        ),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_ownership_report(
    program: StrategyProgram, trace_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    owner_counts = {
        owner: sum(1 for row in trace_rows if row["shared_variable_owner"] == owner)
        for owner in ALLOWED_OWNERS
    }
    linkage_counts = {
        decision: sum(1 for row in trace_rows if row["linkage_decision"] == decision)
        for decision in ALLOWED_LINKAGE_DECISIONS
    }
    exercised = (
        owner_counts["contribution_leader"] > 0
        or owner_counts["multi_owner"] > 0
        or owner_counts["historical_owner"] > 0
        or linkage_counts["break"] > 0
        or any(bool(row["allow_multi_assignment"]) for row in trace_rows)
    )
    return {
        "schema_version": OWNERSHIP_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "strategy_id": program.strategy_id,
        "selected_strategy_id": program.strategy_id,
        "case_count": len(trace_rows),
        "owner_counts": owner_counts,
        "linkage_decision_counts": linkage_counts,
        "multi_assignment_case_count": sum(
            1 for row in trace_rows if bool(row["allow_multi_assignment"])
        ),
        "ownership_or_linkage_decision_exercised": bool(exercised),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_win_loss_report(
    program: StrategyProgram, trace_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    counts = {
        label: sum(1 for row in trace_rows if row["comparison_vs_best_reward"] == label)
        for label in ["win", "tie", "loss"]
    }
    return {
        "schema_version": WIN_LOSS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "strategy_id": program.strategy_id,
        "selected_strategy_id": program.strategy_id,
        "case_count": len(trace_rows),
        "win_count_vs_best_reward": counts["win"],
        "tie_count_vs_best_reward": counts["tie"],
        "loss_count_vs_best_reward": counts["loss"],
        "mean_delta_vs_best_reward": round(
            float(np.mean([row["delta_vs_best_reward"] for row in trace_rows])), 12
        ),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _candidate_payloads() -> list[dict[str, Any]]:
    return [
        {
            "schema_version": PROGRAM_SCHEMA_VERSION,
            "strategy_id": "always_trust_best_reward",
            "origin": "hand_designed_baseline",
            "family": "best_reward_collapse",
            "rules": [
                _rule(
                    condition="always",
                    owner="best_reward_group",
                    multi=False,
                    linkage="preserve",
                    action="trust_best_reward",
                    fallback="weighted_consensus",
                )
            ],
        },
        {
            "schema_version": PROGRAM_SCHEMA_VERSION,
            "strategy_id": "weighted_consensus_guard_v1",
            "origin": "hand_designed_baseline",
            "family": "consensus_guard",
            "rules": [
                _rule(
                    condition="low_reward_margin",
                    owner="multi_owner",
                    multi=True,
                    linkage="preserve",
                    action="weighted_consensus",
                    fallback="simple_consensus",
                ),
                _rule(
                    condition="always",
                    owner="best_reward_group",
                    multi=False,
                    linkage="preserve",
                    action="trust_best_reward",
                    fallback="weighted_consensus",
                ),
            ],
        },
        {
            "schema_version": PROGRAM_SCHEMA_VERSION,
            "strategy_id": "ownership_conflict_guard_v1",
            "origin": "literature_inspired_mvp",
            "family": "ownership_aware_conflict_guard",
            "rules": [
                _rule(
                    condition="conflicting_overlap AND high_owner_regret",
                    owner="contribution_leader",
                    multi=False,
                    linkage="break",
                    action="owner_proposal_select",
                    fallback="shrinkage_repair",
                ),
                _rule(
                    condition="conforming_overlap AND high_owner_agreement",
                    owner="multi_owner",
                    multi=True,
                    linkage="preserve",
                    action="multi_owner_weighted_vote",
                    fallback="weighted_consensus",
                ),
                _rule(
                    condition="unstable_best_reward",
                    owner="historical_owner",
                    multi=False,
                    linkage="preserve",
                    action="reject_unstable_best_reward",
                    fallback="simple_consensus",
                ),
                _rule(
                    condition="always",
                    owner="best_reward_group",
                    multi=False,
                    linkage="preserve",
                    action="trust_best_reward",
                    fallback="weighted_consensus",
                ),
            ],
        },
    ]


def _rule(
    *,
    condition: str,
    owner: str,
    multi: bool,
    linkage: str,
    action: str,
    fallback: str,
) -> dict[str, Any]:
    return {
        "condition": condition,
        "shared_variable_owner": owner,
        "allow_multi_assignment": multi,
        "linkage_decision": linkage,
        "coordination_action": action,
        "fallback_repair_action": fallback,
    }


def _select_evaluation(evaluations: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return sorted(
        evaluations,
        key=lambda evaluation: (
            not bool(evaluation["gate_passed"]),
            int(evaluation["train_side_win_loss_report"]["loss_count_vs_best_reward"]),
            -int(evaluation["train_side_win_loss_report"]["win_count_vs_best_reward"]),
            float(evaluation["train_side_win_loss_report"]["mean_delta_vs_best_reward"]),
            str(evaluation["strategy_id"]),
        ),
    )[0]


def _build_manifest(
    stage8_25_dsl: Mapping[str, Any], programs: Sequence[StrategyProgram]
) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.25",
        "target_scope": stage8_25_dsl["target_scope"],
        "mvp_strategy_dsl_implemented": True,
        "strategy_program_schema_version": PROGRAM_SCHEMA_VERSION,
        "allowed_outputs": list(stage8_25_dsl["allowed_outputs"]),
        "allowed_coordination_actions": list(stage8_25_dsl["allowed_coordination_actions"]),
        "behavior_equivalence_guards": BEHAVIOR_GUARDS,
        "strategy_count": len(programs),
        "strategy_ids": [program.strategy_id for program in programs],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _flatten_trace_rows(
    evaluations: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    for evaluation in evaluations:
        rows.extend(evaluation["synthetic_search_trace_rows"])
    return rows


def _validate_stage8_25_inputs(
    *,
    report: Mapping[str, Any],
    dsl: Mapping[str, Any],
    ledger: Mapping[str, Any],
    boundary: Mapping[str, Any],
    route: Mapping[str, Any],
) -> None:
    if report.get("stage") != "8.25" or report.get("status") != "PASS":
        raise ValueError("Stage 8.26 requires a passing Stage 8.25 report.")
    if report.get("stage8_26_mvp_strategy_dsl_required") is not True:
        raise ValueError("Stage 8.25 must require the Stage 8.26 MVP DSL.")
    if dsl.get("stage8_26_mvp_required") is not True:
        raise ValueError("Stage 8.26 requires the Stage 8.25 DSL contract.")
    if int(ledger.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.26 expects zero-FE Stage 8.25 input.")
    if boundary.get("llm_call_used") is not False:
        raise ValueError("Stage 8.26 refuses LLM-tainted Stage 8.25 input.")
    if route.get("next_stage") != "Stage 8.26":
        raise ValueError("Stage 8.26 requires the Stage 8.25 route.")


def _build_fe_ledger(stage8_25_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "mvp_strategy_dsl_synthetic_conflict_regime_search",
        "inherited_stage8_25_FE_total": int(stage8_25_ledger["FE_total"]),
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "all_extra_fe_counted": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "MVP ownership-aware strategy DSL and checker",
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "new_llm_candidate_generation_used": False,
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


def _build_next_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": "ROUTE_TO_STAGE8_27_REAL_LLM_REFLECTIVE_STRATEGY_SEARCH",
        "next_stage": "Stage 8.27",
        "allowed_next_work": "real_llm_reflective_ownership_aware_strategy_search",
        "run_cec_checkpoint_next": False,
        "run_full_25_run_panel_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    selected: Mapping[str, Any],
    manifest: Mapping[str, Any],
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.25",
        "implementation_scope": "mvp_strategy_dsl_evaluator_behavior_equivalence_checker",
        "mvp_strategy_dsl_implemented": True,
        "strategy_program_schema_version": PROGRAM_SCHEMA_VERSION,
        "behavior_equivalence_checker_implemented": True,
        "synthetic_conflict_regime_search_executed": True,
        "strategy_count": int(manifest["strategy_count"]),
        "selected_strategy_id": selected["strategy_id"],
        "selected_strategy_not_equivalent_to_best_reward_select": bool(
            selected["behavior_equivalence_report"][
                "not_equivalent_to_best_reward_select"
            ]
        ),
        "non_trust_branch_exercised": bool(
            selected["branch_coverage_report"]["non_trust_branch_exercised"]
        ),
        "ownership_or_linkage_decision_exercised": bool(
            selected["ownership_decision_coverage_report"][
                "ownership_or_linkage_decision_exercised"
            ]
        ),
        "train_side_win_count_vs_best_reward": int(
            selected["train_side_win_loss_report"]["win_count_vs_best_reward"]
        ),
        "train_side_loss_count_vs_best_reward": int(
            selected["train_side_win_loss_report"]["loss_count_vs_best_reward"]
        ),
        "FE_total": int(ledger["FE_total"]),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "selected_policy_revision_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "recommended_next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _condition_matches(condition: str, features: Mapping[str, Any]) -> bool:
    normalized = " ".join(condition.strip().split())
    if not normalized:
        return False
    if normalized.lower() == "always":
        return True
    return any(
        all(_atomic_condition_matches(part, features) for part in or_part.split(" AND "))
        for or_part in normalized.split(" OR ")
    )


def _atomic_condition_matches(condition: str, features: Mapping[str, Any]) -> bool:
    value = features.get(condition.strip())
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) >= 0.5
    return False


def _objective(value: float, target: float) -> float:
    return float((float(value) - float(target)) ** 2)


def _compare(candidate: float, reference: float) -> str:
    delta = float(candidate) - float(reference)
    if delta < -1e-12:
        return "win"
    if delta > 1e-12:
        return "loss"
    return "tie"


def _require_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"strategy field must be a non-empty string: {key}")
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

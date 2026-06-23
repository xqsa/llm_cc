"""Stage 8.32 overcorrection guard / conditional owner-trust repair design.

This stage is a no-objective, no-LLM, no-CEC design gate. It turns the Stage
8.31 overcorrection diagnosis into a guarded policy payload for later bounded
checking.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "8.32"
REPAIR_POLICY_ID = "stage8_32_guarded_owner_trust_repair_v1"
POLICY_SCHEMA_VERSION = "loco.stage8_32_guarded_owner_trust_policy.v1"
REPORT_SCHEMA_VERSION = "loco.stage8_32_repair_design_report.v1"
GUARD_SCHEMA_VERSION = "loco.stage8_32_overcorrection_guard_spec.v1"
COVERAGE_SCHEMA_VERSION = "loco.stage8_32_static_guard_coverage_report.v1"
CLAIM_SCHEMA_VERSION = "loco.stage8_32_claim_boundary_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_32_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_32_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_32_next_route_decision.v1"

PREVIOUS_FAILURE_MODE = "contribution_leader_break_overcorrection"
NEXT_STAGE = "Stage 8.33"
NEXT_WORK = "static_guard_sanity_or_bounded_checkpoint_gate"


@dataclass(frozen=True)
class GuardedOwnerTrustPolicy:
    """Static decision policy for Stage 8.32 repair design."""

    strategy_id: str = REPAIR_POLICY_ID

    def decide(self, state: Mapping[str, Any]) -> dict[str, Any]:
        if bool(state.get("best_reward_reliable", False)):
            return _decision(
                condition="best_reward_reliable",
                owner="best_reward_group",
                linkage="preserve",
                action="trust_best_reward",
                fallback="weighted_consensus",
            )
        if bool(state.get("strong_owner_conflict", False)) and bool(
            state.get("best_reward_misleading", False)
        ):
            return _decision(
                condition="strong_owner_conflict AND best_reward_misleading",
                owner="contribution_leader",
                linkage="break",
                action="owner_proposal_select",
                fallback="shrinkage_repair",
            )
        if bool(state.get("unstable_or_uncertain", False)):
            owner = "historical_owner" if bool(state.get("historical_owner_known", True)) else "multi_owner"
            return _decision(
                condition="unstable_or_uncertain",
                owner=owner,
                linkage="preserve",
                action="shrinkage_repair",
                fallback="weighted_consensus",
            )
        return _decision(
            condition="always",
            owner="multi_owner",
            linkage="preserve",
            action="weighted_consensus",
            fallback="simple_consensus",
            allow_multi_assignment=True,
        )


def guarded_static_fixtures() -> list[dict[str, Any]]:
    """Return static states that exercise the Stage 8.32 guarded policy paths."""

    return [
        {
            "fixture_id": "best_reward_reliable_preserve",
            "best_reward_reliable": True,
            "strong_owner_conflict": False,
            "best_reward_misleading": False,
            "unstable_or_uncertain": False,
            "historical_owner_known": True,
        },
        {
            "fixture_id": "strong_owner_conflict_best_reward_misleading",
            "best_reward_reliable": False,
            "strong_owner_conflict": True,
            "best_reward_misleading": True,
            "unstable_or_uncertain": False,
            "historical_owner_known": True,
        },
        {
            "fixture_id": "unstable_or_uncertain_historical_shrinkage",
            "best_reward_reliable": False,
            "strong_owner_conflict": False,
            "best_reward_misleading": False,
            "unstable_or_uncertain": True,
            "historical_owner_known": True,
        },
        {
            "fixture_id": "default_preserve_weighted_safety",
            "best_reward_reliable": False,
            "strong_owner_conflict": False,
            "best_reward_misleading": False,
            "unstable_or_uncertain": False,
            "historical_owner_known": False,
        },
    ]


def run_stage8_32_overcorrection_guard_design(
    *,
    stage8_31_failure_diagnosis_path: Path | str,
    stage8_31_overcorrection_path: Path | str,
    stage8_31_branch_usage_path: Path | str,
    stage8_31_fe_ledger_path: Path | str,
    stage8_31_runtime_boundary_path: Path | str,
    stage8_31_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Design a guarded repair policy from Stage 8.31 artifacts."""

    diagnosis = _read_json(Path(stage8_31_failure_diagnosis_path))
    overcorrection = _read_json(Path(stage8_31_overcorrection_path))
    branch_usage = _read_json(Path(stage8_31_branch_usage_path))
    stage8_31_ledger = _read_json(Path(stage8_31_fe_ledger_path))
    stage8_31_boundary = _read_json(Path(stage8_31_runtime_boundary_path))
    stage8_31_route = _read_json(Path(stage8_31_next_route_path))
    _validate_inputs(
        diagnosis=diagnosis,
        overcorrection=overcorrection,
        branch_usage=branch_usage,
        stage8_31_ledger=stage8_31_ledger,
        stage8_31_boundary=stage8_31_boundary,
        stage8_31_route=stage8_31_route,
    )

    policy_payload = _build_guarded_policy_payload()
    guard_spec = _build_guard_spec(diagnosis, overcorrection)
    coverage = _build_static_guard_coverage_report()
    claim = _build_claim_boundary_report()
    ledger = _build_fe_ledger(stage8_31_ledger)
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    report = _build_repair_design_report(
        diagnosis=diagnosis,
        overcorrection=overcorrection,
        coverage=coverage,
        ledger=ledger,
        route=route,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "repair_design_report.json", report)
    _write_json(output_path / "guarded_policy_payload.json", policy_payload)
    _write_json(output_path / "overcorrection_guard_spec.json", guard_spec)
    _write_json(output_path / "static_guard_coverage_report.json", coverage)
    _write_json(output_path / "claim_boundary_report.json", claim)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    *,
    diagnosis: Mapping[str, Any],
    overcorrection: Mapping[str, Any],
    branch_usage: Mapping[str, Any],
    stage8_31_ledger: Mapping[str, Any],
    stage8_31_boundary: Mapping[str, Any],
    stage8_31_route: Mapping[str, Any],
) -> None:
    if diagnosis.get("stage") != "8.31" or diagnosis.get("status") != "PASS":
        raise ValueError("Stage 8.32 requires a passing Stage 8.31 diagnosis.")
    if diagnosis.get("overcorrection_confirmed") is not True:
        raise ValueError("Stage 8.32 requires confirmed Stage 8.31 overcorrection.")
    if diagnosis.get("overcorrection_type") != PREVIOUS_FAILURE_MODE:
        raise ValueError("Stage 8.32 requires contribution-leader break overcorrection.")
    if overcorrection.get("overcorrection_confirmed") is not True:
        raise ValueError("Stage 8.32 requires the overcorrection report.")
    if overcorrection.get("overcorrection_type") != PREVIOUS_FAILURE_MODE:
        raise ValueError("Stage 8.32 refuses a different failure mode.")
    if branch_usage.get("policy_branch_collapse_confirmed") is not True:
        raise ValueError("Stage 8.32 requires branch-collapse evidence.")
    if int(branch_usage.get("trust_best_reward_count", -1)) != 0:
        raise ValueError("Stage 8.32 expects absent trust_best_reward evidence.")
    if int(branch_usage.get("preserve_count", -1)) != 0:
        raise ValueError("Stage 8.32 expects absent preserve evidence.")
    if int(stage8_31_ledger.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.32 requires zero-FE Stage 8.31 input.")
    if stage8_31_boundary.get("objective_loop_executed") is not False:
        raise ValueError("Stage 8.32 refuses objective-loop Stage 8.31 input.")
    if stage8_31_route.get("next_stage") != "Stage 8.32":
        raise ValueError("Stage 8.32 requires the Stage 8.31 route.")
    if stage8_31_route.get("run_full_25_run_panel_next") is not False:
        raise ValueError("Stage 8.32 refuses a 25-run route.")


def _build_guarded_policy_payload() -> dict[str, Any]:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "stage": STAGE,
        "strategy_id": REPAIR_POLICY_ID,
        "origin": "stage8_32_repair_design_no_llm",
        "family": "conditional_owner_trust_overcorrection_guard",
        "source_failure_mode": PREVIOUS_FAILURE_MODE,
        "rules": [
            _rule(
                condition="best_reward_reliable",
                owner="best_reward_group",
                linkage="preserve",
                action="trust_best_reward",
                fallback="weighted_consensus",
            ),
            _rule(
                condition="strong_owner_conflict AND best_reward_misleading",
                owner="contribution_leader",
                linkage="break",
                action="owner_proposal_select",
                fallback="shrinkage_repair",
            ),
            _rule(
                condition="unstable_or_uncertain",
                owner="historical_owner",
                linkage="preserve",
                action="shrinkage_repair",
                fallback="weighted_consensus",
            ),
            _rule(
                condition="always",
                owner="multi_owner",
                linkage="preserve",
                action="weighted_consensus",
                fallback="simple_consensus",
                allow_multi_assignment=True,
            ),
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_guard_spec(
    diagnosis: Mapping[str, Any], overcorrection: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": GUARD_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.31",
        "repair_policy_id": REPAIR_POLICY_ID,
        "previous_failure_mode": str(overcorrection["overcorrection_type"]),
        "guarded_against_overcorrection": True,
        "forbidden_degenerate_pattern": "always_contribution_leader_break",
        "diagnostic_anchor": {
            "owner_proposal_select_count": int(diagnosis["owner_proposal_select_count"]),
            "shrinkage_repair_count": int(diagnosis["shrinkage_repair_count"]),
            "contribution_leader_count": int(diagnosis["contribution_leader_count"]),
            "break_count": int(diagnosis["break_count"]),
            "trust_best_reward_count": int(diagnosis["trust_best_reward_count"]),
            "preserve_count": int(diagnosis["preserve_count"]),
            "best_reward_group_count": int(diagnosis["best_reward_group_count"]),
        },
        "guard_logic": [
            {
                "if": "best_reward_reliable",
                "owner": "best_reward_group",
                "linkage": "preserve",
                "action": "trust_best_reward",
            },
            {
                "elif": "strong_owner_conflict AND best_reward_misleading",
                "owner": "contribution_leader",
                "linkage": "break",
                "action": "owner_proposal_select",
            },
            {
                "elif": "unstable_or_uncertain",
                "owner": "historical_owner_or_multi_owner",
                "linkage": "preserve",
                "action": "shrinkage_repair_or_weighted_consensus",
            },
            {
                "else": "preserve_safety",
                "owner": "multi_owner",
                "linkage": "preserve",
                "action": "weighted_consensus_or_simple_consensus",
            },
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_static_guard_coverage_report() -> dict[str, Any]:
    policy = GuardedOwnerTrustPolicy()
    rows = []
    action_counts: Counter[str] = Counter()
    owner_counts: Counter[str] = Counter()
    linkage_counts: Counter[str] = Counter()
    for fixture in guarded_static_fixtures():
        decision = policy.decide(fixture)
        row = {
            "fixture_id": str(fixture["fixture_id"]),
            "decision": decision,
            "FE_total": 0,
        }
        rows.append(row)
        action_counts[str(decision["coordination_action"])] += 1
        owner_counts[str(decision["shared_variable_owner"])] += 1
        linkage_counts[str(decision["linkage_decision"])] += 1

    branch_counts = _zero_filled_counts(
        action_counts,
        [
            "trust_best_reward",
            "owner_proposal_select",
            "shrinkage_repair",
            "weighted_consensus",
            "simple_consensus",
        ],
    )
    owner_dict = _zero_filled_counts(
        owner_counts,
        ["best_reward_group", "contribution_leader", "historical_owner", "multi_owner"],
    )
    linkage_dict = _zero_filled_counts(linkage_counts, ["preserve", "break"])
    return {
        "schema_version": COVERAGE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.31",
        "repair_policy_id": REPAIR_POLICY_ID,
        "fixture_count": len(rows),
        "fixture_rows": rows,
        "branch_counts": branch_counts,
        "owner_counts": owner_dict,
        "linkage_decision_counts": linkage_dict,
        "all_required_guard_paths_covered": (
            branch_counts["trust_best_reward"] >= 1
            and branch_counts["owner_proposal_select"] >= 1
            and branch_counts["shrinkage_repair"] >= 1
            and branch_counts["weighted_consensus"] >= 1
            and owner_dict["best_reward_group"] >= 1
            and owner_dict["contribution_leader"] >= 1
            and linkage_dict["preserve"] >= 1
            and linkage_dict["break"] >= 1
        ),
        "degenerate_always_contribution_leader_break_avoided": (
            owner_dict["contribution_leader"] < len(rows)
            and linkage_dict["break"] < len(rows)
        ),
        "FE_total": 0,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_claim_boundary_report() -> dict[str, Any]:
    return {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.31",
        "claim_scope": "repair design gate only",
        "allowed_claim": (
            "Stage 8.32 designs a guarded owner-trust repair policy that avoids "
            "the Stage 8.31 always contribution_leader + break failure mode."
        ),
        "policy_repair_selected_for_objective_run": False,
        "official_benchmark_claim_allowed": False,
        "sota_claim_allowed": False,
        "final_performance_claim_allowed": False,
        "forbidden_claims": [
            "SOTA improvement",
            "final objective-value performance improvement",
            "CEC2013 checkpoint improvement",
            "formal 25-run CEC2013 result",
            "objective-loop repair success",
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(stage8_31_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "overcorrection_guard_design_no_objective_no_llm_no_cec",
        "inherited_stage8_31_FE_total": int(stage8_31_ledger["FE_total"]),
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "cec_checkpoint_executed": False,
        "all_extra_fe_counted": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "overcorrection guard / conditional owner-trust repair design",
        "legal_inputs": [
            "artifacts/analysis/stage8_31/failure_diagnosis_report.json",
            "artifacts/analysis/stage8_31/overcorrection_diagnosis.json",
            "artifacts/analysis/stage8_31/branch_usage_diagnosis.json",
            "artifacts/analysis/stage8_31/fe_ledger.json",
            "artifacts/analysis/stage8_31/runtime_boundary.json",
            "artifacts/analysis/stage8_31/next_route_decision.json",
        ],
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "cec_checkpoint_executed": False,
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "new_llm_strategy_generation": False,
            "selected_policy_revision": False,
            "evolution_search": False,
            "objective_loop_execution": False,
            "new_objective_evaluation": False,
            "cec_checkpoint_execution": False,
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
        "status": "PASS",
        "decision": "ROUTE_TO_STATIC_GUARD_SANITY_OR_BOUNDED_CHECKPOINT_GATE",
        "decision_reason": (
            "Stage 8.32 only designs the guarded repair; a later bounded gate "
            "must check whether the guard behaves safely before any formal panel."
        ),
        "next_stage": NEXT_STAGE,
        "allowed_next_work": NEXT_WORK,
        "run_full_25_run_panel_next": False,
        "run_cec_checkpoint_next": False,
        "run_new_objective_next": False,
        "call_llm_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_repair_design_report(
    *,
    diagnosis: Mapping[str, Any],
    overcorrection: Mapping[str, Any],
    coverage: Mapping[str, Any],
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.31",
        "repair_scope": "overcorrection_guard_design_only",
        "repair_policy_id": REPAIR_POLICY_ID,
        "stage8_31_overcorrection_confirmed": bool(
            diagnosis["overcorrection_confirmed"]
        ),
        "stage8_31_overcorrection_type": str(overcorrection["overcorrection_type"]),
        "overcorrection_guard_designed": True,
        "best_reward_reliable_path_preserved": (
            int(coverage["branch_counts"]["trust_best_reward"]) >= 1
        ),
        "owner_conflict_break_path_guarded": (
            int(coverage["branch_counts"]["owner_proposal_select"]) >= 1
            and int(coverage["linkage_decision_counts"]["break"]) == 1
        ),
        "unstable_uncertain_preserve_path_defined": (
            int(coverage["branch_counts"]["shrinkage_repair"]) >= 1
            and int(coverage["linkage_decision_counts"]["preserve"]) >= 1
        ),
        "default_preserve_safety_path_defined": (
            int(coverage["branch_counts"]["weighted_consensus"]) >= 1
        ),
        "all_required_guard_paths_covered": bool(
            coverage["all_required_guard_paths_covered"]
        ),
        "formal_25_run_recommended_now": False,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "cec_checkpoint_executed": False,
        "FE_total": int(ledger["FE_total"]),
        "inherited_stage8_31_FE_total": int(ledger["inherited_stage8_31_FE_total"]),
        "recommended_next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "new_llm_strategy_generation_used": False,
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


def _decision(
    *,
    condition: str,
    owner: str,
    linkage: str,
    action: str,
    fallback: str,
    allow_multi_assignment: bool = False,
) -> dict[str, Any]:
    return {
        "condition": condition,
        "shared_variable_owner": owner,
        "allow_multi_assignment": bool(allow_multi_assignment),
        "linkage_decision": linkage,
        "coordination_action": action,
        "fallback_repair_action": fallback,
    }


def _rule(
    *,
    condition: str,
    owner: str,
    linkage: str,
    action: str,
    fallback: str,
    allow_multi_assignment: bool = False,
) -> dict[str, Any]:
    return _decision(
        condition=condition,
        owner=owner,
        linkage=linkage,
        action=action,
        fallback=fallback,
        allow_multi_assignment=allow_multi_assignment,
    )


def _zero_filled_counts(counter: Counter[str], names: Sequence[str]) -> dict[str, int]:
    return {name: int(counter.get(name, 0)) for name in names}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

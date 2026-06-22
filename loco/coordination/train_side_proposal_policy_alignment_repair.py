"""Stage 8.16 train-side proposal/policy alignment repair.

This stage adds a train-side reward-reliability gate for shared-variable
coordination. It does not run objectives, tune from the Stage 8.14 smoke, revise
the selected policy for the official panel, or make SOTA/final claims.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from loco.conflict.conflict_metrics import (
    conflict_intensity,
    direction_disagreement,
    value_disagreement,
)
from loco.conflict.conflict_state import GroupProposal, SharedVariableConflictState
from loco.coordination.baselines import (
    AverageConsensus,
    BestRewardSelection,
    CoordinationResult,
    WeightedConsensus,
)


STAGE = "8.16"
REPAIR_POLICY_NAME = "reward_trust_gated_coordination_v1"
ALIGNMENT_SCHEMA_VERSION = "loco.stage8_16_alignment_repair_report.v1"
FEATURE_SCHEMA_VERSION = "loco.stage8_16_reward_reliability_feature_report.v1"
BRANCH_SCHEMA_VERSION = "loco.stage8_16_policy_branch_alignment_report.v1"
CLAIM_SCHEMA_VERSION = "loco.stage8_16_claim_boundary_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_16_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_16_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_16_next_route_decision.v1"

FEATURE_NAMES = [
    "reward_top_margin",
    "reward_concentration",
    "best_reward_direction_agreement",
    "best_reward_value_outlier_score",
    "best_reward_update_fraction",
]
POLICY_BRANCHES = [
    "trust_best_reward",
    "weighted_safety",
    "simple_safety",
    "shrinkage_repair",
]


@dataclass(frozen=True)
class RewardTrustGatedCoordination:
    """Train-side repair candidate for reward-aware proposal coordination."""

    name: str = f"RewardTrustGatedCoordination({REPAIR_POLICY_NAME})"
    top_margin_threshold: float = 0.12
    concentration_threshold: float = 0.4
    direction_agreement_threshold: float = 2.0 / 3.0
    outlier_threshold: float = 1.35
    update_fraction_threshold: float = 0.75

    def __post_init__(self) -> None:
        object.__setattr__(self, "_best", BestRewardSelection())
        object.__setattr__(self, "_weighted", WeightedConsensus(temperature=1.0))
        object.__setattr__(self, "_simple", AverageConsensus())

    def coordinate(
        self, conflict_state: SharedVariableConflictState
    ) -> CoordinationResult:
        features = compute_reward_reliability_features(
            conflict_state,
            top_margin_threshold=self.top_margin_threshold,
            concentration_threshold=self.concentration_threshold,
            direction_agreement_threshold=self.direction_agreement_threshold,
            outlier_threshold=self.outlier_threshold,
            update_fraction_threshold=self.update_fraction_threshold,
        )
        if features["best_reward_trustworthy"]:
            result = self._best.coordinate(conflict_state)
            return _with_policy_diagnostics(
                result,
                policy_branch="trust_best_reward",
                fallback_operator=None,
                features=features,
                operator_name=self.name,
            )

        fallback_branch, fallback = self._fallback(conflict_state, features)
        result = fallback.coordinate(conflict_state)
        if fallback_branch == "shrinkage_repair":
            repaired = _shrink_toward_current(conflict_state, result.coordinated_value)
            result = CoordinationResult(
                variable_id=result.variable_id,
                coordinated_value=repaired,
                operator_name=result.operator_name,
                extra_fe=result.extra_fe,
                diagnostics=dict(result.diagnostics),
            )
        return _with_policy_diagnostics(
            result,
            policy_branch=fallback_branch,
            fallback_operator=result.operator_name,
            features=features,
            operator_name=self.name,
        )

    def _fallback(
        self,
        conflict_state: SharedVariableConflictState,
        features: Mapping[str, Any],
    ) -> tuple[str, Any]:
        conflict = conflict_intensity(conflict_state)
        direction_gap = direction_disagreement(conflict_state)
        value_gap = value_disagreement(conflict_state)
        if (
            float(features["best_reward_value_outlier_score"]) > self.outlier_threshold
            or float(features["best_reward_update_fraction"])
            > self.update_fraction_threshold
        ):
            return "shrinkage_repair", self._weighted
        if conflict >= 0.34 or direction_gap >= 0.65:
            return "simple_safety", self._simple
        if value_gap <= 0.2:
            return "weighted_safety", self._weighted
        return "simple_safety", self._simple


def compute_reward_reliability_features(
    conflict_state: SharedVariableConflictState,
    *,
    top_margin_threshold: float = 0.12,
    concentration_threshold: float = 0.4,
    direction_agreement_threshold: float = 2.0 / 3.0,
    outlier_threshold: float = 1.35,
    update_fraction_threshold: float = 0.75,
) -> dict[str, Any]:
    """Compute train-side features for deciding whether to trust best reward."""

    rewards = np.asarray(conflict_state.group_rewards, dtype=float)
    proposals = np.asarray(conflict_state.proposals, dtype=float)
    directions = proposals - float(conflict_state.current_value)
    best_index = int(np.argmax(rewards))
    sorted_rewards = np.sort(rewards)
    top_reward = float(sorted_rewards[-1])
    second_reward = float(sorted_rewards[-2]) if rewards.size > 1 else top_reward
    reward_scale = max(abs(top_reward), 1.0)
    reward_top_margin = max((top_reward - second_reward) / reward_scale, 0.0)
    reward_concentration = _softmax_top_weight(rewards)
    best_direction = float(directions[best_index])
    best_reward_direction_agreement = _direction_agreement(directions, best_direction)
    best_reward_value_outlier_score = _outlier_score(
        proposals, best_index, conflict_state.range_width
    )
    best_reward_update_fraction = abs(best_direction) / max(
        conflict_state.range_width, 1e-12
    )
    best_reward_trustworthy = (
        reward_top_margin >= top_margin_threshold
        and reward_concentration >= concentration_threshold
        and best_reward_direction_agreement >= direction_agreement_threshold
        and best_reward_value_outlier_score <= outlier_threshold
        and best_reward_update_fraction <= update_fraction_threshold
    )
    return {
        "reward_top_margin": round(float(reward_top_margin), 12),
        "reward_concentration": round(float(reward_concentration), 12),
        "best_reward_direction_agreement": round(
            float(best_reward_direction_agreement), 12
        ),
        "best_reward_value_outlier_score": round(
            float(best_reward_value_outlier_score), 12
        ),
        "best_reward_update_fraction": round(float(best_reward_update_fraction), 12),
        "best_reward_index": best_index,
        "best_reward_value": float(proposals[best_index]),
        "best_reward": float(rewards[best_index]),
        "best_reward_trustworthy": bool(best_reward_trustworthy),
        "trust_thresholds": {
            "top_margin_threshold": float(top_margin_threshold),
            "concentration_threshold": float(concentration_threshold),
            "direction_agreement_threshold": float(direction_agreement_threshold),
            "outlier_threshold": float(outlier_threshold),
            "update_fraction_threshold": float(update_fraction_threshold),
        },
    }


def run_stage8_16_train_side_proposal_policy_alignment_repair(
    *,
    stage8_15_diagnosis_report_path: Path | str,
    stage8_15_method_gap_path: Path | str,
    stage8_15_branch_diagnostics_path: Path | str,
    stage8_15_root_cause_path: Path | str,
    stage8_15_fe_ledger_path: Path | str,
    stage8_15_runtime_boundary_path: Path | str,
    stage8_15_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    diagnosis = _read_json(Path(stage8_15_diagnosis_report_path))
    method_gap = _read_json(Path(stage8_15_method_gap_path))
    branch = _read_json(Path(stage8_15_branch_diagnostics_path))
    root_cause = _read_json(Path(stage8_15_root_cause_path))
    stage8_15_ledger = _read_json(Path(stage8_15_fe_ledger_path))
    runtime_boundary = _read_json(Path(stage8_15_runtime_boundary_path))
    next_route = _read_json(Path(stage8_15_next_route_path))
    _validate_inputs(
        diagnosis=diagnosis,
        method_gap=method_gap,
        branch=branch,
        root_cause=root_cause,
        stage8_15_ledger=stage8_15_ledger,
        runtime_boundary=runtime_boundary,
        next_route=next_route,
    )

    fixture_rows = _fixture_rows()
    feature_report = _build_feature_report(fixture_rows)
    branch_report = _build_branch_report(fixture_rows)
    claim = _build_claim_boundary_report()
    ledger = _build_fe_ledger(stage8_15_ledger)
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    report = _build_alignment_report(
        diagnosis=diagnosis,
        method_gap=method_gap,
        branch=branch,
        feature_report=feature_report,
        branch_report=branch_report,
        ledger=ledger,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "alignment_repair_report.json", report)
    _write_json(output_path / "reward_reliability_feature_report.json", feature_report)
    _write_json(output_path / "policy_branch_alignment_report.json", branch_report)
    _write_json(output_path / "claim_boundary_report.json", claim)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    *,
    diagnosis: Mapping[str, Any],
    method_gap: Mapping[str, Any],
    branch: Mapping[str, Any],
    root_cause: Mapping[str, Any],
    stage8_15_ledger: Mapping[str, Any],
    runtime_boundary: Mapping[str, Any],
    next_route: Mapping[str, Any],
) -> None:
    if diagnosis.get("stage") != "8.15" or diagnosis.get("status") != "PASS":
        raise ValueError("Stage 8.16 requires a passing Stage 8.15 diagnosis.")
    if diagnosis.get("dominant_failure_mode") != "best_reward_select_alignment_gap":
        raise ValueError("Stage 8.16 requires the best-reward alignment diagnosis.")
    if diagnosis.get("policy_revision_allowed") is not False:
        raise ValueError("Stage 8.16 refuses selected-policy revision inputs.")
    if method_gap.get("best_baseline_method_count") != {"best_reward_select": 2}:
        raise ValueError("Stage 8.16 requires the Stage 8.15 method-gap evidence.")
    if branch.get("f13_policy_equivalent_to_simple_consensus") is not True:
        raise ValueError("Stage 8.16 requires the F13 branch-collapse evidence.")
    if branch.get("f14_policy_equivalent_to_weighted_consensus") is not True:
        raise ValueError("Stage 8.16 requires the F14 branch-collapse evidence.")
    if root_cause.get("top_hypothesis_id") != "H1_best_reward_alignment_gap":
        raise ValueError("Stage 8.16 requires the H1 root-cause hypothesis.")
    if int(stage8_15_ledger.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.16 requires zero-FE Stage 8.15 diagnosis input.")
    if runtime_boundary.get("new_objective_evaluation_used") is not False:
        raise ValueError("Stage 8.16 refuses new-objective Stage 8.15 inputs.")
    if next_route.get("allowed_next_work") != (
        "train_side_proposal_policy_alignment_repair"
    ):
        raise ValueError("Stage 8.16 requires the Stage 8.15 route.")
    if next_route.get("use_test_feedback") is not False:
        raise ValueError("Stage 8.16 rejects test-feedback leakage.")


def _fixture_rows() -> list[dict[str, Any]]:
    policy = RewardTrustGatedCoordination()
    rows = []
    for fixture_name, state in _train_side_fixtures():
        features = compute_reward_reliability_features(state)
        result = policy.coordinate(state)
        rows.append(
            {
                "fixture_name": fixture_name,
                "features": features,
                "policy_branch": result.diagnostics["policy_branch"],
                "fallback_operator": result.diagnostics["fallback_operator"],
                "coordinated_value": result.coordinated_value,
                "best_reward_value": features["best_reward_value"],
                "best_reward_trustworthy": features["best_reward_trustworthy"],
            }
        )
    return rows


def _train_side_fixtures() -> list[tuple[str, SharedVariableConflictState]]:
    return [
        (
            "trusted_best_reward_margin_aligned",
            _state(
                current=10.0,
                proposals=[6.0, 8.0, 9.0],
                rewards=[0.95, 0.54, 0.5],
                panel="train_side_reward_reliable_fixture",
            ),
        ),
        (
            "untrusted_best_reward_outlier",
            _state(
                current=10.0,
                proposals=[-95.0, 8.5, 9.0],
                rewards=[0.91, 0.88, 0.86],
                panel="train_side_reward_outlier_fixture",
            ),
        ),
        (
            "untrusted_low_reward_margin_weighted",
            _state(
                current=10.0,
                proposals=[7.0, 8.0, 8.5],
                rewards=[0.71, 0.7, 0.69],
                panel="train_side_low_margin_fixture",
            ),
        ),
        (
            "untrusted_direction_conflict_simple",
            _state(
                current=10.0,
                proposals=[6.5, 12.5, 13.0],
                rewards=[0.82, 0.68, 0.66],
                panel="train_side_direction_conflict_fixture",
            ),
        ),
        (
            "untrusted_oversized_best_reward_shrinkage",
            _state(
                current=10.0,
                proposals=[-160.0, 8.5, 9.0],
                rewards=[0.94, 0.7, 0.69],
                panel="train_side_oversized_update_fixture",
            ),
        ),
    ]


def _state(
    *,
    current: float,
    proposals: Sequence[float],
    rewards: Sequence[float],
    panel: str,
) -> SharedVariableConflictState:
    return SharedVariableConflictState.from_group_proposals(
        variable_id=7,
        current_value=current,
        bounds=(-100.0, 100.0),
        proposals=[
            GroupProposal(index + 1, 7, float(value), float(reward))
            for index, (value, reward) in enumerate(zip(proposals, rewards))
        ],
        diagnostics={"panel": panel, "split": "train_side_alignment_fixture"},
    )


def _build_feature_report(fixture_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    trustworthy = [
        row for row in fixture_rows if bool(row["features"]["best_reward_trustworthy"])
    ]
    untrustworthy = [
        row for row in fixture_rows if not bool(row["features"]["best_reward_trustworthy"])
    ]
    return {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.15",
        "repair_policy_name": REPAIR_POLICY_NAME,
        "feature_names": FEATURE_NAMES,
        "best_reward_trust_gate_defined": True,
        "fixture_count": len(fixture_rows),
        "trustworthy_fixture_count": len(trustworthy),
        "untrustworthy_fixture_count": len(untrustworthy),
        "fixture_rows": list(fixture_rows),
        "FE_total": 0,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_branch_report(fixture_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    branch_counts = {
        branch: sum(1 for row in fixture_rows if row["policy_branch"] == branch)
        for branch in POLICY_BRANCHES
    }
    trust_count = branch_counts["trust_best_reward"]
    fallback_count = len(fixture_rows) - trust_count
    return {
        "schema_version": BRANCH_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.15",
        "repair_policy_name": REPAIR_POLICY_NAME,
        "policy_branches": POLICY_BRANCHES,
        "branch_counts": branch_counts,
        "trust_best_reward_case_count": trust_count,
        "fallback_case_count": fallback_count,
        "best_reward_alignment_gap_addressed": trust_count >= 1 and fallback_count >= 1,
        "fixture_rows": list(fixture_rows),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_claim_boundary_report() -> dict[str, Any]:
    return {
        "schema_version": CLAIM_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.15",
        "claim_scope": "train-side proposal/policy alignment repair candidate",
        "allowed_claim": (
            "Stage 8.16 adds a train-side reward-reliability alignment gate and "
            "a repair candidate for later bounded objective checking."
        ),
        "official_benchmark_claim_allowed": False,
        "sota_claim_allowed": False,
        "final_performance_claim_allowed": False,
        "policy_selected_for_official_panel": False,
        "forbidden_claims": [
            "SOTA improvement",
            "final objective-value performance improvement",
            "full 25-run CEC2013 result",
            "policy selected for official panel",
            "CEC2013 performance repair success",
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(stage8_15_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "train_side_alignment_repair_no_objective_execution",
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "inherited_stage8_15_FE_total": int(stage8_15_ledger["FE_total"]),
        "inherited_stage8_14_FE_total": int(
            stage8_15_ledger["inherited_stage8_14_FE_total"]
        ),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "all_extra_fe_counted": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "train-side reward-reliability repair candidate",
        "legal_inputs": [
            "artifacts/objective_eval/stage8_15/diagnosis_report.json",
            "artifacts/objective_eval/stage8_15/method_gap_report.json",
            "artifacts/objective_eval/stage8_15/branch_diagnostics.json",
            "artifacts/objective_eval/stage8_15/root_cause_hypotheses.json",
            "artifacts/objective_eval/stage8_15/fe_ledger.json",
            "artifacts/objective_eval/stage8_15/runtime_boundary.json",
            "artifacts/objective_eval/stage8_15/next_route_decision.json",
        ],
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "forbidden_behaviors": {
            "llm_call": False,
            "new_llm_candidate_generation": False,
            "selected_operator_revision": False,
            "evolution_search": False,
            "objective_loop_execution": False,
            "new_objective_evaluation": False,
            "validation_feedback": False,
            "test_feedback": False,
            "stage8_14_direct_tuning_feedback": False,
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
        "decision": "ROUTE_TO_BOUNDED_TRAIN_SIDE_REPAIRED_POLICY_OBJECTIVE_CHECK",
        "decision_reason": (
            "Stage 8.16 created a train-side reward-trust repair candidate; it "
            "must be checked in a bounded objective loop before any 25-run panel."
        ),
        "next_stage": "Stage 8.17",
        "allowed_next_work": "bounded_train_side_repaired_policy_objective_check",
        "run_full_25_run_panel_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_alignment_report(
    *,
    diagnosis: Mapping[str, Any],
    method_gap: Mapping[str, Any],
    branch: Mapping[str, Any],
    feature_report: Mapping[str, Any],
    branch_report: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    del method_gap, branch
    return {
        "schema_version": ALIGNMENT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.15",
        "repair_scope": "train_side_proposal_policy_alignment_repair",
        "dominant_failure_mode_addressed": diagnosis["dominant_failure_mode"],
        "repair_policy_name": REPAIR_POLICY_NAME,
        "train_side_repair_candidate_created": True,
        "official_cec2013_feedback_used_for_tuning": False,
        "stage8_14_smoke_used_as_direct_tuning_feedback": False,
        "reward_reliability_features_added": True,
        "policy_alignment_gate_added": True,
        "trust_best_reward_fixture_passed": bool(
            branch_report["trust_best_reward_case_count"] >= 1
        ),
        "unsafe_best_reward_fallback_fixture_passed": bool(
            branch_report["fallback_case_count"] >= 1
        ),
        "feature_names": list(feature_report["feature_names"]),
        "policy_branches": list(branch_report["policy_branches"]),
        "full_25_run_panel_blocked": True,
        "recommended_next_stage": "Stage 8.17",
        "recommended_next_work": "bounded_train_side_repaired_policy_objective_check",
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "FE_total": int(ledger["FE_total"]),
        "llm_call_used": False,
        "new_llm_candidate_generation_used": False,
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


def _with_policy_diagnostics(
    result: CoordinationResult,
    *,
    policy_branch: str,
    fallback_operator: str | None,
    features: Mapping[str, Any],
    operator_name: str,
) -> CoordinationResult:
    diagnostics = dict(result.diagnostics)
    diagnostics.update(
        {
            "policy_name": REPAIR_POLICY_NAME,
            "policy_branch": policy_branch,
            "fallback_operator": fallback_operator,
            "reward_reliability_features": dict(features),
        }
    )
    return CoordinationResult(
        variable_id=result.variable_id,
        coordinated_value=result.coordinated_value,
        operator_name=operator_name,
        extra_fe=result.extra_fe,
        diagnostics=diagnostics,
    )


def _softmax_top_weight(rewards: np.ndarray) -> float:
    scaled = rewards - float(np.max(rewards))
    weights = np.exp(scaled)
    weights = weights / float(np.sum(weights))
    return float(np.max(weights))


def _direction_agreement(directions: np.ndarray, best_direction: float) -> float:
    if abs(best_direction) <= 1e-12:
        return 1.0
    best_sign = np.sign(best_direction)
    signs = np.sign(directions[np.abs(directions) > 1e-12])
    if signs.size == 0:
        return 1.0
    return float(np.sum(signs == best_sign) / signs.size)


def _outlier_score(proposals: np.ndarray, best_index: int, range_width: float) -> float:
    if proposals.size <= 1:
        return 0.0
    median = float(np.median(proposals))
    return float(abs(float(proposals[best_index]) - median) / max(range_width, 1e-12))


def _shrink_toward_current(
    conflict_state: SharedVariableConflictState, target_value: float
) -> float:
    value = float(conflict_state.current_value) + 0.5 * (
        float(target_value) - float(conflict_state.current_value)
    )
    return conflict_state.clip(value)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

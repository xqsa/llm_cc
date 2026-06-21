from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage4_coordination_family_space.yaml"
DOC = ROOT / "docs" / "stage4" / "coordination_family_literature_review.md"
README = ROOT / "README.md"

REQUIRED_FAMILY_IDS = {
    "F0",
    "F1",
    "F2",
    "F3",
    "F4",
    "F5",
    "F6",
    "F7",
    "F8",
    "F9",
}

REQUIRED_FAMILY_NAMES = {
    "identity_no_coord_low_overlap_safeguard",
    "consensus",
    "robust_consensus",
    "reward_or_contribution_weighting",
    "winner_or_soft_selection",
    "dampening_trust_region_like_step_control",
    "projection_repair",
    "residual_dual_memory_conflict_balancing",
    "temporal_hysteresis_anti_oscillation",
    "conditional_composition_within_typed_ast",
}

REQUIRED_ALLOWED_PRIMITIVES = {
    "no_coord",
    "weighted_consensus",
    "robust_consensus",
    "best_reward_select",
    "dampening",
    "projection",
    "repair",
    "residual_balance",
    "temporal_hysteresis",
    "conditional",
}

FORBIDDEN_TOKENS = {
    "optimizer",
    "controller",
    "scheduler",
    "optimizer_selection",
    "BaseOpt modification",
    "function_id",
    "benchmark_name",
    "true_optimum",
    "test_metadata",
    "future_evaluations",
    "hidden_test_information",
}


def test_stage4_family_space_config_locks_required_families_and_boundaries():
    assert CONFIG.is_file(), CONFIG
    text = CONFIG.read_text(encoding="utf-8")

    assert 'stage: "3.7"' in text
    assert 'status: "READY_FOR_STAGE4_TRAIN_ONLY_SEARCH_AFTER_FAMILY_LOCK"' in text
    assert 'target_scope: "shared_variables_only"' in text
    assert 'allowed_split: "train"' in text
    assert 'validation_usage: "selection only after train search"' in text
    assert 'test_usage: "sealed final reporting only"' in text
    assert 'fe_accounting_policy: "count_all_extra_function_evaluations"' in text
    assert "not_performance_claim: true" in text
    assert "no_llm_call: true" in text
    assert "no_evolution_run: true" in text
    assert "no_ast_execution: true" in text
    assert "no_objective_evaluation: true" in text
    assert "no_test_feedback: true" in text

    for family_id in REQUIRED_FAMILY_IDS:
        assert f'id: "{family_id}"' in text
    for family_name in REQUIRED_FAMILY_NAMES:
        assert f'name: "{family_name}"' in text
    for primitive in REQUIRED_ALLOWED_PRIMITIVES:
        assert f'"{primitive}"' in text
    for token in FORBIDDEN_TOKENS:
        assert f'"{token}"' in text


def test_stage4_family_literature_review_documents_sources_and_loco_mapping():
    assert DOC.is_file(), DOC
    text = DOC.read_text(encoding="utf-8")

    assert "Stage 3.7" in text
    assert "Coordination Family Literature Grounding" in text
    assert "not a performance claim" in text
    assert "shared variables only" in text
    assert "typed coordination operator AST" in text
    assert (
        "FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair"
        in text
    )

    required_source_markers = [
        "CEC2013 LSGO",
        "OEDG",
        "HCC",
        "ADMM",
        "robust aggregation",
        "contribution-based cooperative coevolution",
        "trust-region",
        "projection",
    ]
    for marker in required_source_markers:
        assert marker in text

    for family_id in REQUIRED_FAMILY_IDS:
        assert f"### {family_id}" in text
    for family_name in REQUIRED_FAMILY_NAMES:
        assert family_name in text
    for token in FORBIDDEN_TOKENS:
        assert token in text


def test_readme_reports_stage3_7_family_lock_as_pre_stage4_gate():
    text = README.read_text(encoding="utf-8")

    assert "Current repository state: `Stage 6.1 PASS`" in text
    assert (
        "Coordination Family Literature Grounding and Allowed Vocabulary Lock" in text
    )
    assert "Stage 3.7 added the Coordination Family Literature Grounding" in text
    assert "Stage 4 train-only evolution/search" in text
    assert (
        "Do not run Stage 4 evolution/search before the Stage 3.7 family lock" in text
    )
    assert "not a performance claim" in text

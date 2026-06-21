from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage7_0_objective_eval_protocol.yaml"
STAGE_DOC = ROOT / "docs" / "stage7" / "stage7_0_objective_eval_protocol.md"
SELF_CHECK = ROOT / "docs" / "stage7" / "stage7_0_self_check_report.md"
README = ROOT / "README.md"


REQUIRED_BASELINES = {
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "selected_loco_operator",
}

REQUIRED_PANELS = {
    "synthetic_no_overlap_panel",
    "synthetic_low_overlap_panel",
    "synthetic_conflicting_overlap_panel",
    "synthetic_high_overlap_panel",
}

REQUIRED_OBJECTIVE_METRICS = {
    "final_best_objective",
    "best_so_far_curve",
    "anytime_auc",
    "mean_std_over_seeds",
    "win_tie_loss_vs_baselines",
}

REQUIRED_MECHANISM_METRICS = {
    "conflict_intensity_over_time",
    "proposal_disagreement_over_time",
    "shared_variable_oscillation",
    "coordination_update_size",
    "distance_to_best_reward_proposal",
    "shared_conflict_frequency",
}

REQUIRED_FE_FIELDS = {
    "FE_grouping",
    "FE_proposal",
    "FE_coordination_extra",
    "FE_repair",
    "FE_global_objective",
    "FE_total",
}

FORBIDDEN_SCOPE_MARKERS = {
    "no LLM call",
    "no new candidate generation",
    "no selected-operator revision",
    "no evolution/search run",
    "no objective benchmark run",
    "no test-feedback tuning",
    "no BaseOpt modification",
    "no optimizer/controller/scheduler generation",
    "not a performance claim",
}


def test_stage7_0_protocol_config_locks_objective_level_eval_boundary() -> None:
    assert CONFIG.is_file(), CONFIG
    text = CONFIG.read_text(encoding="utf-8")

    assert 'stage: "7.0"' in text
    assert 'name: "Objective-Level Large-Scale Evaluation Protocol Lock"' in text
    assert "LOCO-CC objective loop" in text
    assert "fixed BaseOpt" in text
    assert "frozen selected_loco_operator" in text
    assert "shared-variable conflict states" in text
    assert "global objective evaluation" in text
    assert "oracle grouping" in text
    assert "detected grouping" in text
    assert "CEC2013 F13/F14 optional" in text

    for baseline in REQUIRED_BASELINES:
        assert baseline in text
    for panel in REQUIRED_PANELS:
        assert panel in text
    for metric in REQUIRED_OBJECTIVE_METRICS:
        assert metric in text
    for metric in REQUIRED_MECHANISM_METRICS:
        assert metric in text
    for field in REQUIRED_FE_FIELDS:
        assert field in text
    for marker in FORBIDDEN_SCOPE_MARKERS:
        assert marker in text

    assert "objective_evaluation_protocol_locked: true" in text
    assert "large_scale_runner_implemented: false" in text
    assert "objective_benchmark_run: false" in text
    assert "next_status: READY_FOR_STAGE7_1_MINIMAL_OBJECTIVE_LOOP_PILOT" in text


def test_stage7_0_docs_and_readme_record_claim_boundary_and_next_step() -> None:
    for path in [STAGE_DOC, SELF_CHECK]:
        assert path.is_file(), path

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )

    assert "Stage 7.0" in combined
    assert "Objective-Level Large-Scale Evaluation Protocol Lock" in combined
    assert "LOCO-CC" in combined
    assert "objective-level evaluation protocol" in combined
    assert "Stage 7.1: Minimal LOCO-CC Objective Loop Pilot" in combined
    assert "Current repository state: `Stage 7.2 PASS`" in combined
    assert "Stage 7.0    objective-level evaluation protocol lock" in combined
    assert "Stage 7.1    minimal LOCO-CC objective loop pilot" in combined
    assert "Stage 7.2    synthetic large-scale objective panel" in combined

    for baseline in REQUIRED_BASELINES:
        assert baseline in combined
    for panel in REQUIRED_PANELS:
        assert panel in combined
    for field in REQUIRED_FE_FIELDS:
        assert field in combined
    for marker in FORBIDDEN_SCOPE_MARKERS:
        assert marker in combined

    assert "not an objective-value performance claim" in combined
    assert "does not run objective benchmark" in combined
    assert "does not implement the objective-loop runner" in combined
    assert "paper claim polishing should wait for Stage 7.1/7.2 evidence" in combined

import csv
import json
import math

from loco.conflict.longitudinal_metrics import longitudinal_conflict_reduction_ratio
from loco.experiments.stage2_multiround_runner import (
    Stage21BConfig,
    Stage21BSetting,
    run_stage2_1b_multiround,
)


def _small_config(tmp_path):
    return Stage21BConfig(
        settings=[
            Stage21BSetting(
                topology="line",
                dimension=100,
                overlap_ratio=0.05,
                seeds=[0],
            ),
            Stage21BSetting(
                topology="ring",
                dimension=100,
                overlap_ratio=0.10,
                seeds=[1],
            ),
            Stage21BSetting(
                topology="random_graph",
                dimension=100,
                overlap_ratio=0.20,
                seeds=[2],
            ),
        ],
        rounds=5,
        output_json=tmp_path / "multiround.json",
        output_csv=tmp_path / "summary.csv",
        output_report=tmp_path / "report.md",
    )


def test_stage2_1b_multiround_outputs_artifacts_and_boundaries(tmp_path) -> None:
    config = _small_config(tmp_path)
    result = run_stage2_1b_multiround(config)

    assert result["stage"] == "2.1B"
    assert result["rounds"] == 5
    assert result["boundary"]["llm_used"] is False
    assert result["boundary"]["evolution_used"] is False
    assert result["boundary"]["optimizer_implemented"] is False
    assert result["boundary"]["benchmark_objective_modified"] is False
    assert result["boundary"]["metric_claim"] == "multiround_evidence_not_sota_claim"
    assert result["panel"]["setting_count"] == 3
    assert result["panel"]["run_count"] == 15
    assert result["panel"]["operator_count"] == 5

    assert config.output_json.is_file()
    assert config.output_csv.is_file()
    assert config.output_report.is_file()
    assert b"\r\n" not in config.output_json.read_bytes()
    assert b"\r\n" not in config.output_csv.read_bytes()
    assert b"\r\n" not in config.output_report.read_bytes()
    assert json.loads(config.output_json.read_text(encoding="utf-8")) == result

    rows = list(csv.DictReader(config.output_csv.open(encoding="utf-8", newline="")))
    assert len(rows) == 15
    required_columns = {
        "setting_id",
        "topology",
        "dimension",
        "overlap_ratio",
        "seed",
        "operator",
        "rounds",
        "longitudinal_conflict_reduction_ratio",
        "mean_conflict_before",
        "mean_regenerated_conflict_next",
        "proposal_consensus_collapse_ratio_mean",
        "conflict_oscillation",
        "conflict_persistence_over_rounds",
        "consensus_instability_over_rounds",
        "objective_improvement_per_fe",
        "FE_total",
        "FE_commit_evaluation",
        "FE_analysis_only",
        "cross_baseline_evaluations_shared",
    }
    assert required_columns.issubset(rows[0])

    report = config.output_report.read_text(encoding="utf-8")
    assert (
        "Stage 2.1B Multi-round Post-Coordination Regenerated Conflict Evidence"
        in report
    )
    assert "不是 optimizer-loop performance claim" in report
    assert "No LLM / no evolution / no optimizer" in report


def test_stage2_1b_same_seed_deterministic_and_metric_contract(tmp_path) -> None:
    first = run_stage2_1b_multiround(_small_config(tmp_path / "a"))
    second = run_stage2_1b_multiround(_small_config(tmp_path / "b"))

    assert first == second
    for run in first["runs"]:
        assert run["rounds"] == 5
        assert len(run["round_log"]) == 5
        assert run["cross_baseline_evaluations_shared"] is False
        assert run["FE_analysis_only"] == 0
        assert run["FE_commit_evaluation"] == 5
        assert run["FE_total"] == run["fe_accounting"]["fe_total"]
        assert run["FE_total"] == (
            run["fe_accounting"]["fe_grouping"]
            + run["fe_accounting"]["fe_proposal"]
            + run["fe_accounting"]["fe_coordination_extra"]
            + run["fe_accounting"]["fe_repair"]
        )
        assert "conflict_reduction_ratio" not in run
        assert "proposal_consensus_collapse_ratio_mean" in run
        assert run["longitudinal_metric_source"] == "next_round_regenerated_conflict"
        assert run["proposal_metric_source"] == "same_round_proposal_collapse"

        conflict_before = [row["conflict_before"] for row in run["round_log"]]
        regenerated_next = [
            row["regenerated_conflict_next"] for row in run["round_log"]
        ]
        same_round_after = [
            row["same_round_conflict_after"] for row in run["round_log"]
        ]
        expected_longitudinal = longitudinal_conflict_reduction_ratio(
            conflict_before,
            regenerated_next,
        )
        same_round_reduction = longitudinal_conflict_reduction_ratio(
            conflict_before,
            same_round_after,
        )
        assert math.isclose(
            run["longitudinal_conflict_reduction_ratio"],
            expected_longitudinal,
        )
        if run["operator"] != "NoCoordination":
            assert same_round_reduction >= run["longitudinal_conflict_reduction_ratio"]

        for metric_name in (
            "longitudinal_conflict_reduction_ratio",
            "conflict_oscillation",
            "conflict_persistence_over_rounds",
            "consensus_instability_over_rounds",
            "objective_improvement_per_fe",
            "proposal_consensus_collapse_ratio_mean",
        ):
            assert math.isfinite(run[metric_name])
            assert run[metric_name] >= 0.0

        for round_row in run["round_log"]:
            assert set(round_row["changed_variables"]).issubset(
                set(round_row["shared_variables"])
            )
            assert round_row["regenerated_conflict_next"] >= 0.0
            assert round_row["same_round_conflict_after"] >= 0.0


def test_stage2_1b_default_config_covers_required_panel(tmp_path) -> None:
    config = Stage21BConfig(
        output_json=tmp_path / "default.json",
        output_csv=tmp_path / "default.csv",
        output_report=tmp_path / "default.md",
    )

    settings = config.normalized_settings()

    assert config.rounds >= 5
    assert {setting.topology for setting in settings} == {
        "line",
        "ring",
        "random_graph",
    }
    assert {setting.dimension for setting in settings} >= {100, 500, 1000}
    assert {setting.overlap_ratio for setting in settings} >= {0.05, 0.10, 0.20, 0.30}
    assert {seed for setting in settings for seed in setting.seeds} >= {0, 1, 2}

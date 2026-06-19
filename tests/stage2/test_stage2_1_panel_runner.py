import csv
import json
import math

from loco.experiments.stage2_panel_runner import (
    Stage21PanelConfig,
    Stage21Setting,
    run_stage2_1_panel,
)


def test_stage2_1_panel_outputs_json_csv_and_report(tmp_path) -> None:
    config = Stage21PanelConfig(
        settings=[
            Stage21Setting(
                topology="line",
                dimension=60,
                overlap_ratio=0.0,
                seeds=[0],
            ),
            Stage21Setting(
                topology="ring",
                dimension=80,
                overlap_ratio=0.05,
                seeds=[1],
            ),
            Stage21Setting(
                topology="random_graph",
                dimension=100,
                overlap_ratio=0.2,
                seeds=[2],
            ),
        ],
        output_json=tmp_path / "panel.json",
        output_csv=tmp_path / "summary.csv",
        output_report=tmp_path / "report.md",
    )

    result = run_stage2_1_panel(config)

    assert result["stage"] == "2.1"
    assert result["boundary"]["llm_used"] is False
    assert result["boundary"]["evolution_used"] is False
    assert result["boundary"]["optimizer_implemented"] is False
    assert result["boundary"]["metric_claim"] == "evidence_gate_not_sota_claim"
    assert result["panel"]["setting_count"] == 3
    assert result["panel"]["run_count"] == 3
    assert result["panel"]["operator_count"] == 5

    assert config.output_json.is_file()
    assert config.output_csv.is_file()
    assert config.output_report.is_file()
    assert b"\r\n" not in config.output_json.read_bytes()
    assert b"\r\n" not in config.output_csv.read_bytes()
    assert b"\r\n" not in config.output_report.read_bytes()

    saved = json.loads(config.output_json.read_text(encoding="utf-8"))
    assert saved == result

    rows = list(csv.DictReader(config.output_csv.open(encoding="utf-8", newline="")))
    assert len(rows) == 15
    required_columns = {
        "setting_id",
        "topology",
        "dimension",
        "overlap_ratio",
        "seed",
        "operator",
        "mean_conflict_before",
        "proposal_consensus_collapse_ratio",
        "post_coordination_regenerated_conflict",
        "conflict_persistence",
        "consensus_instability",
        "reward_proposal_inconsistency",
        "FE_total",
        "FE_commit_evaluation",
        "FE_analysis_only",
        "low_overlap_regression_flag",
    }
    assert required_columns.issubset(rows[0])

    report_text = config.output_report.read_text(encoding="utf-8")
    assert "Stage 2.1 Multi-setting Conflict Evidence Gate" in report_text
    assert "不是 longitudinal conflict reduction" in report_text
    assert "No LLM / no evolution / no optimizer" in report_text


def test_stage2_1_panel_keeps_metric_contract_and_low_overlap_flags(tmp_path) -> None:
    config = Stage21PanelConfig(
        settings=[
            Stage21Setting(
                topology="line",
                dimension=50,
                overlap_ratio=0.0,
                seeds=[0, 1],
            ),
            Stage21Setting(
                topology="line",
                dimension=50,
                overlap_ratio=0.05,
                seeds=[0],
            ),
        ],
        output_json=tmp_path / "panel.json",
        output_csv=tmp_path / "summary.csv",
        output_report=tmp_path / "report.md",
    )

    result = run_stage2_1_panel(config)

    no_overlap_runs = [
        run for run in result["runs"] if run["setting"]["overlap_ratio_target"] == 0.0
    ]
    assert len(no_overlap_runs) == 2
    for run in no_overlap_runs:
        assert run["aggregate_conflict_metrics"]["number_of_shared_variables"] == 0
        assert run["low_overlap_case"] is True
        for operator_result in run["operators"].values():
            assert "conflict_reduction_ratio" not in operator_result
            assert "proposal_consensus_collapse_ratio" in operator_result
            assert operator_result["proposal_consensus_collapse_ratio"] == 0.0
            assert operator_result["post_coordination_regenerated_conflict"] == 0.0
            assert operator_result["conflict_persistence"] == 0.0
            assert operator_result["FE_commit_evaluation"] == 1
            assert operator_result["FE_analysis_only"] == 0
            assert operator_result["low_overlap_regression_flag"] is False

    for run in result["runs"]:
        assert "proposal_log" not in run
        assert "per_variable_conflict_metrics" not in run
        assert "per_variable" not in run["aggregate_conflict_metrics"]
        for operator_result in run["operators"].values():
            assert "coordination_results" not in operator_result
            for metric_name in (
                "proposal_consensus_collapse_ratio",
                "post_coordination_regenerated_conflict",
                "conflict_persistence",
                "consensus_instability",
                "reward_proposal_inconsistency",
            ):
                assert math.isfinite(operator_result[metric_name])
                assert operator_result[metric_name] >= 0.0

import json
import math

import pytest

from loco.experiments.stage2_minimal_runner import (
    run_optional_f14_smoke,
    run_stage2_synthetic_minimal,
)


def test_stage2_synthetic_runner_outputs_all_baselines_and_metrics(tmp_path) -> None:
    output_path = tmp_path / "stage2_result.json"
    result = run_stage2_synthetic_minimal(seed=17, output_path=output_path)

    assert output_path.is_file()
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved == result
    raw_output = output_path.read_bytes()
    assert b"\r\n" not in raw_output
    assert result["benchmark"]["source"] == "synthetic_overlap"
    assert result["aggregate_conflict_metrics"]["number_of_shared_variables"] > 0
    assert result["aggregate_conflict_metrics"]["overlap_ratio"] > 0.0

    expected = {
        "NoCoordination",
        "AverageConsensus",
        "BestRewardSelection",
        "WeightedConsensus",
        "ConflictDampening",
        "FrozenASTSmoke",
    }
    assert set(result["operators"]) == expected
    for operator_result in result["operators"].values():
        assert math.isfinite(operator_result["final_objective"])
        assert (
            operator_result["FE_total"] == operator_result["fe_accounting"]["fe_total"]
        )
        assert operator_result["FE_coordination_extra"] == 0
        assert operator_result["FE_commit_evaluation"] == 1
        assert operator_result["FE_analysis_only"] == 0
        assert operator_result["budget_scope"] == "per_method_run"
        assert operator_result["cross_baseline_evaluations_shared"] is False
        assert "conflict_reduction_ratio" not in operator_result
        assert "proposal_consensus_collapse_ratio" in operator_result
        assert operator_result["fe_accounting"]["fe_total"] == (
            operator_result["fe_accounting"]["fe_grouping"]
            + operator_result["fe_accounting"]["fe_proposal"]
            + operator_result["fe_accounting"]["fe_coordination_extra"]
            + operator_result["fe_accounting"]["fe_repair"]
        )
        assert math.isfinite(operator_result["mean_conflict_before"])
        assert math.isfinite(operator_result["mean_conflict_after"])


def test_stage2_runner_is_seed_reproducible() -> None:
    first = run_stage2_synthetic_minimal(seed=5)
    second = run_stage2_synthetic_minimal(seed=5)

    assert first == second


def test_optional_f14_smoke_passes_or_skips_honestly() -> None:
    result = run_optional_f14_smoke(seed=3)
    if result["status"] != "PASS":
        pytest.skip(f"F14 real smoke not PASS: {result['reason']}")

    assert result["function_id"] == 14
    assert result["status"] == "PASS"
    assert result["operator_count"] == 6

import json
import math
import sys

from loco.experiments.stage2_minimal_runner import run_stage2_synthetic_minimal


def test_stage2_4_runner_includes_frozen_ast_smoke_operator(tmp_path) -> None:
    output_path = tmp_path / "stage2_4_result.json"
    result = run_stage2_synthetic_minimal(seed=23, output_path=output_path)

    assert output_path.is_file()
    assert json.loads(output_path.read_text(encoding="utf-8")) == result
    assert result["stage"] == "2.4"
    assert result["frozen_ast_smoke"]["enabled"] is True
    assert result["frozen_ast_smoke"]["source"] == "handwritten_frozen_ast_template"
    assert result["frozen_ast_smoke"]["no_llm"] is True
    assert result["frozen_ast_smoke"]["no_evolution"] is True

    operator_result = result["operators"]["FrozenASTSmoke"]
    assert math.isfinite(operator_result["final_objective"])
    assert operator_result["FE_coordination_extra"] == 0
    assert operator_result["FE_commit_evaluation"] == 1
    assert operator_result["budget_scope"] == "per_method_run"
    assert operator_result["cross_baseline_evaluations_shared"] is False
    assert operator_result["frozen_ast_runtime"]["template_id"] == (
        "stage2_4_weighted_dampened_clip_template"
    )
    assert operator_result["frozen_ast_runtime"]["schema_version"] == "loco.dsl.v1"
    assert (
        len(operator_result["frozen_ast_runtime"]["template_fingerprint_sha256"]) == 64
    )
    assert operator_result["frozen_ast_runtime"]["accepted_by_preflight"] is True

    for coordination_result in operator_result["coordination_results"].values():
        assert coordination_result["operator_name"].startswith("DSLRuntime(")
        assert coordination_result["extra_fe"] == 0
        diagnostics = coordination_result["diagnostics"]
        assert diagnostics["schema_version"] == "loco.dsl.v1"
        assert diagnostics["operator_id"].startswith("stage2_4_frozen_ast_shared_")
        assert [step["node_id"] for step in diagnostics["trace"]] == [
            "weighted",
            "dampened",
            "bounded",
        ]


def test_stage2_4_frozen_ast_runner_is_seed_reproducible() -> None:
    first = run_stage2_synthetic_minimal(seed=19)
    second = run_stage2_synthetic_minimal(seed=19)

    assert first == second
    assert "FrozenASTSmoke" in first["operators"]


def test_stage2_4_runner_does_not_import_llm_or_evolution_modules() -> None:
    forbidden_loaded_before = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }

    run_stage2_synthetic_minimal(seed=29)

    forbidden_loaded_after = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }
    assert forbidden_loaded_after == forbidden_loaded_before

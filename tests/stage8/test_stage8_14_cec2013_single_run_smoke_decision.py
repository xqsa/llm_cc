import json
from pathlib import Path

import numpy as np


ROOT = Path("E:/llm_cc")
CONFIG = ROOT / "configs" / "stage8_14_cec2013_single_run_smoke_decision.yaml"
STAGE8_13_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_13"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_14"
SMOKE_REPORT = OUTPUT_DIR / "single_run_smoke_report.json"
TRACE = OUTPUT_DIR / "objective_trace.jsonl"
METHOD_SUMMARY = OUTPUT_DIR / "method_summary.json"
WIN_LOSS = OUTPUT_DIR / "win_loss_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_14_cec2013_single_run_smoke_decision.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_14_self_check_report.md"
README = ROOT / "README.md"


class FakeCECProblem:
    def __init__(self, function_id: int):
        self.function_id = function_id
        self._dimension = 24 if function_id == 13 else 18
        self._bounds = (-5.0, 5.0)
        self._groups = (
            (0, 1, 2, 3, 7),
            (7, 8, 9, 10, 11),
            (12, 13, 7, 14, 15),
        )
        self.fe_count = 0

    def dimension(self) -> int:
        return self._dimension

    def bounds(self):
        return (
            np.full(self._dimension, self._bounds[0], dtype=float),
            np.full(self._dimension, self._bounds[1], dtype=float),
        )

    def grouping(self):
        return [list(group) for group in self._groups]

    def shared_variables(self):
        return {7}

    def metadata(self):
        return {
            "function_id": self.function_id,
            "source": "fake_cec2013",
            "D_formula": 905,
            "D_api": 1000,
            "overlap_semantics": (
                "conforming_overlap"
                if self.function_id == 13
                else "conflicting_overlap"
            ),
            "adapter_mode": (
                "implementation_api_adapter"
                if self.function_id == 13
                else "direct_metabox_dimension"
            ),
            "shared_variable_count": 1,
            "overlap_ratio": 1 / self._dimension,
        }

    def evaluate(self, vector) -> float:
        self.fe_count += 1
        x = np.asarray(vector, dtype=float)
        target = -0.2 if self.function_id == 13 else -0.35
        return float(np.sum((x - target) ** 2))


def test_stage8_14_runs_one_cec2013_overlap_smoke_and_routes(tmp_path) -> None:
    from loco.coordination.cec2013_single_run_smoke_decision import (
        run_stage8_14_cec2013_single_run_smoke_decision,
    )

    report = run_stage8_14_cec2013_single_run_smoke_decision(
        stage8_13_design_report_path=STAGE8_13_DIR / "formal_sota_experiment_design.json",
        stage8_13_budget_lock_path=STAGE8_13_DIR / "budget_lock.json",
        stage8_13_function_scope_path=STAGE8_13_DIR / "function_scope_lock.json",
        stage8_13_claim_gate_path=STAGE8_13_DIR / "claim_gate.json",
        stage8_13_runtime_boundary_path=STAGE8_13_DIR / "runtime_boundary.json",
        stage8_13_next_route_path=STAGE8_13_DIR / "next_route_decision.json",
        output_dir=tmp_path,
        problem_loader=lambda function_id: FakeCECProblem(function_id),
        smoke_function_ids=[13, 14],
        smoke_seed=0,
        smoke_max_fe=12,
        promising_delta_threshold=0.0,
    )

    assert report["stage"] == "8.14"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.13"
    assert report["smoke_scope"] == "cec2013_single_run_overlap_smoke"
    assert report["benchmark_suite"] == "CEC2013_LSGO"
    assert report["policy_name"] == "regime_safe_adaptive_shrinkage_v1"
    assert report["run_count"] == 1
    assert report["smoke_seed"] == 0
    assert report["function_ids"] == ["F13", "F14"]
    assert report["function_count"] == 2
    assert report["full_formal_run_count"] == 25
    assert report["full_formal_function_count"] == 15
    assert report["not_full_25_run_panel"] is True
    assert report["not_full_f1_f15_panel"] is True
    assert report["full_official_budget_deferred"] is True
    assert report["single_run_smoke_executed"] is True
    assert report["official_cec2013_problem_loaded"] is True
    assert report["objective_loop_executed"] is True
    assert report["new_objective_evaluation_used"] is True
    assert report["baseline_comparison_made"] is True
    assert report["method_count"] >= 5
    assert report["trace_row_count"] > 0
    assert report["FE_total"] > 0
    assert report["FE_global_objective"] > 0
    assert report["stage8_14_route_decision"] in {
        "PROMISING_SINGLE_RUN_PROCEED_TO_25_RUN_PANEL",
        "NOT_PROMISING_SINGLE_RUN_DIAGNOSE_BEFORE_25_RUN_PANEL",
    }
    assert report["recommended_next_stage"] == "Stage 8.15"

    for flag in [
        "llm_call_used",
        "new_candidate_generation_used",
        "selected_operator_revision_used",
        "evolution_search_used",
        "validation_feedback_used",
        "test_feedback_used",
        "reported_results_used_as_runtime_feedback",
        "baseopt_modified",
        "optimizer_generation_used",
        "controller_scheduler_generation_used",
    ]:
        assert report[flag] is False
    assert report["not_sota_claim"] is True
    assert report["not_final_performance_claim"] is True

    trace_rows = [
        json.loads(line)
        for line in (tmp_path / "objective_trace.jsonl").read_text().splitlines()
    ]
    assert trace_rows
    assert sorted({row["function_id"] for row in trace_rows}) == ["F13", "F14"]
    assert {row["run_index"] for row in trace_rows} == {1}
    assert {row["seed"] for row in trace_rows} == {0}
    assert all(row["official_cec2013_smoke"] is True for row in trace_rows)
    assert all(row["FE_global_objective"] == 1 for row in trace_rows)

    method_summary = json.loads((tmp_path / "method_summary.json").read_text())
    win_loss = json.loads((tmp_path / "win_loss_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert method_summary["run_count"] == 1
    assert method_summary["function_ids"] == ["F13", "F14"]
    assert win_loss["comparison_case_count"] == 2
    assert win_loss["baseline_comparison_made"] is True
    assert ledger["FE_total"] == report["FE_total"]
    assert ledger["run_count"] == 1
    assert ledger["all_extra_fe_counted"] is True
    assert boundary["not_full_25_run_panel"] is True
    assert boundary["official_cec2013_panel_run"] is False
    assert route["next_stage"] == "Stage 8.15"
    assert route["run_full_25_run_panel_next"] in {True, False}
    assert route["run_failure_diagnosis_next"] in {True, False}
    assert route["use_test_feedback"] is False


def test_stage8_14_committed_artifacts_docs_and_readme_record_single_run_gate() -> None:
    required = [
        CONFIG,
        SMOKE_REPORT,
        TRACE,
        METHOD_SUMMARY,
        WIN_LOSS,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(SMOKE_REPORT.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    boundary = json.loads(RUNTIME_BOUNDARY.read_text(encoding="utf-8"))

    assert report["stage"] == "8.14"
    assert report["status"] == "PASS"
    assert report["run_count"] == 1
    assert report["not_full_25_run_panel"] is True
    assert report["not_sota_claim"] is True
    assert ledger["FE_total"] == report["FE_total"]
    assert boundary["full_official_budget_deferred"] is True
    assert route["if_promising_next"] == "execute_full_25_run_formal_panel"
    assert route["if_not_promising_next"] == "failure_honest_cec2013_smoke_diagnosis"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.35 PASS`" in combined
    assert "Stage 8.14   CEC2013 single-run smoke and route decision" in combined
    assert "run_count = 1" in combined
    assert "not_full_25_run_panel = true" in combined
    assert "Stage 8.15" in combined
    assert "not a SOTA claim" in combined
    assert "not a final objective-value performance claim" in combined

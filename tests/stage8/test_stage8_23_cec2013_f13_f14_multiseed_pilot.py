import json
from pathlib import Path

import numpy as np


ROOT = Path("E:/llm_cc")
STAGE8_22_DIR = ROOT / "artifacts" / "selected" / "stage8_22"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_23"
CONFIG = ROOT / "configs" / "stage8_23_cec2013_f13_f14_multiseed_pilot.yaml"
PILOT_REPORT = OUTPUT_DIR / "multiseed_pilot_report.json"
TRACE = OUTPUT_DIR / "objective_trace.jsonl"
METHOD_SUMMARY = OUTPUT_DIR / "method_summary.json"
WIN_LOSS = OUTPUT_DIR / "win_loss_report.json"
POLICY_BRANCH = OUTPUT_DIR / "policy_branch_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_23_cec2013_f13_f14_multiseed_pilot.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_23_self_check_report.md"
README = ROOT / "README.md"


class FakeCECProblem:
    def __init__(self, function_id: int):
        self.function_id = function_id
        self._dimension = 24 if function_id == 13 else 18
        self._bounds = (-5.0, 5.0)

    def dimension(self) -> int:
        return self._dimension

    def bounds(self):
        return (
            np.full(self._dimension, self._bounds[0], dtype=float),
            np.full(self._dimension, self._bounds[1], dtype=float),
        )

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
        }

    def evaluate(self, vector) -> float:
        x = np.asarray(vector, dtype=float)
        target = -0.2 if self.function_id == 13 else -0.35
        return float(np.sum((x - target) ** 2))


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_stage8_23_runs_frozen_llm_policy_multiseed_pilot(tmp_path) -> None:
    from loco.coordination.cec2013_frozen_policy_multiseed_pilot import (
        run_stage8_23_cec2013_f13_f14_multiseed_pilot,
    )

    report = run_stage8_23_cec2013_f13_f14_multiseed_pilot(
        stage8_22_frozen_policy_path=STAGE8_22_DIR / "frozen_policy.json",
        stage8_22_frozen_policy_payload_path=STAGE8_22_DIR
        / "frozen_policy_payload.json",
        stage8_22_manifest_path=STAGE8_22_DIR / "frozen_policy_manifest.json",
        stage8_22_readiness_protocol_path=STAGE8_22_DIR
        / "cec2013_f13_f14_multiseed_readiness_protocol.json",
        stage8_22_fe_ledger_path=STAGE8_22_DIR / "fe_ledger.json",
        stage8_22_runtime_boundary_path=STAGE8_22_DIR / "runtime_boundary.json",
        stage8_22_next_route_path=STAGE8_22_DIR / "next_route_decision.json",
        output_dir=tmp_path,
        problem_loader=lambda function_id: FakeCECProblem(function_id),
        run_seeds=[0, 1, 2],
        max_fe_per_method_per_function=12,
    )

    assert report["stage"] == "8.23"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.22"
    assert report["benchmark_suite"] == "CEC2013_LSGO"
    assert report["selected_candidate_id"] == "stage8_20_round_candidate_8"
    assert report["frozen_policy_used"] is True
    assert report["selected_policy_revision_used"] is False
    assert report["run_count"] == 3
    assert report["seed_count"] == 3
    assert report["function_ids"] == ["F13", "F14"]
    assert report["method_count"] == 5
    assert report["method_names"] == [
        "identity_no_coord",
        "simple_consensus",
        "weighted_consensus",
        "best_reward_select",
        "stage8_22_frozen_llm_policy",
    ]
    assert report["trace_row_count"] == 360
    assert report["objective_loop_executed"] is True
    assert report["new_objective_evaluation_used"] is True
    assert report["official_cec2013_problem_loaded"] is True
    assert report["multiseed_pilot_executed"] is True
    assert report["not_full_25_run_panel"] is True
    assert report["not_full_f1_f15_panel"] is True
    assert report["baseline_comparison_made"] is True
    assert report["FE_total"] > 0
    assert report["FE_global_objective"] > 0
    assert report["recommended_next_stage"] in {"Stage 8.24", "Stage 8.23"}
    assert report["run_full_25_run_panel_next"] is False

    for flag in [
        "llm_call_used",
        "new_candidate_generation_used",
        "selected_policy_revision_used",
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

    trace_rows = _read_jsonl(tmp_path / "objective_trace.jsonl")
    method_summary = json.loads((tmp_path / "method_summary.json").read_text())
    win_loss = json.loads((tmp_path / "win_loss_report.json").read_text())
    branch = json.loads((tmp_path / "policy_branch_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert len(trace_rows) == 360
    assert sorted({row["function_id"] for row in trace_rows}) == ["F13", "F14"]
    assert sorted({row["seed"] for row in trace_rows}) == [0, 1, 2]
    assert "stage8_22_frozen_llm_policy" in method_summary["methods"]
    assert win_loss["comparison_case_count"] == 6
    assert "frozen_policy_vs_best_reward_select" in win_loss
    assert "frozen_policy_vs_best_baseline" in win_loss
    assert branch["policy_trace_row_count"] == 72
    assert branch["branch_counts"]["trust_best_reward"] >= 1
    assert ledger["FE_total"] == report["FE_total"]
    assert ledger["run_count"] == 3
    assert ledger["max_fe_per_method_per_function"] == 12
    assert boundary["not_full_25_run_panel"] is True
    assert route["run_full_25_run_panel_next"] is False


def test_stage8_23_committed_artifacts_docs_and_readme_record_multiseed_pilot() -> None:
    required = [
        CONFIG,
        PILOT_REPORT,
        TRACE,
        METHOD_SUMMARY,
        WIN_LOSS,
        POLICY_BRANCH,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(PILOT_REPORT.read_text(encoding="utf-8"))
    win_loss = json.loads(WIN_LOSS.read_text(encoding="utf-8"))
    branch = json.loads(POLICY_BRANCH.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))
    trace_rows = _read_jsonl(TRACE)

    assert report["stage"] == "8.23"
    assert report["status"] == "PASS"
    assert report["selected_candidate_id"] == "stage8_20_round_candidate_8"
    assert report["frozen_policy_used"] is True
    assert report["run_count"] >= 3
    assert report["not_full_25_run_panel"] is True
    assert win_loss["comparison_case_count"] == report["comparison_case_count"]
    assert branch["policy_trace_row_count"] > 0
    assert ledger["FE_total"] == report["FE_total"]
    assert len(trace_rows) == report["trace_row_count"]
    assert route["next_stage"] in {"Stage 8.24", "Stage 8.23"}

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.28 PASS`" in combined
    assert "Stage 8.23   CEC2013 F13/F14 multiseed pilot" in combined
    assert "stage8_20_round_candidate_8" in combined
    assert "FROZEN_FOR_CEC2013_F13_F14_MULTISEED_NOT_FINAL" in combined
    assert "not a SOTA claim" in combined
    assert "not a final objective-value performance claim" in combined

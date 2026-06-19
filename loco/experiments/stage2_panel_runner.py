"""Stage 2.1 multi-setting conflict evidence panel.

This module extends the Stage 2.0 smoke runner into a deterministic evidence
panel. It still does not implement an optimizer, LLM search, evolution, or new
coordination operators.
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from loco.benchmarks.synthetic_overlap_generator import (
    SyntheticOverlapProblem,
    generate_synthetic_overlap,
)
from loco.experiments.stage2_minimal_runner import _git_commit_hash, _run_problem


DEFAULT_OPERATORS = (
    "NoCoordination",
    "AverageConsensus",
    "BestRewardSelection",
    "WeightedConsensus",
    "ConflictDampening",
)


@dataclass(frozen=True)
class Stage21Setting:
    topology: str
    dimension: int
    overlap_ratio: float
    seeds: list[int]
    num_groups: int = 8
    base_group_size: int | None = None
    allow_variable_overlap_degree: bool = False
    max_overlap_degree: int = 2


@dataclass(frozen=True)
class Stage21PanelConfig:
    settings: list[Stage21Setting] = field(default_factory=list)
    output_json: Path | str = Path("docs/stage2/stage2_1_synthetic_panel_result.json")
    output_csv: Path | str = Path("docs/stage2/stage2_1_synthetic_panel_summary.csv")
    output_report: Path | str = Path("docs/stage2/stage2_1_self_check_report.md")
    max_fe: int = 10_000

    def normalized_settings(self) -> list[Stage21Setting]:
        if self.settings:
            return list(self.settings)
        return [
            Stage21Setting(
                topology=topology,
                dimension=dimension,
                overlap_ratio=ratio,
                seeds=[0, 1, 2],
            )
            for topology in ("line", "ring", "random_graph")
            for dimension in (100, 500, 1000)
            for ratio in (0.0, 0.05, 0.10, 0.20, 0.30)
        ]


def _write_text_lf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(text)


def _base_group_size(setting: Stage21Setting) -> int:
    if setting.base_group_size is not None:
        return setting.base_group_size
    return max(1, setting.dimension // max(setting.num_groups, 1))


def _make_panel_problem(
    setting: Stage21Setting, seed: int, setting_id: str
) -> SyntheticOverlapProblem:
    structure = generate_synthetic_overlap(
        dimension=setting.dimension,
        num_groups=setting.num_groups,
        base_group_size=_base_group_size(setting),
        overlap_ratio=setting.overlap_ratio,
        topology=setting.topology,
        seed=seed,
        allow_variable_overlap_degree=setting.allow_variable_overlap_degree,
        max_overlap_degree=setting.max_overlap_degree,
    )
    name = f"stage2_1_{setting_id}_seed_{seed}"
    return SyntheticOverlapProblem(structure, name=name)


def _operator_diagnostics(
    run_result: dict[str, Any], operator_name: str
) -> dict[str, float | bool]:
    operator_result = run_result["operators"][operator_name]
    before = float(operator_result["mean_conflict_before"])
    after = float(operator_result["mean_conflict_after"])
    number_of_shared = int(
        run_result["aggregate_conflict_metrics"]["number_of_shared_variables"]
    )
    low_overlap_case = bool(run_result["low_overlap_case"])

    if before <= 1e-12:
        conflict_persistence = 0.0
    else:
        conflict_persistence = max(0.0, after / before)

    # Stage 2.1 does not run a longitudinal optimizer. This diagnostic is the
    # regenerated conflict proxy after one deterministic post-coordination probe.
    post_coordination_regenerated_conflict = after

    coordination_values = [
        float(item["coordinated_value"])
        for item in operator_result["coordination_results"].values()
    ]
    if len(coordination_values) <= 1:
        consensus_instability = 0.0
    else:
        consensus_instability = float(np.std(coordination_values))

    per_variable = run_result["aggregate_conflict_metrics"]["per_variable"]
    if not per_variable:
        reward_proposal_inconsistency = 0.0
    else:
        reward_proposal_inconsistency = float(
            mean(
                abs(
                    float(metrics["reward_disagreement"])
                    - float(metrics["value_disagreement"])
                )
                for metrics in per_variable.values()
            )
        )

    no_coordination_objective = float(
        run_result["operators"]["NoCoordination"]["final_objective"]
    )
    objective_delta = (
        float(operator_result["final_objective"]) - no_coordination_objective
    )
    regression_tolerance = max(1e-9, abs(no_coordination_objective) * 0.05)
    low_overlap_regression_flag = bool(
        low_overlap_case
        and number_of_shared > 0
        and objective_delta > regression_tolerance
        and operator_name != "NoCoordination"
    )

    return {
        "post_coordination_regenerated_conflict": post_coordination_regenerated_conflict,
        "conflict_persistence": conflict_persistence,
        "consensus_instability": consensus_instability,
        "reward_proposal_inconsistency": reward_proposal_inconsistency,
        "low_overlap_regression_flag": low_overlap_regression_flag,
    }


def _annotate_run(
    setting: Stage21Setting, setting_id: str, seed: int, run: dict[str, Any]
) -> dict[str, Any]:
    low_overlap_case = setting.overlap_ratio <= 0.05
    run["stage"] = "2.1"
    run["setting"] = {
        "setting_id": setting_id,
        "topology": setting.topology,
        "dimension": setting.dimension,
        "num_groups": setting.num_groups,
        "base_group_size": _base_group_size(setting),
        "overlap_ratio_target": setting.overlap_ratio,
        "seed": seed,
    }
    run["low_overlap_case"] = low_overlap_case
    for operator_name in run["operators"]:
        run["operators"][operator_name].update(
            _operator_diagnostics(run, operator_name)
        )
    return run


def _compact_run(run: dict[str, Any]) -> dict[str, Any]:
    aggregate = dict(run["aggregate_conflict_metrics"])
    aggregate.pop("per_variable", None)
    compact_operators = {}
    for operator_name, operator_result in run["operators"].items():
        compact_operators[operator_name] = {
            "final_objective": operator_result["final_objective"],
            "final_error": operator_result["final_error"],
            "FE_total": operator_result["FE_total"],
            "FE_coordination_extra": operator_result["FE_coordination_extra"],
            "FE_commit_evaluation": operator_result["FE_commit_evaluation"],
            "FE_analysis_only": operator_result["FE_analysis_only"],
            "budget_scope": operator_result["budget_scope"],
            "cross_baseline_evaluations_shared": operator_result[
                "cross_baseline_evaluations_shared"
            ],
            "fe_accounting": operator_result["fe_accounting"],
            "mean_conflict_before": operator_result["mean_conflict_before"],
            "mean_conflict_after": operator_result["mean_conflict_after"],
            "proposal_consensus_collapse_ratio": operator_result[
                "proposal_consensus_collapse_ratio"
            ],
            "post_coordination_regenerated_conflict": operator_result[
                "post_coordination_regenerated_conflict"
            ],
            "conflict_persistence": operator_result["conflict_persistence"],
            "consensus_instability": operator_result["consensus_instability"],
            "reward_proposal_inconsistency": operator_result[
                "reward_proposal_inconsistency"
            ],
            "low_overlap_regression_flag": operator_result[
                "low_overlap_regression_flag"
            ],
            "metric_honesty_note": operator_result["metric_honesty_note"],
        }
    return {
        "stage": run["stage"],
        "seed": run["seed"],
        "git_commit": run["git_commit"],
        "setting": run["setting"],
        "low_overlap_case": run["low_overlap_case"],
        "benchmark": run["benchmark"],
        "initial_objective": run["initial_objective"],
        "aggregate_conflict_metrics": aggregate,
        "operators": compact_operators,
    }


def _summary_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for run in result["runs"]:
        setting = run["setting"]
        for operator_name, operator_result in run["operators"].items():
            rows.append(
                {
                    "setting_id": setting["setting_id"],
                    "topology": setting["topology"],
                    "dimension": setting["dimension"],
                    "overlap_ratio": run["benchmark"]["overlap_ratio"],
                    "overlap_ratio_target": setting["overlap_ratio_target"],
                    "seed": setting["seed"],
                    "operator": operator_name,
                    "mean_conflict_before": operator_result["mean_conflict_before"],
                    "mean_conflict_after": operator_result["mean_conflict_after"],
                    "proposal_consensus_collapse_ratio": operator_result[
                        "proposal_consensus_collapse_ratio"
                    ],
                    "post_coordination_regenerated_conflict": operator_result[
                        "post_coordination_regenerated_conflict"
                    ],
                    "conflict_persistence": operator_result["conflict_persistence"],
                    "consensus_instability": operator_result["consensus_instability"],
                    "reward_proposal_inconsistency": operator_result[
                        "reward_proposal_inconsistency"
                    ],
                    "final_objective": operator_result["final_objective"],
                    "FE_total": operator_result["FE_total"],
                    "FE_commit_evaluation": operator_result["FE_commit_evaluation"],
                    "FE_analysis_only": operator_result["FE_analysis_only"],
                    "FE_coordination_extra": operator_result["FE_coordination_extra"],
                    "low_overlap_case": run["low_overlap_case"],
                    "low_overlap_regression_flag": operator_result[
                        "low_overlap_regression_flag"
                    ],
                }
            )
    return rows


def _write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _aggregate_operator_summary(
    rows: list[dict[str, Any]]
) -> dict[str, dict[str, float]]:
    summary = {}
    for operator_name in DEFAULT_OPERATORS:
        operator_rows = [row for row in rows if row["operator"] == operator_name]
        if not operator_rows:
            continue
        summary[operator_name] = {
            "mean_proposal_consensus_collapse_ratio": float(
                mean(
                    float(row["proposal_consensus_collapse_ratio"])
                    for row in operator_rows
                )
            ),
            "mean_post_coordination_regenerated_conflict": float(
                mean(
                    float(row["post_coordination_regenerated_conflict"])
                    for row in operator_rows
                )
            ),
            "mean_conflict_persistence": float(
                mean(float(row["conflict_persistence"]) for row in operator_rows)
            ),
            "low_overlap_regression_count": int(
                sum(
                    str(row["low_overlap_regression_flag"]).lower() == "true"
                    for row in operator_rows
                )
            ),
        }
    return summary


def _render_report(result: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    operator_summary = result["operator_summary"]
    lines = [
        "# Stage 2.1 Multi-setting Conflict Evidence Gate",
        "",
        "生成日期：2026-06-20",
        "执行者：Codex",
        "",
        "## 边界",
        "",
        "No LLM / no evolution / no optimizer。Stage 2.1 只扩展 synthetic multi-setting evidence panel，不生成 coordination operator，不修改 BaseOpt，不实现 scheduler/controller。",
        "",
        "## 指标诚实性",
        "",
        "`proposal_consensus_collapse_ratio` 仍然只是当前 proposal set 的 consensus collapse 诊断，不是 longitudinal conflict reduction。`post_coordination_regenerated_conflict` 是 Stage 2.1 的 deterministic regenerated-conflict proxy，用于 evidence gate，不是 SOTA claim。",
        "",
        "## Panel 摘要",
        "",
        f"- settings: {result['panel']['setting_count']}",
        f"- runs: {result['panel']['run_count']}",
        f"- operators: {result['panel']['operator_count']}",
        f"- summary rows: {len(rows)}",
        "",
        "| Operator | Mean proposal collapse | Mean regenerated conflict | Mean persistence | Low-overlap regressions |",
        "|---|---:|---:|---:|---:|",
    ]
    for operator_name in DEFAULT_OPERATORS:
        summary = operator_summary.get(operator_name)
        if not summary:
            continue
        lines.append(
            "| {name} | {collapse:.6f} | {regen:.6f} | {persistence:.6f} | {regressions} |".format(
                name=operator_name,
                collapse=summary["mean_proposal_consensus_collapse_ratio"],
                regen=summary["mean_post_coordination_regenerated_conflict"],
                persistence=summary["mean_conflict_persistence"],
                regressions=summary["low_overlap_regression_count"],
            )
        )
    lines.extend(
        [
            "",
            "## 通过标准",
            "",
            "- JSON/CSV/report 三类产物可生成，且使用 LF line endings。",
            "- 所有 baseline 作为独立 method run 汇报 FE，不共享 cross-baseline evaluations。",
            "- no-overlap / low-overlap case 必须显式标记，不能被伪装成 conflict-resolution 成功。",
            "- 该阶段仍不进入 LLM/evolution/operator discovery。",
            "",
        ]
    )
    return "\n".join(lines)


def run_stage2_1_panel(config: Stage21PanelConfig | None = None) -> dict[str, Any]:
    config = config or Stage21PanelConfig()
    runs = []
    settings = config.normalized_settings()
    for setting_index, setting in enumerate(settings):
        setting_id = f"s{setting_index:03d}_{setting.topology}_d{setting.dimension}_o{setting.overlap_ratio:g}"
        for seed in setting.seeds:
            problem = _make_panel_problem(setting, seed, setting_id)
            run = _run_problem(problem=problem, seed=seed, max_fe=config.max_fe)
            runs.append(_compact_run(_annotate_run(setting, setting_id, seed, run)))

    result = {
        "stage": "2.1",
        "git_commit": _git_commit_hash(),
        "boundary": {
            "llm_used": False,
            "evolution_used": False,
            "optimizer_implemented": False,
            "base_optimizer_modified": False,
            "metric_claim": "evidence_gate_not_sota_claim",
        },
        "panel": {
            "setting_count": len(settings),
            "run_count": len(runs),
            "operator_count": len(DEFAULT_OPERATORS),
        },
        "runs": runs,
    }
    rows = _summary_rows(result)
    result["operator_summary"] = _aggregate_operator_summary(rows)

    output_json = Path(config.output_json)
    output_csv = Path(config.output_csv)
    output_report = Path(config.output_report)
    _write_text_lf(output_json, json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary_csv(output_csv, rows)
    _write_text_lf(output_report, _render_report(result, rows))
    return result


def main() -> int:
    result = run_stage2_1_panel()
    print(json.dumps(result["panel"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

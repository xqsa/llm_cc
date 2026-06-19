"""Stage 2.1B multi-round regenerated-conflict evidence runner."""

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

from loco.benchmarks.synthetic_overlap_generator import SyntheticOverlapProblem
from loco.conflict.conflict_metrics import aggregate_conflict_metrics
from loco.conflict.longitudinal_metrics import (
    conflict_oscillation,
    conflict_persistence_over_rounds,
    consensus_instability_over_rounds,
    longitudinal_conflict_reduction_ratio,
    objective_improvement_per_fe,
)
from loco.coordination.baselines import NoCoordination, default_baseline_operators
from loco.evaluation.fe_accounting import FEBudgetTracker
from loco.experiments.stage2_minimal_runner import (
    _build_group_proposals,
    _collapsed_after_batch,
    _git_commit_hash,
    _initial_solution,
    _json_ready,
    _make_conflict_batch,
)
from loco.experiments.stage2_panel_runner import (
    DEFAULT_OPERATORS,
    Stage21Setting,
    _base_group_size,
    _make_panel_problem,
)


@dataclass(frozen=True)
class Stage21BSetting:
    topology: str
    dimension: int
    overlap_ratio: float
    seeds: list[int]
    num_groups: int = 8
    base_group_size: int | None = None
    allow_variable_overlap_degree: bool = False
    max_overlap_degree: int = 2

    def as_stage21_setting(self) -> Stage21Setting:
        return Stage21Setting(
            topology=self.topology,
            dimension=self.dimension,
            overlap_ratio=self.overlap_ratio,
            seeds=list(self.seeds),
            num_groups=self.num_groups,
            base_group_size=self.base_group_size,
            allow_variable_overlap_degree=self.allow_variable_overlap_degree,
            max_overlap_degree=self.max_overlap_degree,
        )


@dataclass(frozen=True)
class Stage21BConfig:
    settings: list[Stage21BSetting] = field(default_factory=list)
    rounds: int = 5
    output_json: Path | str = Path("docs/stage2/stage2_1b_multiround_result.json")
    output_csv: Path | str = Path("docs/stage2/stage2_1b_multiround_summary.csv")
    output_report: Path | str = Path("docs/stage2/stage2_1b_self_check_report.md")
    max_fe: int = 100_000

    def __post_init__(self) -> None:
        if self.rounds < 5:
            raise ValueError("Stage 2.1B requires rounds >= 5.")

    def normalized_settings(self) -> list[Stage21BSetting]:
        if self.settings:
            return list(self.settings)
        return [
            Stage21BSetting(
                topology=topology,
                dimension=dimension,
                overlap_ratio=ratio,
                seeds=[0, 1, 2],
            )
            for topology in ("line", "ring", "random_graph")
            for dimension in (100, 500, 1000)
            for ratio in (0.05, 0.10, 0.20, 0.30)
        ]


def _write_text_lf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        output_file.write(text)


def _proposal_round(
    problem: SyntheticOverlapProblem,
    current: np.ndarray,
    tracker: FEBudgetTracker,
) -> tuple[Any, dict[str, Any], list[dict[str, Any]], float]:
    objective = problem.evaluate(current)
    tracker.record("proposal", 1)
    grouped_proposals, proposal_log = _build_group_proposals(
        problem=problem,
        current=current,
        baseline_objective=objective,
        tracker=tracker,
    )
    conflict_batch = _make_conflict_batch(problem, current, grouped_proposals)
    metrics = aggregate_conflict_metrics(
        conflict_batch,
        overlap_ratio=float(problem.metadata().get("overlap_ratio", 0.0)),
    )
    return conflict_batch, metrics, proposal_log, objective


def _apply_operator(
    operator: Any,
    current: np.ndarray,
    conflict_batch: Any,
    shared_variables: set[int],
) -> tuple[np.ndarray, dict[int, float], list[int], int]:
    coordinated = current.copy()
    consensus_values: dict[int, float] = {}
    changed_variables = []
    extra_fe = 0
    for state in conflict_batch:
        result = operator.coordinate(state)
        if result.variable_id not in shared_variables:
            raise RuntimeError(
                "Coordination attempted to change a non-shared variable."
            )
        coordinated[result.variable_id] = result.coordinated_value
        consensus_values[result.variable_id] = result.coordinated_value
        changed_variables.append(result.variable_id)
        extra_fe += result.extra_fe
    return coordinated, consensus_values, sorted(changed_variables), extra_fe


def _same_round_after_conflict(
    operator: Any,
    before_batch: Any,
    before_intensity: float,
    consensus_values: dict[int, float],
    overlap_ratio: float,
) -> float:
    if not before_batch.states or isinstance(operator, NoCoordination):
        return before_intensity
    after_batch = _collapsed_after_batch(
        before_batch,
        coordinated_values=consensus_values,
        collapse_rewards=True,
    )
    return float(
        aggregate_conflict_metrics(after_batch, overlap_ratio=overlap_ratio)[
            "mean_conflict_intensity"
        ]
    )


def _run_operator_multiround(
    problem: SyntheticOverlapProblem,
    setting_id: str,
    setting: Stage21BSetting,
    seed: int,
    operator: Any,
    rounds: int,
    max_fe: int,
) -> dict[str, Any]:
    tracker = FEBudgetTracker(max_fe=max_fe)
    current = _initial_solution(problem, seed)
    shared_variables = problem.shared_variables()
    lower, upper = problem.bounds()
    round_log = []
    conflict_before_series = []
    regenerated_conflict_series = []
    same_round_after_series = []
    objective_values = []
    fe_totals = []
    consensus_history_by_variable: dict[int, list[float]] = {
        variable_id: [] for variable_id in sorted(shared_variables)
    }

    for round_index in range(1, rounds + 1):
        before_batch, before_metrics, _, objective_before = _proposal_round(
            problem, current, tracker
        )
        before_intensity = float(before_metrics["mean_conflict_intensity"])
        coordinated, consensus_values, changed_variables, extra_fe = _apply_operator(
            operator, current, before_batch, shared_variables
        )
        if extra_fe:
            tracker.record("coordination_extra", extra_fe)

        committed_objective = problem.evaluate(coordinated)
        tracker.record("proposal", 1)
        same_round_after = _same_round_after_conflict(
            operator=operator,
            before_batch=before_batch,
            before_intensity=before_intensity,
            consensus_values=consensus_values,
            overlap_ratio=float(problem.metadata().get("overlap_ratio", 0.0)),
        )
        next_batch, next_metrics, _, _ = _proposal_round(problem, coordinated, tracker)
        regenerated_conflict = float(next_metrics["mean_conflict_intensity"])

        for variable_id, value in consensus_values.items():
            consensus_history_by_variable.setdefault(variable_id, []).append(value)

        conflict_before_series.append(before_intensity)
        same_round_after_series.append(same_round_after)
        regenerated_conflict_series.append(regenerated_conflict)
        objective_values.append(committed_objective)
        fe_totals.append(tracker.fe_total)
        round_log.append(
            {
                "round": round_index,
                "objective_before": objective_before,
                "committed_objective": committed_objective,
                "conflict_before": before_intensity,
                "same_round_conflict_after": same_round_after,
                "regenerated_conflict_next": regenerated_conflict,
                "proposal_consensus_collapse_ratio": (
                    0.0
                    if before_intensity <= 1e-12
                    else max(
                        0.0, (before_intensity - same_round_after) / before_intensity
                    )
                ),
                "FE_total": tracker.fe_total,
                "FE_commit_evaluation": round_index,
                "FE_analysis_only": 0,
                "shared_variables": sorted(shared_variables),
                "changed_variables": changed_variables,
            }
        )
        current = np.clip(coordinated, lower, upper)

    run = {
        "stage": "2.1B",
        "setting_id": setting_id,
        "setting": {
            "topology": setting.topology,
            "dimension": setting.dimension,
            "num_groups": setting.num_groups,
            "base_group_size": _base_group_size(setting.as_stage21_setting()),
            "overlap_ratio_target": setting.overlap_ratio,
        },
        "benchmark": {
            "name": problem.metadata().get("name"),
            "source": problem.metadata().get("source"),
            "dimension": problem.dimension(),
            "number_of_shared_variables": len(shared_variables),
            "overlap_ratio": float(problem.metadata().get("overlap_ratio", 0.0)),
        },
        "seed": seed,
        "operator": operator.name,
        "rounds": rounds,
        "round_log": round_log,
        "FE_total": tracker.fe_total,
        "FE_commit_evaluation": rounds,
        "FE_analysis_only": 0,
        "FE_coordination_extra": tracker.fe_coordination_extra,
        "fe_accounting": tracker.to_dict(),
        "cross_baseline_evaluations_shared": False,
        "proposal_consensus_collapse_ratio_mean": float(
            mean(row["proposal_consensus_collapse_ratio"] for row in round_log)
        ),
        "proposal_metric_source": "same_round_proposal_collapse",
        "longitudinal_conflict_reduction_ratio": longitudinal_conflict_reduction_ratio(
            conflict_before_series,
            regenerated_conflict_series,
        ),
        "longitudinal_metric_source": "next_round_regenerated_conflict",
        "mean_conflict_before": float(mean(conflict_before_series)),
        "mean_regenerated_conflict_next": float(mean(regenerated_conflict_series)),
        "conflict_oscillation": conflict_oscillation(regenerated_conflict_series),
        "conflict_persistence_over_rounds": conflict_persistence_over_rounds(
            conflict_before_series,
            regenerated_conflict_series,
        ),
        "consensus_instability_over_rounds": consensus_instability_over_rounds(
            consensus_history_by_variable
        ),
        "objective_improvement_per_fe": objective_improvement_per_fe(
            objective_values,
            fe_totals,
        ),
        "metric_honesty_note": (
            "longitudinal_conflict_reduction_ratio uses next-round regenerated conflict; "
            "proposal_consensus_collapse_ratio_mean remains a one-shot same-round metric."
        ),
    }
    return _json_ready(run)


def _summary_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for run in result["runs"]:
        rows.append(
            {
                "setting_id": run["setting_id"],
                "topology": run["setting"]["topology"],
                "dimension": run["setting"]["dimension"],
                "overlap_ratio": run["benchmark"]["overlap_ratio"],
                "overlap_ratio_target": run["setting"]["overlap_ratio_target"],
                "seed": run["seed"],
                "operator": run["operator"],
                "rounds": run["rounds"],
                "longitudinal_conflict_reduction_ratio": run[
                    "longitudinal_conflict_reduction_ratio"
                ],
                "mean_conflict_before": run["mean_conflict_before"],
                "mean_regenerated_conflict_next": run["mean_regenerated_conflict_next"],
                "proposal_consensus_collapse_ratio_mean": run[
                    "proposal_consensus_collapse_ratio_mean"
                ],
                "conflict_oscillation": run["conflict_oscillation"],
                "conflict_persistence_over_rounds": run[
                    "conflict_persistence_over_rounds"
                ],
                "consensus_instability_over_rounds": run[
                    "consensus_instability_over_rounds"
                ],
                "objective_improvement_per_fe": run["objective_improvement_per_fe"],
                "FE_total": run["FE_total"],
                "FE_commit_evaluation": run["FE_commit_evaluation"],
                "FE_analysis_only": run["FE_analysis_only"],
                "FE_coordination_extra": run["FE_coordination_extra"],
                "cross_baseline_evaluations_shared": run[
                    "cross_baseline_evaluations_shared"
                ],
            }
        )
    return rows


def _write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=list(rows[0].keys()) if rows else [],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _operator_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    summary = {}
    for operator_name in DEFAULT_OPERATORS:
        operator_rows = [row for row in rows if row["operator"] == operator_name]
        if not operator_rows:
            continue
        summary[operator_name] = {
            "mean_longitudinal_conflict_reduction_ratio": float(
                mean(
                    float(row["longitudinal_conflict_reduction_ratio"])
                    for row in operator_rows
                )
            ),
            "mean_proposal_consensus_collapse_ratio": float(
                mean(
                    float(row["proposal_consensus_collapse_ratio_mean"])
                    for row in operator_rows
                )
            ),
            "mean_conflict_persistence_over_rounds": float(
                mean(
                    float(row["conflict_persistence_over_rounds"])
                    for row in operator_rows
                )
            ),
            "mean_objective_improvement_per_fe": float(
                mean(
                    float(row["objective_improvement_per_fe"]) for row in operator_rows
                )
            ),
        }
    return summary


def _render_report(result: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Stage 2.1B Multi-round Post-Coordination Regenerated Conflict Evidence",
        "",
        "生成日期：2026-06-20",
        "执行者：Codex",
        "",
        "## 边界",
        "",
        "No LLM / no evolution / no optimizer。Stage 2.1B 只做固定轮数 deterministic evidence gate，不生成 coordination operator，不修改 BaseOpt，不修改 benchmark objective，不修改 MetaBox source。",
        "",
        "## 指标诚实性",
        "",
        "`proposal_consensus_collapse_ratio_mean` 仍是 same-round proposal-set collapse。`longitudinal_conflict_reduction_ratio` 使用下一轮 regenerated conflict，不是 same-round conflict-after，也不是 optimizer-loop performance claim。",
        "",
        "## Panel 摘要",
        "",
        f"- settings: {result['panel']['setting_count']}",
        f"- runs: {result['panel']['run_count']}",
        f"- rounds per run: {result['rounds']}",
        f"- summary rows: {len(rows)}",
        "",
        "| Operator | Mean longitudinal reduction | Mean proposal collapse | Mean persistence | Mean objective improvement / FE |",
        "|---|---:|---:|---:|---:|",
    ]
    for operator_name in DEFAULT_OPERATORS:
        summary = result["operator_summary"].get(operator_name)
        if not summary:
            continue
        lines.append(
            "| {name} | {longitudinal:.6f} | {collapse:.6f} | {persistence:.6f} | {improvement:.6f} |".format(
                name=operator_name,
                longitudinal=summary["mean_longitudinal_conflict_reduction_ratio"],
                collapse=summary["mean_proposal_consensus_collapse_ratio"],
                persistence=summary["mean_conflict_persistence_over_rounds"],
                improvement=summary["mean_objective_improvement_per_fe"],
            )
        )
    lines.extend(
        [
            "",
            "## 通过标准",
            "",
            "- 每个 baseline 独立运行，cross-baseline evaluations 不共享。",
            "- FE_total 等于 FE_grouping + FE_proposal + FE_coordination_extra + FE_repair。",
            "- coordination 只写 shared variables。",
            "- no LLM / no evolution / no optimizer / no MetaBox source mutation。",
            "",
        ]
    )
    return "\n".join(lines)


def run_stage2_1b_multiround(config: Stage21BConfig | None = None) -> dict[str, Any]:
    config = config or Stage21BConfig()
    settings = config.normalized_settings()
    runs = []
    for setting_index, setting in enumerate(settings):
        setting_id = f"m{setting_index:03d}_{setting.topology}_d{setting.dimension}_o{setting.overlap_ratio:g}"
        panel_setting = setting.as_stage21_setting()
        for seed in setting.seeds:
            for operator in default_baseline_operators():
                problem = _make_panel_problem(panel_setting, seed, setting_id)
                runs.append(
                    _run_operator_multiround(
                        problem=problem,
                        setting_id=setting_id,
                        setting=setting,
                        seed=seed,
                        operator=operator,
                        rounds=config.rounds,
                        max_fe=config.max_fe,
                    )
                )

    result = {
        "stage": "2.1B",
        "git_commit": _git_commit_hash(),
        "rounds": config.rounds,
        "boundary": {
            "llm_used": False,
            "evolution_used": False,
            "optimizer_implemented": False,
            "base_optimizer_modified": False,
            "benchmark_objective_modified": False,
            "metabox_source_modified": False,
            "f13_padding_used": False,
            "metric_claim": "multiround_evidence_not_sota_claim",
        },
        "panel": {
            "setting_count": len(settings),
            "run_count": len(runs),
            "operator_count": len(DEFAULT_OPERATORS),
        },
        "runs": runs,
    }
    rows = _summary_rows(result)
    result["operator_summary"] = _operator_summary(rows)

    output_json = Path(config.output_json)
    output_csv = Path(config.output_csv)
    output_report = Path(config.output_report)
    _write_text_lf(output_json, json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_summary_csv(output_csv, rows)
    _write_text_lf(output_report, _render_report(result, rows))
    return result


def main() -> int:
    result = run_stage2_1b_multiround()
    print(json.dumps(result["panel"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

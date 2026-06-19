"""Train/validation/test split generation for Stage 1 benchmark manifests."""

from __future__ import annotations

import json
from pathlib import Path

from .benchmark_manifest import BenchmarkManifest, BenchmarkManifestEntry


def _synthetic_name(
    split: str, dimension: int, ratio: float, topology: str, seed: int
) -> str:
    ratio_tag = f"{ratio:.2f}".replace(".", "p")
    return f"synthetic_{split}_d{dimension}_rho{ratio_tag}_{topology}_s{seed}"


def generate_default_manifest() -> BenchmarkManifest:
    """Generate the Stage 1 frozen split manifest deterministically."""

    entries: list[BenchmarkManifestEntry] = []

    for function_id, split in [(12, "train"), (13, "train"), (14, "test")]:
        entries.append(
            BenchmarkManifestEntry(
                name=f"cec2013lsgo_f{function_id}_{split}",
                source="metabox_cec2013lsgo",
                function_id=function_id,
                dimension=1000 if function_id == 12 else 905,
                topology="cec2013lsgo_overlap",
                overlap_ratio=0.0 if function_id == 12 else 95 / 905,
                split=split,
                seed=None,
                grouping_source="metabox_or_reconstructed",
            )
        )

    split_specs = [
        ("train", [500, 1000], [0.05, 0.10], ["line", "ring"], [0, 1]),
        ("val", [1000], [0.15], ["ring", "random_graph"], [2]),
        ("test", [2000, 5000], [0.20, 0.30], ["random_graph"], [3, 4]),
    ]
    for split, dimensions, ratios, topologies, seeds in split_specs:
        for dimension in dimensions:
            for ratio in ratios:
                for topology in topologies:
                    for seed in seeds:
                        entries.append(
                            BenchmarkManifestEntry(
                                name=_synthetic_name(
                                    split, dimension, ratio, topology, seed
                                ),
                                source="synthetic_overlap",
                                function_id=None,
                                dimension=dimension,
                                topology=topology,
                                overlap_ratio=ratio,
                                split=split,
                                seed=seed,
                                grouping_source="synthetic_overlap_generator",
                            )
                        )

    entries.sort(key=lambda entry: (entry.split, entry.source, entry.name))
    return BenchmarkManifest(
        name="stage1_loco_lsgo_benchmark_manifest", entries=entries
    )


def write_manifest(manifest: BenchmarkManifest, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def manifest_from_dict(data: dict) -> BenchmarkManifest:
    entries = [BenchmarkManifestEntry(**entry) for entry in data["entries"]]
    return BenchmarkManifest(
        name=data["name"],
        entries=entries,
        frozen=bool(data.get("frozen", True)),
        version=int(data.get("version", 1)),
    )

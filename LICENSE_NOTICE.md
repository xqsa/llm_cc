# License Notice

This repository is currently released for research use under an explicit license boundary until a final project license is selected.

## LOCO-LSGO Code

The code authored in this repository is intended to be open for academic research and reproducibility. A final SPDX license should be selected before publication or external reuse.

Until then, treat this repository as:

```text
Copyright (c) 2026 LOCO-LSGO contributors.
All rights reserved unless a file or dependency license states otherwise.
```

## Third-party Benchmark Boundary

This repository does not copy or rewrite CEC2013 LSGO objective implementations.

CEC2013 LSGO access is handled through dependency/adapter code:

- MetaBox / `metaevobox` is used as an optional external dependency.
- CEC2013 LSGO objective code remains in the external package or official wrapper.
- LOCO code only reconstructs metadata, grouping contracts, and adapter-facing benchmark information.

The project documents that MetaBox is BSD-3-Clause, while MetaBox documentation notes the CEC2013 LSGO implementation as GPL-3.0. Because of that, this repository avoids copying third-party benchmark source into LOCO.

## Synthetic Benchmarks

Synthetic overlap benchmark generation code in `loco/benchmarks/synthetic_overlap_generator.py` is original LOCO-controlled infrastructure and does not implement official CEC2013 LSGO objective functions.

## Before Public Release

Before claiming a formal open-source release, choose and add a root `LICENSE` file. Recommended options:

- MIT or BSD-3-Clause for LOCO-authored code if broad reuse is desired.
- A more restrictive academic-only license if commercial reuse should be limited.

Do not select a license that creates ambiguity with external CEC2013 LSGO implementation licensing.

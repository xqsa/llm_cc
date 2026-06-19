# Stage 1 Self-check Report

生成日期：2026-06-19  
执行者：Codex  
验证命令：`$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest -p no:cacheprovider tests/stage1 -q`  
验证结果：`15 passed in 0.28s`

## 1. 是否复用了 MetaBox-v2？

是，采用 dependency / adapter 设计。已下载并调研 MetaBox-v2 / `metaevobox==2.0.2`，代码通过 lazy import 调用 MetaBox CEC2013LSGO，而不是复制源码。当前环境中常规 `pip install metaevobox` 失败；`--no-deps --no-build-isolation` 本地安装成功，但 top-level import 仍受 optimizer/agent 依赖链影响。

## 2. 是否没有重写 CEC2013LSGO？

是。没有实现 F1-F15 objective，没有复制 CEC2013LSGO 源码。`loco/benchmarks/cec2013lsgo_metabox.py` 只提供 loader 和 metadata reconstruction。

## 3. 是否能加载 F12/F13/F14？

接口已实现：`load_cec2013lsgo_overlap_suite()` 固定加载 F12/F13/F14。当前本机真实 MetaBox import 仍失败于 top-level dependency chain，因此测试使用 fake MetaBox module 验证 loader contract；真实加载需要一个可正常 import `metaevobox.environment.problem.SOO.CEC2013LSGO` 的环境。

## 4. 是否所有 benchmark 都统一为 LSGOProblem interface？

是。MetaBox-backed problem 通过 `MetaBoxProblemAdapter` 包装为 `LSGOProblem`；synthetic overlap supplement 通过 `SyntheticOverlapProblem` 实现同一接口。

## 5. 是否输出 groups G？

是。`grouping()` 返回 `list[list[int]] | None`。对 F13/F14 这类暴露 `Pvector`、`s`、`overlap` 的 MetaBox problem，可重建 groups。

## 6. 是否输出 shared variables S？

是。`shared_variables()` 显式返回 `S = {i | m_i >= 2}`，由 `build_overlap_metadata()` 统一计算。

## 7. 是否输出 incidence matrix A？

是。`OverlapMetadata.incidence_matrix` 满足 `A[i, k] = 1 if i in G_k else 0`。

## 8. 是否支持 line/ring/random_graph synthetic overlap？

是。`generate_synthetic_overlap()` 支持 `line`、`ring`、`random_graph`。

## 9. 是否支持 train/val/test frozen split？

是。`generate_default_manifest()` 生成 deterministic manifest；当前冻结文件为 `configs/stage1_benchmark_manifest.json`。

## 10. 是否保证 seed reproducibility？

是。synthetic generator 使用 `np.random.default_rng(seed)`，测试覆盖同 seed 完全复现。

## 11. 是否没有实现 optimizer？

是。没有新增 optimizer、BaseOpt、DE/CMA-ES/PSO/SHADE/L-SHADE。

## 12. 是否没有实现 LLM？

是。没有 LLM API、prompting、operator generation 或 test-time LLM call。

## 13. 是否没有实现 evolution？

是。没有 evolution search、mutation/selection loop 或 operator search。

## 14. 是否没有实现 coordination operator？

是。没有实现 shared-variable coordination operator logic。当前只定义 benchmark metadata 与加载接口。

## 15. 是否记录了 MetaBox 和 CEC2013LSGO license？

是。MetaBox repo license 为 BSD-3-Clause；MetaBox CEC2013LSGO 源码文档标注官方 CEC2013LSGO implementation 为 GPL-3.0。因此 Stage 1 采用 dependency / adapter，不复制第三方源码。

## 16. 当前最大风险是什么？

最大风险是 `metaevobox` top-level import 副作用过重：benchmark-only import 会先触发 trainer/optimizer/agent 依赖链，当前环境因此无法直接真实加载 F12/F13/F14。Stage 2 前应使用隔离环境补齐 MetaBox 运行时依赖，或优先向 MetaBox 侧确认 benchmark-only import path。

## 17. Stage 2 可以直接依赖哪些接口？

Stage 2 可以直接依赖：

- `loco.benchmarks.problem_interface.LSGOProblem`
- `loco.benchmarks.benchmark_registry.BenchmarkRegistry`
- `loco.benchmarks.benchmark_registry.load_manifest`
- `loco.benchmarks.overlap_metadata.OverlapMetadata`
- `loco.benchmarks.overlap_metadata.build_overlap_metadata`
- `loco.benchmarks.cec2013lsgo_metabox.load_cec2013lsgo_problem`
- `loco.benchmarks.synthetic_overlap_generator.generate_synthetic_overlap`

Stage 2 不应直接 import MetaBox internal problem classes。


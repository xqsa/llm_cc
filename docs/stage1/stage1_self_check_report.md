# Stage 1 Self-check Report

生成日期：2026-06-19  
执行者：Codex  
验证命令：`python -m pytest -p no:cacheprovider tests -q -rs`
验证结果：见当前提交的本地验证记录；真实 MetaBox optional tests 在安装 `metaevobox` 的本机 benchmark-only 环境中为 PASS，在 CI 缺少 MetaBox 时应 clean skip。

## 1. 是否复用了 MetaBox-v2？

是，采用 dependency / adapter 设计。已下载并调研 MetaBox-v2 / `metaevobox==2.0.2`，代码通过 lazy import 调用 MetaBox CEC2013LSGO，而不是复制源码。当前环境中常规 `pip install metaevobox` 失败；`--no-deps --no-build-isolation` 本地安装成功，但 top-level import 仍受 optimizer/agent 依赖链影响。

## 2. 是否没有重写 CEC2013LSGO？

是。没有实现 F1-F15 objective，没有复制 CEC2013LSGO 源码。`loco/benchmarks/cec2013lsgo_metabox.py` 只提供 loader 和 metadata reconstruction。

## 3. 是否能加载 F12/F13/F14？

接口已实现：`load_cec2013lsgo_overlap_suite()` 固定加载 F12/F13/F14。LOCO 使用 benchmark-only lazy import adapter 直接加载 MetaBox CEC2013LSGO numpy module，避免触发 top-level trainer / optimizer / agent 依赖链。

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

## Stage 1.5 MetaBox Real Smoke Status

当前状态：`PASS_WITH_BENCHMARK_ONLY_IMPORT`

含义：

- LOCO adapter contract 与 Stage 1 tests 通过。
- 真实 MetaBox smoke 脚本：`scripts/stage1/check_metabox_cec2013lsgo_real.py`。
- optional pytest：`tests/stage1/test_metabox_real_optional.py`，真实 smoke 不可用时 clean skip，不使用 fake module 伪造成功。
- benchmark-only bypass import 可以加载已安装 MetaBox 的 CEC2013LSGO numpy module，不触发 `metaevobox.__init__`。
- 普通 direct import `metaevobox.environment.problem.SOO.CEC2013LSGO` 仍触发 trainer / optimizer / agent 依赖链；这不是 benchmark-only smoke 的 blocker。
- Stage 1.6 已修正 CEC2013 LSGO semantics：F13/F14 必须同时记录 `D_formula=905` 与 `D_api=1000`。
- F13/F14 使用 `Pvector/s/overlap` extractor，group count 为 20，overlap size 为 5，shared variables 数量为 95，overlap ratio 为 `95/905`。
- F12 不使用 F13/F14 的 `Pvector/s/overlap` grouping rule；当前 wrapper 未暴露对应 metadata 时，`grouping_status=unavailable` 是合法状态，不再视为 F13/F14 同类失败。
- F13 真实 evaluate 已通过显式 `implementation_api_adapter` 适配：保留 `D_formula=905`，使用 `runtime_dimension=1000` 对齐 MetaBox F13 implementation/API 的 1000-length `Ovector`。
- F14 是当前直接 `D_formula=905` 真实完整通过的 CEC2013 conflicting-overlap smoke case。

判定：

- `PASS_WITH_BENCHMARK_ONLY_IMPORT`：F12/F13/F14 均可通过 LOCO adapter load/evaluate；F13 的 runtime surface 显式标记为 `implementation_api_adapter`。
- 不是 full MetaBox top-level import PASS：普通 `metaevobox` import 仍可能被 trainer/agent 依赖链阻塞。
- 不是语义改写：F13/F14 的 official grouping、shared variables 与 overlap ratio 仍按 `D_formula=905` 报告。

## Stage 1.6 CEC2013 LSGO Semantics Correction Status

当前状态：`PASS`

已修正：

- 新增 `docs/stage1/cec2013lsgo_semantics.md`，记录 CEC2013 LSGO 15 functions 四类结构、F12/F13/F14 定义差异、`D_formula` 与 `D_api` 分离规则。
- 已吸收用户提供的官方语义优先资料，补充 CEC2013 LSGO 相比 CEC2010 的扩展点：nonuniform subcomponent sizes、subcomponent contribution imbalance、overlapping subcomponents、nonlinear transformations。
- 已补充官方 evaluation protocol：15 minimization problems、25 runs per function、`Max FE = 3 * 10^6`，并强调 LOCO 的 coordination / repair / probing 等额外 evaluations 必须计入 FE budget。
- F13/F14 metadata 固定记录 `D_formula=905` 与 `D_api=1000`，不把 F13/F14 改成普通 1000D 逻辑。
- F13/F14 使用 `Pvector/s/overlap` extractor，恢复 20 groups、overlap size 5、shared variables 95、overlap ratio `95/905`。
- F13 标记为 `conforming_overlap`；F14 标记为 `conflicting_overlap`。
- F12 不再要求 `Pvector/s/overlap`，不硬套 F13/F14 extractor；当前标记 `grouping_status=unavailable`、`grouping_source=unavailable`。
- 若未来实现 F12 analytical Rosenbrock-chain grouping，必须单独标记 `grouping_source=analytical_rosenbrock_chain`。
- 已固定 LOCO 使用角色：F14 是 primary real conflicting-overlap benchmark，F13 是 conforming-overlap sanity/stability benchmark，F12 是 Rosenbrock-chain special topology benchmark。

剩余风险：

- F13 的 adapter 改变的是 LOCO 对 MetaBox implementation/API 的 runtime input surface：`problem.dimension()` 返回 1000，但 metadata 中继续保留 `D_formula=905`、`D_api=1000`、`adapter_mode=implementation_api_adapter`。
- F13 incidence matrix 在 adapter runtime surface 下为 `1000 x 20`；shared-variable count 与 overlap ratio 仍按 official formula variables 报告为 `95` 与 `95/905`。
- 不允许把该适配描述成 objective rewrite、benchmark copy 或普通 1000D semantics；它只是 MetaBox runtime compatibility layer。

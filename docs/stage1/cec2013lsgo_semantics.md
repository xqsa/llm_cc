# Stage 1.6: CEC2013 LSGO Semantics Correction

生成日期：2026-06-19
执行者：Codex
任务边界：只修正 CEC2013 LSGO benchmark semantics、metadata extractor 与测试；不实现 optimizer、benchmark objective、coordination operator 或 LLM/evolution。

## 1. 依据来源

本文件依据以下来源锁定语义：

- CEC2013 LSGO official technical report：X. Li, K. Tang, M. N. Omidvar, Z. Yang, K. Qin, "Benchmark Functions for the CEC'2013 Special Session and Competition on Large Scale Global Optimization," Technical Report, RMIT University, 2013。镜像 URL `https://al-roomi.org/multimedia/CEC_Database/CEC2013/LargeScaleGlobalOptimization/CEC2013_LargeScaleGO_TechnicalReport.pdf` 当前 HEAD 返回 200。
- CEC competition page URL：`http://goanna.cs.rmit.edu.au/~xiaodong/cec13-lsgo/competition/`。当前本机访问返回 `502 Bad Gateway`，因此本阶段仅记录其作为 official report / wrapper README 引用的官方页面，不把它当作本次已直接读取成功的网页。
- `dmolina/cec2013lsgo` public wrapper README：该 wrapper 说明它是 CEC2013 LSGO C++ implementation 的 Python wrapper，引用上述 technical report 与 competition page，并说明 `Benchmark.get_info(function_id)` 为了兼容 CEC20xx interface，返回的 `dimension` 始终为 `1000`。
- `dmolina/cec2013lsgo` public C++ wrapper：F13/F14 implementation 中均设置 `dimension = 905`，`overlap = 5`，这与 `D_formula` 语义一致。
- 当前安装的 MetaBox `metaevobox.environment.problem.SOO.CEC2013LSGO.cec2013lsgo_numpy`：用于确认 wrapper/API 层字段行为，包括 F12、F13、F14 class 暴露的 `dim`、`dimension`、`Pvector`、`s`、`overlap`。

LOCO 不复制 third-party source code，不重写 CEC2013 objective；本阶段只记录语义并修正 LOCO metadata contract。

## 2. 官方定位与设计动机

CEC2013 LSGO 指的是 CEC'2013 Special Session and Competition on Large-Scale Global Optimization，不是 CEC2013 niching / multimodal 测试集。

官方 technical report 提出 15 个 large-scale minimization benchmark problems，作为 CEC2010 LSGO benchmark 的扩展。它的目标不是只提供“大维度函数”，而是更明确地模拟 large-scale optimization 中的变量交互结构。

相比 CEC2010 LSGO，CEC2013 LSGO 特别加入或强化：

- nonuniform subcomponent sizes；
- imbalance in subcomponent contribution，通过 `w_i` 表达不同 subcomponents 的贡献不平衡；
- overlapping subcomponents；
- nonlinear transformations，包括 ill-conditioning、symmetry breaking 和 smooth irregularities。

这对 LOCO-LSGO 很关键：F13/F14 不是普通函数编号，而是官方专门用来测试 overlapping subcomponents 的 benchmark。F14 进一步引入 conflicting overlap，正好对应 shared-variable conflict coordination 的真实 benchmark 语义。

## 3. 15 Functions 的四类结构

CEC2013 LSGO 共 15 个 functions，technical report / MetaBox 文档将其分为四类：

| 类别 | Functions | 结构语义 |
|---|---:|---|
| Fully-separable functions | F1-F3 | 完全可分离 large-scale functions。 |
| Partially separable functions | F4-F11 | F4-F7 有若干 non-separable subcomponents，并保留一个 fully-separable subcomponent；F8-F11 只有 non-separable subcomponents，没有额外 separable subcomponent。 |
| Overlapping functions | F12-F14 | F12-F13 属于 conforming overlapping family，F14 属于 conflicting overlapping。 |
| Fully-nonseparable function | F15 | 完全不可分离 large-scale function。 |

对 LOCO-LSGO 来说，真正需要 shared-variable coordination metadata 的主要对象是具有显式 subcomponent overlap metadata 的 F13/F14。F12 虽属于 overlapping family，但不是 F13/F14 那种 `S/m/Pvector` 显式分组格式。

完整函数结构摘要：

| Functions | 官方基础函数与结构 | LOCO 用途 |
|---|---|---|
| F1-F3 | Shifted Elliptic、Shifted Rastrigin、Shifted Ackley；fully separable。 | 可作为 non-overlap / separable sanity reference，不是 LOCO 主场景。 |
| F4-F7 | 7 个 non-separable subcomponents + 1 个 separable subcomponent；基础函数为 Elliptic、Rastrigin、Ackley、Schwefel。 | 可作为 partially separable 对照。 |
| F8-F11 | 20 个 non-separable subcomponents，无 separable subcomponent；基础函数为 Elliptic、Rastrigin、Ackley、Schwefel。 | 适合作为 non-overlapping 20-subcomponent 对照。 |
| F12 | Shifted Rosenbrock；Rosenbrock-chain adjacent interaction。 | special topology benchmark；不要与 F13/F14 混成同一 grouping rule。 |
| F13 | Shifted Schwefel with Conforming Overlapping Subcomponents。 | conforming-overlap sanity / stability benchmark，测试 LOCO 是否过度干预。 |
| F14 | Shifted Schwefel with Conflicting Overlapping Subcomponents。 | primary real conflicting-overlap benchmark。 |
| F15 | Fully non-separable shifted Schwefel。 | 极端 fully non-separable reference，不是 LOCO shared-variable operator 主场景。 |

## 4. 官方符号体系

Stage 1.6 后，代码、文档和论文草稿应尽量保持以下符号一致：

| 符号 | 含义 |
|---|---|
| `D` | objective function dimension。LOCO metadata 中进一步拆成 `D_formula` 与 `D_api`。 |
| `S = {s_1, ..., s_K}` | subcomponent sizes 的 multiset / vector。 |
| `K = |S|` | subcomponents 数量。F13/F14 中 `K=20`。 |
| `C_i = sum_{j=1}^{i} s_j` | 前 `i` 个 subcomponents 的累积大小，`C_0=0`。 |
| `P` / `Pvector` | 变量索引 permutation。 |
| `w_i` | 第 `i` 个 non-separable subcomponent 的权重，用于制造贡献不平衡。 |
| `x^{opt}` | shifted optimum vector。 |
| `R_i` | subcomponent rotation matrix。 |
| `m` | overlapping subcomponents 之间的 overlap size。F13/F14 中 `m=5`。 |
| `T_osz`, `T_asy`, `Lambda_alpha` | 用于引入 smooth irregularities、symmetry breaking 和 ill-conditioning 的 nonlinear transformations。 |

注意：LOCO 自己的 shared variable set 也常记为 `S = {i | m_i >= 2}`。为避免和 CEC2013 的 subcomponent-size vector `S` 混淆，论文中建议写：

```text
CEC subcomponent sizes: S_CEC = {s_1, ..., s_K}
LOCO shared variable set: S_shared = {i | degree(i) >= 2}
```

## 5. F12/F13/F14 官方定义差异

| Function | 官方/实现名 | overlap semantics | LOCO grouping policy |
|---|---|---|---|
| F12 | Shifted Rosenbrock | Rosenbrock chain-style overlap / conforming overlapping family | 不使用 F13/F14 的 `Pvector/s/overlap` extractor；若 wrapper 未暴露可靠 metadata，则 `grouping_status=unavailable`。 |
| F13 | Shifted Schwefel with Conforming Overlapping Subcomponents | `conforming_overlap` | 使用 `Pvector/s/overlap` 恢复 20 个 overlapping groups。 |
| F14 | Shifted Schwefel with Conflicting Overlapping Subcomponents | `conflicting_overlap` | 使用 `Pvector/s/overlap` 恢复 20 个 overlapping groups。 |

F12 可以从 Rosenbrock chain 的数学形式推导 analytical chain grouping，例如相邻变量 pair `(x_i, x_{i+1})`。但如果后续实现这种 grouping，必须单独标记：

```text
grouping_source = analytical_rosenbrock_chain
```

在 Stage 1.6 当前实现中，F12 不伪造 grouping，默认：

```text
grouping_status = unavailable
grouping_source = unavailable
```

## 6. D_formula 与 D_api 必须分开

Stage 1.6 后，LOCO metadata 必须同时记录：

| 字段 | 含义 |
|---|---|
| `D_formula` | 按 benchmark mathematical formula / effective decision variables 计算出的维度。 |
| `D_api` | 某些 competition wrapper / API 为保持 CEC20xx interface 而暴露的接口维度。 |

对 F13/F14：

```text
K = 20
m = 5
sum_k |G_k| = 1000
D_formula = 1000 - (K - 1) * m = 1000 - 19 * 5 = 905
D_api = 1000  # 部分 competition wrappers / get_info interface 可能这样报告
```

因此：

```text
F13 D_formula = 905
F14 D_formula = 905
```

不允许把 F13/F14 简化成普通 `1000D` 逻辑；不允许把 905 维 padding 到 1000 后假装解决问题。若某个 official wrapper 或 dependency implementation 的 evaluate API 需要 1000D runtime input，必须显式标记：

```text
grouping_source 或 adapter_mode = implementation_api_adapter
```

并证明该 wrapper 的 evaluate API 确实要求 1000D input。该 adapter 只能作为 wrapper compatibility 层，不能改变 official formula semantics。

当前 MetaBox F13 使用该规则：LOCO metadata 保留 `D_formula=905` 与 `D_api=1000`，但 adapter runtime surface 使用 `runtime_dimension=1000`，原因是 MetaBox F13 implementation/API 内部暴露 1000-length `Ovector`、`Pvector` 和 `s` construction data。该行为标记为：

```text
adapter_mode = implementation_api_adapter
adapter_reason = metabox_f13_ovector_requires_D_api
```

## 7. F13/F14 Grouping Recovery 公式

F13/F14 暴露：

```text
Pvector: permutation vector
s = [s_1, ..., s_K]: subcomponent sizes, K = 20
m: overlap size, m = 5
```

令 cursor 初始为 0。第 `k` 个 group，按 0-based index 写作：

```text
start_k = cursor - k * m
end_k = cursor + s_k - k * m
G_k = Pvector[start_k : end_k]
cursor = cursor + s_k
```

其中：

```text
sum_k s_k = 1000
K = 20
m = 5
D_formula = sum_k s_k - (K - 1) * m = 905
```

相邻 groups 每次共享 `m=5` 个 variables。因此 shared variables 数量为：

```text
|S| = (K - 1) * m = 19 * 5 = 95
```

overlap ratio 为：

```text
rho = |S| / D_formula = 95 / 905 ≈ 0.1049723757
```

Stage 1.6 测试固定检查：

```text
group count = 20
overlap size = 5
shared variable count = 95
overlap ratio = 95 / 905
```

这一步是从官方 F13/F14 构造公式推出的，不是经验猜测。前提是每对相邻 subcomponents 共享的 5 个 variables 互不重复；在官方 F13/F14 构造中，这产生 `19 * 5 = 95` 个 shared variables。

## 8. F13 与 F14 的差别

F13 与 F14 使用相同的 `Pvector/s/overlap` grouping rule，但冲突语义不同：

- F13：`conforming_overlap`。Overlapping subcomponents 的 shared variables 在 subcomponent transformations 中保持 conforming relation。
- F14：`conflicting_overlap`。Overlapping subcomponents 对 shared variables 有 conflicting shifts / transformations，是 LOCO 当前最直接的 CEC2013 conflicting-overlap smoke case。

因此 LOCO metadata 必须区分：

```text
F13 overlap_semantics = conforming_overlap
F14 overlap_semantics = conflicting_overlap
```

不能只用 `cec2013lsgo_overlap` 这样一个模糊标签替代。

## 9. F12 处理规则

F12 是 Shifted Rosenbrock。Rosenbrock 本身具有 chain dependency：

```text
f(x) = sum_i [100 * (x_i^2 - x_{i+1})^2 + (x_i - 1)^2]
```

这意味着它可被解释为相邻 pair 的 analytical chain coupling，但它没有 F13/F14 的：

```text
Pvector
s
overlap
```

因此 Stage 1.6 规则为：

- F12 不要求 `Pvector/s/overlap` 可读。
- F12 不允许被 F13/F14 extractor 硬套。
- F12 若 wrapper 未暴露可靠 metadata，则标记 `grouping_status=unavailable`。
- 若未来启用 analytical chain grouping，必须显式标记 `grouping_source=analytical_rosenbrock_chain`，不能伪装成 official `Pvector/s/overlap` grouping。

## 10. 官方评价协议与 FE Accounting

官方 evaluation setting 包括：

```text
15 minimization problems
25 runs per function
Max FE = 3 * 10^6
termination condition = maximum FE
```

官方还要求记录不同 FE checkpoints 的结果，并对 selected functions 画 convergence curve。对 LOCO-LSGO，这意味着 FE accounting 必须严格且可拆分：

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
```

或在实验实现中进一步映射为：

```text
FE_total = FE_base + FE_coordination + FE_repair + other_counted_FE
```

任何因为 coordination、repair、bridge subspace、metadata probing 或 compatibility adapter 引入的额外 function evaluations 都必须计入预算。不能把 LOCO 的额外 evaluate 当作“免费协调成本”。

## 11. LOCO-LSGO 使用建议

Stage 1.6 后，CEC2013 LSGO 在 LOCO 中的推荐角色为：

| Function | LOCO role | 是否适合作为 shared-variable conflict 主实验 |
|---|---|---|
| F12 | Rosenbrock-chain special overlap / adjacent interaction case。 | 可作为特殊结构；不要和 F13/F14 混为同一类。 |
| F13 | conforming overlapping subcomponents。 | 适合测试 LOCO 是否稳定、是否不过度干预。 |
| F14 | conflicting overlapping subcomponents。 | 最核心真实 benchmark。 |
| F8-F11 | non-overlapping 20-subcomponent partially separable。 | 适合作为 non-overlap 对照。 |
| F15 | fully non-separable。 | 可测试极端非分解场景，但不是 LOCO 主场景。 |

推荐论文表述：

```text
F14: primary real conflicting-overlap benchmark
F13: conforming-overlap sanity/stability benchmark
F12: Rosenbrock-chain special topology benchmark
Synthetic overlap: controlled topology / rho / dimension generalization
```

核心边界保持不变：LOCO-LSGO 不生成 optimizer，不选择 optimizer，不修改 BaseOpt；它只学习作用于 shared variables 的 coordination operators。

## 12. Stage 1.5/1.9 的语义修正

Stage 1.5 的早期 `PARTIAL` 不应解释为“F12 metadata failure 与 F13/F14 同类”。修正后：

- F12 metadata unavailable 是符合当前 wrapper 语义的合法状态。
- F13 evaluate mismatch 已定位为 `D_formula=905` 与 MetaBox implementation/API 内部 `Ovector(1000)` 的兼容问题，并通过显式 `implementation_api_adapter` 解决。
- F13 的 grouping、shared-variable count 和 overlap ratio 仍按 official `D_formula=905` 报告，不因为 runtime input surface 为 1000 而改成普通 1000D 函数。
- F14 是当前直接 905D 真实完整通过的 CEC2013 conflicting-overlap smoke case。
- 任何后续 wrapper compatibility adapter 都不能暗中 padding 或伪造 PASS，必须像 F13 一样写入 metadata 并在报告中单独说明。

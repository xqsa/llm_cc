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

## 2. 15 Functions 的四类结构

CEC2013 LSGO 共 15 个 functions，technical report / MetaBox 文档将其分为四类：

| 类别 | Functions | 结构语义 |
|---|---:|---|
| Fully-separable functions | F1-F3 | 完全可分离 large-scale functions。 |
| Partially separable functions | F4-F11 | F4-F7 有若干 non-separable subcomponents，并保留一个 fully-separable subcomponent；F8-F11 只有 non-separable subcomponents，没有额外 separable subcomponent。 |
| Overlapping functions | F12-F14 | F12-F13 属于 conforming overlapping family，F14 属于 conflicting overlapping。 |
| Fully-nonseparable function | F15 | 完全不可分离 large-scale function。 |

对 LOCO-LSGO 来说，真正需要 shared-variable coordination metadata 的主要对象是具有显式 subcomponent overlap metadata 的 F13/F14。F12 虽属于 overlapping family，但不是 F13/F14 那种 `S/m/Pvector` 显式分组格式。

## 3. F12/F13/F14 官方定义差异

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

## 4. D_formula 与 D_api 必须分开

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

不允许把 F13/F14 简化成普通 `1000D` 逻辑；不允许把 905 维 padding 到 1000 后假装解决问题。若后续必须对某个 official wrapper 做 905->1000 adapter，必须显式标记：

```text
grouping_source 或 adapter_mode = implementation_api_adapter
```

并证明该 wrapper 的 evaluate API 确实要求 1000D input。该 adapter 只能作为 wrapper compatibility 层，不能改变 official formula semantics。

## 5. F13/F14 Grouping Recovery 公式

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

## 6. F13 与 F14 的差别

F13 与 F14 使用相同的 `Pvector/s/overlap` grouping rule，但冲突语义不同：

- F13：`conforming_overlap`。Overlapping subcomponents 的 shared variables 在 subcomponent transformations 中保持 conforming relation。
- F14：`conflicting_overlap`。Overlapping subcomponents 对 shared variables 有 conflicting shifts / transformations，是 LOCO 当前最直接的 CEC2013 conflicting-overlap smoke case。

因此 LOCO metadata 必须区分：

```text
F13 overlap_semantics = conforming_overlap
F14 overlap_semantics = conflicting_overlap
```

不能只用 `cec2013lsgo_overlap` 这样一个模糊标签替代。

## 7. F12 处理规则

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

## 8. Stage 1.5 PARTIAL 的语义修正

Stage 1.5 的 `PARTIAL` 不应再解释为“F12 metadata failure 与 F13/F14 同类”。修正后：

- F12 metadata unavailable 是符合当前 wrapper 语义的合法状态。
- F13 evaluate mismatch 是 `D_formula=905` 与某些 implementation/API 内部 `Ovector(1000)` 的兼容问题。
- F14 是当前唯一真实完整通过的 CEC2013 conflicting-overlap smoke case。
- Stage 2 前仍需解决 F13 wrapper evaluate API 的 `D_formula/D_api` 兼容问题，但不能通过 padding 伪造 PASS。

# Stage 1.8 MetaBox F13 Internal Dimension Probe

创建日期：2026-06-20
执行者：Codex
阶段边界：只探查 MetaBox CEC2013LSGO F13/F14 内部维度语义；不修改 LOCO adapter，不修改 MetaBox source，不 padding，不重写 objective，不实现 optimizer。

## 1. 目标

本阶段回答一个很窄的问题：

```text
MetaBox 内部对 CEC2013LSGO F13/F14 的 dimension / dim / Ovector / Pvector / s 到底如何组织？
```

该问题直接影响 LOCO 后续是否需要为 F13 做 `implementation_api_adapter`。Stage 1.8 不做适配，只做 evidence probe。

## 2. 环境

本机 benchmark-only 环境：

- `metaevobox==2.0.2`
- `torch==2.12.1+cpu`
- 使用 LOCO 的 benchmark-only alias import，不执行 `metaevobox.__init__`
- 真实 MetaBox CEC2013LSGO numpy source 来自已安装 dependency

## 3. 关键发现

### F13

MetaBox `F13` 构造后字段为：

```text
dimension = 905
dim = 1000
Ovector shape = [1000]
Pvector shape = [1000]
s shape = [20]
s sum = 1000
overlap = 5
```

evaluate 行为：

```text
905D input  -> FAIL, shapes (1,905) and (1000,) cannot broadcast
1000D input -> PASS, finite objective
```

直接原因是 `F13.func()` 中：

```text
self.anotherz = x - self.Ovector
```

当 LOCO adapter 按 `dimension=905` 输入时，`x` 是 `(1,905)`，但 `Ovector` 是 `(1000,)`，因此 NumPy broadcasting 失败。

### F14

MetaBox `F14` 构造后字段为：

```text
dimension = 905
dim = 1000
OvectorVec len = 20
Pvector shape = [1000]
s shape = [20]
s sum = 1000
overlap = 5
```

evaluate 行为：

```text
905D input  -> PASS, finite objective
1000D input -> PASS, finite objective
```

F14 不使用 F13 那种单一 `Ovector` subtraction 路径，而是使用 `OvectorVec` 和 conflicting overlap rotation path。因此 F14 在 MetaBox 内部表现为 dual-input compatible。

## 4. 诊断结论

Stage 1.8 不能再把 F13 问题简单描述为“缺依赖”。当前本机已安装 `torch` 后：

- benchmark-only import 可用；
- F14 real smoke 可用；
- F13 grouping metadata 可恢复；
- F13 evaluate 仍受 internal dimension path 阻塞。

更准确的描述是：

```text
F13 exposes official overlap dimension=905, while retaining dim=1000,
Pvector length 1000, s sum 1000, and Ovector length 1000.
```

这说明 MetaBox 内部同时保留了 official overlapping dimension signal 和 1000-length construction data。F13 是否应以 905D 还是 1000D 进入 `func()`，需要单独确认，不能由 LOCO 直接 padding 后假装解决。

## 5. 对 LOCO 的影响

当前 LOCO 应保持：

- F14 作为 primary real conflicting-overlap smoke case；
- F13 作为 conforming-overlap internal dimension probe；
- 不把 F13 失败归因于 LOCO coordination pipeline；
- 不为通过测试而 padding；
- 不复制或修改 MetaBox CEC objective；
- 不实现 optimizer 或 controller。

如果后续要支持 F13 evaluate，应新增明确标记的：

```text
implementation_api_adapter
```

该 adapter 必须证明：

- 适配的是 MetaBox API/internal shape，而不是改写 official objective；
- FE accounting 不受影响；
- oracle/detected grouping 报告不被混淆；
- F13 905D official semantics 与 MetaBox 1000-length internal data 的关系被单独记录。

## 6. 当前产物

- `scripts/stage1/probe_metabox_f13_dimension.py`
- `docs/stage1/metabox_f13_dimension_probe.json`
- `tests/stage1/test_metabox_f13_dimension_probe.py`

## 7. 当前状态

Stage 1.8 status:

```text
PARTIAL
```

原因：

```text
F13 internal dimension mismatch is reproduced and localized.
F14 real evaluate is confirmed compatible.
No adapter fix has been attempted.
```

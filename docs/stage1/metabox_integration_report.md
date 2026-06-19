# Stage 1: MetaBox-v2 Integration Report

生成日期：2026-06-19  
执行者：Codex  
项目：LOCO-LSGO

## 1. 调研结论

本阶段优先复用 MetaBox-v2 / MetaBBO-v2 作为 benchmark backbone，不从零重写 CEC2013LSGO、BBOB 或已有 optimizer。LOCO 只新增轻量 adapter、overlap metadata、synthetic overlap structure generator、split manifest 与 registry。

已检查来源：

- MetaBox GitHub: https://github.com/MetaEvo/MetaBox
- PyPI package: `metaevobox==2.0.2`
- 本地下载源码包：`.codex-tasks/stage1-metabox-raw/metaevobox-2.0.2.tar.gz`
- 本地浅克隆：`.codex-tasks/stage1-metabox-raw/MetaBox`

## 2. 安装与导入检查

当前仓库是 git repository，当前分支为 `master`。

本地初始检查：

- `python -m pip show metaevobox`：未安装。
- `python -m pip show torch numpy`：`torch` 与 `numpy` 已安装。

按任务要求尝试：

```powershell
python -m pip install metaevobox
```

结果：失败。失败发生在依赖 `pygame==2.1.3` 构建阶段，Windows/Python 3.12 环境缺少 `distutils.msvccompiler`，导致 `Failed to build 'pygame' when getting requirements to build wheel`。

随后尝试：

```powershell
python -m pip download metaevobox --no-deps -d .codex-tasks\stage1-metabox-raw
```

结果：成功下载 `metaevobox-2.0.2.tar.gz`。

再尝试以 dependency 方式从本地源码包安装，不拉取/重建失败依赖：

```powershell
python -m pip install --no-deps --no-build-isolation .codex-tasks\stage1-metabox-raw\metaevobox-2.0.2.tar.gz
```

结果：成功安装 `metaevobox-2.0.2`。

尝试从源码路径导入：

```python
from metaevobox import Config
from metaevobox.environment.problem.utils import construct_problem_set
```

结果：失败。`metaevobox.__init__` 会导入 `Trainer`，进一步触发 optimizer / `tianshou` 依赖；当前环境最初缺 `sensai`。补装 `sensai-utils==1.6.0` 并安装 `metaevobox --no-deps` 后，导入继续失败于缺少 `pettingzoo`，且该 import 链会继续触发训练器、optimizer、HPO-B、xgboost、pandas/pyarrow 等非 benchmark-only 依赖。

因此 Stage 1 代码采用 lazy import 与清晰错误信息；单元测试使用 fake MetaBox problem 验证 adapter contract，避免把 MetaBox 的 MetaBBO agent / optimizer 依赖链误纳入 LOCO 核心路径。

## 3. MetaBox-v2 仓库结构观察

源码包中存在：

```text
src/metaevobox/environment/problem/utils.py
src/metaevobox/environment/problem/SOO/CEC2013LSGO/__init__.py
src/metaevobox/environment/problem/SOO/CEC2013LSGO/cec2013lsgo_dataset.py
src/metaevobox/environment/problem/SOO/CEC2013LSGO/cec2013lsgo_numpy.py
src/metaevobox/environment/problem/SOO/CEC2013LSGO/cec2013lsgo_torch.py
src/metaevobox/environment/problem/SOO/CEC2013LSGO/datafile/
```

`construct_problem_set(config)` 中，`problem in ['lsgo', 'lsgo-torch']` 会调用 `CEC2013LSGO_Dataset.get_datasets(...)`。这说明 MetaBox 已有 LSGO problem set loading 能力，LOCO 不应重写 benchmark。

## 4. CEC2013LSGO API 观察

已确认源码中存在：

- `CEC2013LSGO_Dataset`
- `CEC2013LSGO_Numpy_Problem`
- `CEC2013LSGO_Torch_Problem`
- `F1 ... F15`
- `F12`
- `F13`
- `F14`

`CEC2013LSGO_Dataset` difficulty split：

| difficulty | train | test |
|---|---|---|
| `easy` | F1-F9 | F10-F15 |
| `difficult` | F7-F15 | F1-F6 |
| `all` | F1-F15 | F1-F15 |

MetaBox CEC2013LSGO base problem exposes or documents:

- `dim`
- `dimension` for some functions
- `lb`
- `ub`
- `opt`
- `optimum`
- `overlap`
- `s_size`
- `Pvector`
- `Ovector`
- `OvectorVec`
- `func(x)`
- `eval(x)` inherited from `Basic_Problem`
- `numevals`

`func(x)` in numpy implementation expects batch-shaped input and returns vector-shaped values. LOCO adapter normalizes a single `np.ndarray` candidate into the expected shape and returns a Python `float`.

## 5. F12 / F13 / F14 metadata notes

MetaBox source indicates:

- `F12` is class `F12`, string name `Shifted Rosenbrock`; it does not expose `Pvector` / `s` overlap grouping in the same way as F13/F14.
- `F13` sets `dimension = 905`, `overlap = 5`, reads `Pvector`, `s`, `w`, rotations, and is named conforming overlapping subcomponents.
- `F14` sets `dimension = 905`, `overlap = 5`, reads `s`, `OvectorVec`, `Pvector`, `w`, rotations, and is named conflicting overlapping subcomponents.

LOCO wrapper reconstructs grouping from `Pvector`, `s`, and `overlap` when available. If reliable grouping cannot be reconstructed, metadata marks:

```text
grouping_source = "unknown"
grouping_confidence = "low"
```

This is expected for environments where MetaBox import fails or for functions whose MetaBox instance does not expose grouping fields.

## 6. Torch / NumPy implementation

源码中同时存在：

- `cec2013lsgo_numpy.py`
- `cec2013lsgo_torch.py`

LOCO Stage 1 default config uses `version: numpy`。Torch path is intentionally not made mandatory in tests because the project goal here is adapter/interface correctness, not MetaBBO training or torch optimizer integration.

## 7. License 记录

MetaBox repository license:

- `BSD 3-Clause License`
- Copyright holder: MetaEvolution Lab

CEC2013LSGO implementation notice inside MetaBox source/docstring:

- Official implementation link: https://github.com/dmolina/cec2013lsgo
- License noted by MetaBox CEC2013LSGO source: `GPL-3.0`

Stage 1 decision:

- 不复制 MetaBox benchmark source code。
- 不复制 CEC2013LSGO implementation source code。
- 只通过 dependency / adapter 使用 MetaBox API。
- 如果未来需要 vendoring，必须单独做 GPL-3.0 兼容性审计。

## 8. 当前差异与风险

实际环境与理想 API 的差异：

- `metaevobox` 可以从 PyPI 下载源码；常规 `pip install metaevobox` 在当前 Windows/Python 3.12 环境失败于 `pygame==2.1.3` 构建。
- `metaevobox --no-deps --no-build-isolation` 可以从本地源码包安装成功，但 top-level import 仍缺少 agent/optimizer 侧依赖。
- `from metaevobox import Config` 会触发训练器和 optimizer 依赖，不是轻量 benchmark-only import。
- 因此 Stage 1 tests 在 MetaBox 不可用时检查清晰错误，而不是伪造加载成功。

最大风险：

- MetaBox 包的 top-level import 副作用过重，会让 benchmark-only adapter 依赖 optimizer/agent 侧依赖。Stage 2 前建议在隔离环境中安装 MetaBox，或与 MetaBox 维护的 package import policy 对齐，优先请求 benchmark-only import path。

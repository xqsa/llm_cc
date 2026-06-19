# Stage 1.5: MetaBox Benchmark-only Import Report

生成日期：2026-06-19
执行者：Codex
任务边界：只处理 MetaBox benchmark-only import 与真实 F12/F13/F14 smoke，不进入 Stage 2。

## 1. 是否存在不触发 top-level trainer/optimizer/agent 的 benchmark-only import path？

存在一个 LOCO 侧 benchmark-only bypass path，但它不是 MetaBox 官方公开 API。

当前实现位于：

```text
loco/benchmarks/cec2013lsgo_metabox.py
```

核心思路：

- 使用 `importlib.util.find_spec("metaevobox")` 定位已安装 package 路径；
- 不执行 `metaevobox.__init__`；
- 只从已安装 package 文件路径加载：
  - `environment/problem/basic_problem.py`
  - `environment/problem/SOO/CEC2013LSGO/cec2013lsgo_numpy.py`
- 使用 alias package `loco_external_metaevobox...` 保持相对 import 可用；
- 仍然复用已安装 MetaBox 源码，不复制 CEC2013LSGO 源码到 LOCO。

这条路径可以加载 `F12`、`F13`、`F14` class，并避免 trainer / optimizer / agent import 链。

## 2. 能否直接 import metaevobox.environment.problem.SOO.CEC2013LSGO？

当前环境不能直接 import。

命令：

```python
import importlib
importlib.import_module("metaevobox.environment.problem.SOO.CEC2013LSGO")
```

结果：

```text
ModuleNotFoundError: No module named 'pettingzoo'
```

## 3. 如果直接 import 仍触发重依赖链，具体触发路径是什么？

当前触发路径为：

```text
metaevobox.__init__
-> metaevobox.trainer
-> metaevobox.environment.basic_environment
-> metaevobox.environment.optimizer.learnable_optimizer
-> metaevobox.environment.optimizer.__init__
-> metaevobox.environment.optimizer.madac_optimizer
-> tianshou
-> tianshou.env.pettingzoo_env
-> pettingzoo
```

此外，失败日志中还观察到 trainer / optimizer 侧 import 可继续牵出 HPO-B、xgboost、pandas、pyarrow 等非 CEC2013LSGO benchmark-only 依赖。

## 4. 当前缺失依赖有哪些？

已观察到的直接缺失依赖：

- `pettingzoo`

此前常规 `pip install metaevobox` 失败还涉及：

- `pygame==2.1.3` 构建失败；
- Windows/Python 3.12 下缺 `distutils.msvccompiler`；
- 初始源码路径导入时缺 `sensai`，已通过 `sensai-utils==1.6.0` 补齐。

## 5. 哪些依赖是 benchmark-only 必需的？

对 CEC2013LSGO numpy benchmark-only smoke，当前必要依赖主要是：

- `numpy`
- MetaBox package 文件中的 `basic_problem.py`
- MetaBox package 文件中的 `CEC2013LSGO/cec2013lsgo_numpy.py`
- MetaBox package 中的 `CEC2013LSGO/datafile/*`

`torch` 仅对 torch version 必需；Stage 1 默认 `version: numpy`，不要求 torch path 通过。

## 6. 哪些依赖只是 MetaBBO trainer/agent 侧引入的？

根据当前 import trace，下列依赖属于 trainer / optimizer / agent 链，非 CEC2013LSGO numpy benchmark-only 必需：

- `tianshou`
- `pettingzoo`
- `ray`
- `tensorboard`
- `tensorboardX`
- `xgboost`
- `pandas`
- `pyarrow`
- `pygame`
- MetaBox optimizer modules
- MetaBox Trainer / PBO_Env

## 7. 是否可以通过 isolated venv 解决？

可以，但要区分两个目标：

- 若目标是运行完整 `metaevobox` top-level API，需要 isolated venv 补齐 MetaBBO trainer/agent 依赖，包括 `pettingzoo`、`pygame` 等。
- 若目标只是 LOCO benchmark-only smoke，当前 LOCO bypass path 已能加载 CEC2013LSGO numpy classes，不需要完整 trainer/agent 依赖。

论文实验前仍建议创建 isolated venv，并记录：

```powershell
python -m venv .venv-metabox
.venv-metabox\Scripts\python -m pip install metaevobox
.venv-metabox\Scripts\python scripts\stage1\check_metabox_cec2013lsgo_real.py
```

如果 Windows/Python 3.12 继续卡在 `pygame==2.1.3`，建议尝试 Python 3.10/3.11 或使用 MetaBox 官方推荐环境。

## 8. 是否需要向 MetaBox 提 issue 或做 upstream patch proposal？

建议需要。

建议 upstream issue / patch proposal：

1. 提供 benchmark-only import path，例如：

```python
from metaevobox.environment.problem.SOO.CEC2013LSGO.cec2013lsgo_numpy import F12, F13, F14
```

不应触发 Trainer、optimizer、agent、tianshou 或 pettingzoo。

2. `metaevobox.environment.problem.SOO.__init__` 不应 eager import HPO-B / xgboost / pandas / pyarrow 等非当前 benchmark 依赖。

3. 检查 F13 official dimension=905 下，MetaBox numpy implementation 中 `x(905)` 与 `Ovector(1000)` 的 shape mismatch。

## 9. LOCO 当前是否应该继续采用 lazy import adapter？

是。

理由：

- 避免把 MetaBBO trainer/agent 依赖链引入 LOCO benchmark layer；
- 避免把 MetaBox MetaBBO agent 误用为 LOCO 方法核心；
- 保持 Stage 1/1.5 只做 benchmark adapter 和 metadata；
- 在真实环境不可用时给出清晰错误，而不是 fake benchmark success。

## 10. 当前真实 smoke 状态

最新脚本：

```powershell
python scripts\stage1\check_metabox_cec2013lsgo_real.py --json-output docs\stage1\metabox_real_smoke_latest.json
```

当前状态：`PARTIAL`

已通过：

- benchmark-only bypass import 可加载 MetaBox CEC2013LSGO numpy module；
- F12/F13/F14 class 可加载；
- F13/F14 的 `D_formula=905` 被保留，并与 wrapper/API 层 `D_api=1000` 分开记录；
- F13/F14 的 `Pvector`、`s`、`overlap` 可读；
- F13/F14 grouping 可重建，group count 为 20，overlap size 为 5；
- F13/F14 shared variables 数量为 95，overlap ratio 为 `95/905`；
- F13/F14 incidence matrix shape 为 `905 x 20`；
- F12 不再要求 `Pvector/s/overlap`，当前 `grouping_status=unavailable` 是合法 metadata 状态；
- F14 可以在 905 维输入上通过 LOCO adapter evaluate，且 zero/random eval finite、deterministic。

当前 blocker：

- 普通 direct import 仍触发 trainer/optimizer/agent 依赖链，失败于 `pettingzoo`。
- F13 在 official `D_formula=905` 输入下，MetaBox numpy implementation 内部执行 `x - Ovector` 时出现 `x(1,905)` 与 `Ovector(1000,)` shape mismatch。这是 `D_formula/D_api` compatibility blocker。
- F12 在当前 MetaBox implementation 中未暴露 `Pvector`、`s`、`overlap`，但 Stage 1.6 已确认 F12 不使用 F13/F14 的 `Pvector/s/overlap` grouping rule，因此不再把 F12 metadata unavailable 视为同类失败。

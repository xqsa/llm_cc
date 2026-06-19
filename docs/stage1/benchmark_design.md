# Stage 1: Benchmark Design

生成日期：2026-06-19  
执行者：Codex

## 1. 设计目标

Stage 1 只建立 benchmark 与数据加载系统，不实现优化算法、LLM、evolution、controller/scheduler 或 coordination operator。

设计原则：

- MetaBox-v2 优先作为 benchmark backbone。
- LOCO 只提供统一接口、轻量 adapter、overlap metadata、synthetic overlap structure、split manifest 和 registry。
- 后续阶段不能直接依赖 MetaBox 内部类，必须通过 `LSGOProblem` 或 registry 访问。

## 2. 统一接口

核心接口位于：

```text
loco/benchmarks/problem_interface.py
```

`LSGOProblem` 提供：

- `evaluate(x) -> float`
- `bounds() -> tuple[np.ndarray, np.ndarray]`
- `dimension() -> int`
- `optimum_value() -> float | None`
- `grouping() -> list[list[int]] | None`
- `shared_variables() -> set[int]`
- `overlap_degree() -> dict[int, int]`
- `metadata() -> dict`

`metadata()` 仅用于实验日志。coordination operator 不能访问 metadata，尤其不能访问 `function_id`、`benchmark_name`、test-set metadata 或 hidden test information。

## 3. MetaBox adapter

`MetaBoxProblemAdapter` 位于：

```text
loco/benchmarks/metabox_adapter.py
```

职责：

- 包装 MetaBox problem instance；
- 从 `dim` / `dimension` 读取维度；
- 从 `lb` / `ub` 读取 bounds；
- 从 `get_optimal()` / `opt` / `optimum` 读取 optimum value；
- 调用 `eval(x)` 或 `func(x)` 评价单个 candidate；
- 维护 LOCO 侧 `fe_count`；
- 不修改 MetaBox objective logic；
- 不复制 MetaBox benchmark source。

## 4. CEC2013LSGO wrapper

`cec2013lsgo_metabox.py` 提供：

- `load_cec2013lsgo_problem(function_id, version="numpy")`
- `load_cec2013lsgo_suite(function_ids, version="numpy")`
- `load_cec2013lsgo_overlap_suite()`

`load_cec2013lsgo_overlap_suite()` 固定优先 F12/F13/F14。

如果 MetaBox 不可用，loader 抛出 `MetaBoxImportError`，不静默 fallback，不伪造 benchmark。

## 5. Synthetic overlap supplement

`synthetic_overlap_generator.py` 只生成 LOCO-specific controlled overlap structures，用来补充 MetaBox 不直接提供的 topology / overlap ratio / dimension generalization。

支持：

- `line`
- `ring`
- `random_graph`
- D = 100, 500, 1000, 2000, 5000
- overlap ratio = 0.05, 0.10, 0.20, 0.30
- fixed seed reproducibility

Synthetic objective 仅作为可加载 controlled supplement，当前为简单 sphere 形式，不包含 hidden shared-variable rule，不代表 LOCO 算法贡献。

## 6. Registry

`benchmark_registry.py` 是后续阶段统一入口：

- `get_problem(name)`
- `list_problems(split=None)`
- `load_manifest(path)`

registry 可以把 metadata 用于实验日志，但不得把 metadata 暴露给 coordination operator。


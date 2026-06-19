# Stage 1: Overlap Metadata Spec

生成日期：2026-06-19  
执行者：Codex

## 1. 符号

变量维度为 `D`，分组为：

```text
G = {G_1, ..., G_M}
```

变量 `i` 的 overlap degree：

```text
m_i = sum_k 1(i in G_k)
```

shared variable set：

```text
S = {i | m_i >= 2}
```

incidence matrix：

```text
A[i, k] = 1 if i in G_k else 0
```

overlap ratio：

```text
rho = |S| / D
```

## 2. 数据结构

`OverlapMetadata` 位于：

```text
loco/benchmarks/overlap_metadata.py
```

字段：

- `groups`
- `shared_variables`
- `overlap_degree`
- `incidence_matrix`
- `topology`
- `overlap_ratio`
- `grouping_source`
- `grouping_confidence`

## 3. 合法性检查

`build_overlap_metadata()` 必须检查：

- `dimension > 0`
- 每个 group 非空
- index 非负
- index 小于 `D`
- group 内无重复 index
- `overlap_degree` 与 incidence matrix 一致
- `shared_variables` 显式由 `m_i >= 2` 计算

## 4. 信息边界

Overlap metadata 可以进入 operator-facing view 的结构字段：

- groups
- shared variables
- overlap degree

禁止进入 operator-facing view 的字段：

- function id
- benchmark name
- true optimum location
- test-set metadata
- hidden test information
- future evaluations


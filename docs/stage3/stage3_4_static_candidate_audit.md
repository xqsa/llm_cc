# Stage 3.4 Candidate Quality Filter and Static Diversity Audit

创建日期：2026-06-20
执行者：Codex
阶段边界：Stage 3.4 只做 candidate quality filter 和 static diversity audit。它读取 Stage 3.3 的 accepted train-only candidate logs，分析 typed coordination operator AST 的静态结构，不调用 LLM、不运行 evolution、不执行 AST、不评价 objective、不做 performance claim。

## 1. 阶段目标

Stage 3.4 回答一个很具体的问题：

```text
Stage 3.3 生成的 9 个 accepted candidates
到底有没有结构差异，
还是基本只是同一种 weighted+clip 变体？
```

因此本阶段只看 AST 静态结构：

```text
accepted_candidates.jsonl
-> quality_filter_report.json
-> static_diversity_audit.json
-> stage3_4_summary.json
```

## 2. Quality Filter

当前 quality filter 是静态规则，不使用 objective feedback：

```text
empty_ast
missing_target_variable
single_consensus_only
```

当前 Stage 3.3 candidate corpus 的结果：

```text
candidate_count = 9
quality_pass_count = 7
quality_reject_count = 2
issue_counts = {"single_consensus_only": 2}
```

被标记的 2 个候选都是单节点 `weighted_consensus`，没有后续 `clip`、`projection`、`dampening`、`reweighting` 或 `repair` 结构。它们不是 schema/boundary failure，但作为候选库质量过滤阶段，属于过于 trivial 的 consensus-only candidates。

## 3. Static Diversity Audit

Stage 3.4 统计：

```text
AST fingerprint count
node kind sequence distribution
operator family distribution
node kind counts
target variable counts
node count distribution
```

当前结果：

```text
unique_ast_fingerprint_count = 9
unique_kind_sequence_count = 2
dominant_kind_sequence = weighted_consensus->clip
dominant_kind_sequence_count = 7
low_diversity_warning = true
```

结构分布：

```text
weighted_consensus->clip = 7
weighted_consensus = 2
```

operator family 分布：

```text
weighted_consensus+clip = 7
weighted_consensus = 2
```

node kind 分布：

```text
weighted_consensus = 9
clip = 7
```

这个结果说明：虽然 9 个候选的 AST fingerprint 都不同，但它们的结构族非常集中。当前 Stage 3.3 corpus 基本是 weighted_consensus / weighted_consensus->clip 变体，还没有覆盖 projection、dampening、reweighting、repair 等更丰富的 coordination mechanisms。

## 4. Honest Interpretation

Stage 3.4 可以声明：

```text
The Stage 3.3 candidate corpus is boundary-valid and replayable, but static structural diversity is low. Seven of nine accepted candidates are weighted_consensus->clip variants, and two are single weighted_consensus candidates filtered as single_consensus_only.
```

Stage 3.4 不能声明：

```text
learned reusable coordination operators
operator performance improvement
evolution selection success
generalization
SOTA optimization result
```

## 5. Next Implication

Stage 3.5 不应直接进入 performance evaluation。更合理的下一步是 prompt-space hardening：

```text
require explicit coverage of projection / dampening / reweighting / repair families
limit repeated weighted_consensus->clip variants
keep train-only and no objective evaluation
rerun Stage 3.3 candidate generation
rerun Stage 3.4 static audit
```

这一步的目标是先让 candidate library 在结构上更像一个可搜索的 coordination operator space，再进入 evolution selection。

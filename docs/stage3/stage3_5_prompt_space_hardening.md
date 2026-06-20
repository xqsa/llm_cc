# Stage 3.5 Prompt-space Hardening

创建日期：2026-06-20
执行者：Codex
阶段边界：Stage 3.5 只做 train-only prompt-space hardening 和 candidate family coverage gate。它真实调用 LLM 多批次生成 typed coordination operator AST candidates，但不运行 evolution、不执行 AST、不评价 objective、不使用 validation/test feedback、不做 performance claim。

## 1. 阶段目标

Stage 3.4 发现 Stage 3.3 的 9 个 candidates 结构多样性偏低：

```text
7/9 = weighted_consensus->clip
2/9 = weighted_consensus
```

Stage 3.5 的目标是修这个 candidate supply 问题，而不是进入性能实验：

```text
hardened prompt
-> train-only multi-batch LLM generation
-> Stage 3.1 replay
-> Stage 3.4 static audit
-> Stage 3.5 coverage gate
```

## 2. PASS 标准

Stage 3.5 必须同时满足：

```text
api_call_count >= 3
raw_candidate_count >= 12
accepted_count >= 8
quality_pass_count >= 8
unique_kind_sequence_count >= 5
operator_family_count >= 5
dominant_kind_sequence_count / quality_pass_count <= 0.5
must_include_projection = true
must_include_dampening = true
must_include_reweighting = true
must_include_repair = true
must_include_best_reward_select = true
no_evolution_run = true
no_objective_evaluation = true
not_performance_claim = true
```

## 3. Current Result

当前真实 DeepSeek-compatible run：

```text
status = PASS
api_call_count = 3
raw_candidate_count = 12
accepted_count = 12
quality_pass_count = 12
unique_kind_sequence_count = 8
operator_family_count = 8
dominant_kind_sequence = projection->dampening
dominant_kind_sequence_count = 3
dominant_ratio = 0.25
```

required family coverage：

```text
projection = true
dampening = true
reweighting = true
repair = true
best_reward_select = true
```

当前 kind sequence distribution：

```text
projection->dampening = 3
best_reward_select->dampening->clip = 2
reweighting->repair = 2
projection->reweighting->repair = 1
projection->projection->best_reward_select->dampening->clip = 1
projection->projection->weighted_consensus->projection = 1
reweighting->weighted_consensus->clip = 1
weighted_consensus->projection = 1
```

## 4. First Failed Attempt

第一次 Stage 3.5 真实 run 没有通过 coverage gate：

```text
accepted_count = 5
quality_pass_count = 5
unique_kind_sequence_count = 3
operator_family_count = 3
dominant_ratio = 0.6
must_include_reweighting = false
must_include_repair = false
status = FAIL
```

主要原因不是 LLM 完全不理解 family，而是使用了非法 DSL input keys，例如：

```text
alpha
method
strategy
lower_bound
upper_bound
selection
source = raw
```

修复方式不是放宽 validator，而是强化 prompt：明确允许的 input keys，并要求 source 必须引用同一 AST 中更早出现的 node id。

## 5. Claim Boundary

Stage 3.5 可以声明：

```text
The prompt-space hardening gate produced a broader train-only candidate corpus that covers projection, dampening, reweighting, repair, and best_reward_select families under the existing typed AST boundary.
```

Stage 3.5 不能声明：

```text
learned reusable coordination operators
evolution search success
operator performance improvement
generalization
SOTA optimization result
```

## 6. Next Step

下一步可以进入 Stage 3.6 或 Stage 4 之前的最后静态准备：

```text
freeze the Stage 3.5 quality-pass candidate pool
write candidate family descriptors
prepare train-only evolution/search protocol
```

如果进入 Stage 4，必须仍然只使用 train split，且所有 FE accounting 和 no-test-feedback firewall 继续生效。

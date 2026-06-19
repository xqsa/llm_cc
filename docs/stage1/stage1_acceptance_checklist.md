# Stage 1: Acceptance Checklist

生成日期：2026-06-19  
执行者：Codex

## 1. 最低完成标准

- [ ] 已调研 MetaBox-v2 / metaevobox API。
- [ ] 已记录 MetaBox 与 CEC2013LSGO license。
- [ ] 已尝试 `pip install metaevobox`，并记录真实结果。
- [ ] 已创建 `LSGOProblem` interface。
- [ ] 已创建 `MetaBoxProblemAdapter`。
- [ ] 已创建 CEC2013LSGO wrapper，优先 F12/F13/F14。
- [ ] 未重写 CEC2013LSGO objective。
- [ ] 未复制 MetaBox benchmark source。
- [ ] 已创建 overlap metadata builder。
- [ ] 已显式输出 groups `G`。
- [ ] 已显式输出 shared variables `S`。
- [ ] 已显式输出 incidence matrix `A`。
- [ ] synthetic overlap generator 支持 line/ring/random_graph。
- [ ] split manifest 可冻结。
- [ ] registry 通过 `LSGOProblem` 暴露问题。
- [ ] tests/stage1 通过。

## 2. 禁止项

Stage 1 判定失败的情况：

- 实现新的 optimizer。
- 实现 DE/CMA-ES/PSO/SHADE/L-SHADE。
- 实现 LLM operator generation。
- 实现 evolution search。
- 实现 coordination operator logic。
- 实现 controller/scheduler。
- 修改 BaseOpt。
- 把 MetaBox MetaBBO agent 当作 LOCO 核心方法。
- 测试阶段调用 LLM。
- 把 benchmark metadata 暴露给 coordination operator。
- 直接复制第三方 benchmark source 且未记录 license。

## 3. 当前验收命令

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest -p no:cacheprovider tests/stage1 -q
```


# Test Feedback Firewall

创建日期：2026-06-20
执行者：Codex
阶段边界：定义 Stage 3 train/validation/test firewall；Stage 3.0 no LLM call、no evolution run。

## 1. Firewall 目标

Test feedback firewall 的目标是防止 hidden test information 进入：

- LLM prompt；
- candidate generation；
- candidate rejection；
- evolution selection；
- operator promotion；
- operator library 修改。

## 2. Split 权限

train 可以用于：

- LLM candidate generation；
- evolution selection；
- rejection corpus expansion；
- train-only diagnostics。

validation 可以用于：

- operator selection；
- early stopping；
- promotion decision；
- protocol-level sanity check。

test 只能用于：

- frozen final operator 的 sealed final reporting。

## 3. 禁止回流

以下行为禁止：

- 把 test metrics 放进 LLM prompt；
- 用 test failure 修改 candidate schema；
- 用 test result 调整 evolution hyperparameters；
- test 后修改 operator AST；
- test 后重新选择 operator；
- 把 benchmark name、function_id、true optimum location 或 hidden test metadata 传给 LLM。

## 4. Stage 3.0 Status

Stage 3.0 只锁定 firewall，不读取 test metrics，不调用 objective function，不生成 candidate，不运行 evolution。

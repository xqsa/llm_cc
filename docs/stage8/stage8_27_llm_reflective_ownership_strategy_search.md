# Stage 8.27 Real LLM Reflective Ownership-aware Strategy Search

Created by Codex on 2026-06-23.

## Purpose

Stage 8.27 moves the LLM role back into the research core. The LLM is not asked
to generate a full optimizer. It is asked to generate bounded ownership-aware
strategy programs under the Stage 8.26 DSL:

```text
shared-variable conflict
-> ownership / multi-assignment / linkage / coordination action
-> Stage 8.26 evaluator
-> behavior-equivalence guard
```

Fake LLM strategies are forbidden. If a real LLM API call is unavailable, the
stage writes blocked artifacts instead of fabricating candidates.

## Boundary

Stage 8.27 does not run CEC F13/F14, does not run the 25-run panel, and does not
make a SOTA claim. It also does not modify BaseOpt, rewrite benchmarks, generate
optimizers, generate schedulers/controllers, use validation/test feedback, or use
reported SOTA values as runtime feedback.

## Required Gate

Accepted ownership-aware strategy programs must pass the Stage 8.26 evaluator:

```text
not equivalent to best_reward_select
non-trust branch exercised
ownership or linkage decision exercised
```

## Next Stage

If Stage 8.27 passes with real LLM-generated strategies, route to Stage 8.28 LLM
vs non-LLM ownership-strategy ablation. If it is blocked by API availability or
call failure, rerun Stage 8.27 after the real LLM API is available.

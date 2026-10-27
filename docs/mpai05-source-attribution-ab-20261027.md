# MP-AI05 — scored source attribution A/B, 2026-10-27

Execution: **PASS**, [FORGE run #40467144838](https://github.com/spoonman136668-ai/FORGE/actions/runs/40467144838).
Source commit: `3b96dd78beb1c86bd4039327daa650371e929d2c`. Pinned Mind-Palace source: `7ad7230a82e3c748aa5336b7288ad2b45d42630c`.
External third-party local model: Qwen2.5-1.5B-Instruct Q4_K_M; GGUF SHA-256 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`. No paid API, Wingless or Yggdrasil involved. Protected holdout access 0.

Four deterministic non-holdout tasks: exact Mind-Palace record ID given a source-record statement excerpt. Retrieval matched the target ID in its top four in all cases. Both arms run at temperature 0, max output 96 tokens. Scores use **exact ID string equality**, not semantic assessment.

| Case | Baseline correct | Memory correct | Target found in retrieval |
|---|---|---|---|
| 1 | No | No | Yes |
| 2 | No | No | Yes |
| 3 | No | No | Yes |
| 4 | No | Yes | Yes |
| TOTAL | 0/4 | 1/4 | 4/4 |

| Metric | Baseline | Memory |
|---|---:|---:|
| Prompt tokens | 452 | 1296 |
| Completion tokens | 39 | 62 |
| Inference seconds | 3.070 | 5.796 |

**Scientific status: preliminary positive observation for one case; NOT a demonstrated robust memory improvement.** Sample is very small, question construction exposes part of target statement, scoring penalizes formatting variations, and four cases were selected deterministically without prospective randomization. Retrieval alone contains the right IDs but generative output was unsuccessful in three treatment cases. Identical output hashes in cases 1–3 across arms indicate no detected output change in those cases. The increased context cost is material.

Next discriminating experiment: diagnose the model's failure mode on the three cases (UNKNOWN, formatting, instruction following) using a predeclared score policy; test a bounded, larger case set with direct lexical lookup as a non-model control; then consider stronger models only if model-based retrieval yields a genuine advantage over that control. Keep holdouts untouched.

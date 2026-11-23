# R12 — learned HOW to encode compositional relationships

## Why this gate exists

FORGE R11 genuinely learned a training-only per-source memory-retention controller, but its independently reviewed development results failed the frozen worst-source transfer rule on **all 3 folds**. Source: [R11 original evaluation and reviewer, run #38665222559](https://github.com/spoonman136668-ai/FORGE/actions/runs/38665222559), original independent review archive `11940945840`, file SHA-256 `c47cd167f988e0dbe3258b14f82cb4b785966b3939fee5fa5b970f96cf4063b6`.

The next research question is **not another high-loss-example selection rule**. R12 tests whether a compact *trainable two-link role code* preserves useful compositional structure under a strict bounded memory, on unseen entity assignments and longer paths.

## New method and genuine scientific controls

Each task is a public deterministic but novel multi-relational graph with new permuted entity identities and role assignments. A query requires traversing either four roles (two compressed steps, 4 answerable paths) or six roles (three compressed steps, 3 answerable paths). At each stage, a competing path uses a different relation-pair label. **The compressor runs without observing any future query.**

Every method is constrained to at most **16 retained memory slots**. The learned compressor codes each ordered pair of relation types into a **2-dimensional quantized 3×3 code**, using exactly **8 trainable real scalars**. Those eight scalars are trained through deterministic coordinate search using *future-question correctness on a training-only cohort*, then frozen before any development/structural-stress query. No development answer may guide optimization.

Four useful preregistered controls are scored with exactly the same graphs and questions:

- **Chronological 16 raw edges** — no compression, truncation under the same slot budget.
- **Fixed two-link hash** — fixed, lossy pair encoding with the same 16 compressed slots.
- **Exact two-link symbolic oracle** — lossless pair labels and the same slot budget, explicitly an **upper bound**, not a matched learned-parameter control.
- **Shuffled-query relation labels** — a negative control to detect spurious gains without meaningful role binding.

The encoding scheme retains exact entity pointers and a fixed pair-traversal algorithm; it does **not** demonstrate native learned graph construction, autonomous scientific hypothesis generation or full-fledged relationship reasoning. The comparison tests whether learning the role-code representation provides value *beyond a fixed lossy encoding*.

## Freeze and novel generalization conditions

R12 commits one immutable experiment identity in `research/r12-relational-memory/frozen.json`: 24 development-training graph seeds 30000–30023, 16 completely separate 4-role-hop graph seeds 31000–31015, and 16 harder **six-hop structural transfer** seeds 32000–32015. Seeds 33000–33031 are reserved for a hypothetical future sealed experiment and **must never be generated** by R12. These are independent of previously consumed Wingless original seeds and R11 development 28xxx/29xxx cohorts.

A development signal is recognized only if the learned encoder improves accuracy over the fixed lossy code by **at least five percentage points on both** the four-hop and six-hop cohorts. A positive result is merely a developmental method signal; an independent source/custody and one-shot original would still be needed to claim scientific improvement.

## Reproducible independent witness

A separate R12 reviewer imports neither the original generator nor the model training code. It independently rebuilds all graph structures and decoy paths, refits the eight parameters using only training seeds, recomputes every **64 novel-binding and 48 longer-chain query** answer, tests all four controls, verifies the source hashes and unconsumed authority flags, and checks the frozen decision threshold without changing it.

This procedure runs on the **existing GitHub-hosted qualification path**, with source-only unit tests on both Linux and Windows and a single native FORGE full regression. No new FORGE controller, no paid model API, no Cloudflare configuration changes, no new external FSA, no CKB-plane/KTRADE changes, and no Wingless/Yggdrasil science ref mutations.

**After R12:** if the learned representation fails, preserve a valid negative and focus on a more powerful structure-aware compression or retrieval mechanism. If it succeeds, independently qualify method fidelity on other structures and preregister a fresh original under the already-proven once-only R8-style worker, never replaying R7/R8.

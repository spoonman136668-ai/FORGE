# F102 — Yggdrasil Y100-C1 learned relation-role composition, public DEV only

F102 executes the first separately preregistered **Yggdrasil learned typed-role counterfactual mechanism** using only the existing FORGE GitHub-hosted Linux/Windows cycle. It is an implemented model-training experiment, **not** just a synthetic proposal receipt. It does not consume Codex, Work task, a paid model API or protected Yggdrasil science data.

## Preregistration before executable implementation

- Source parent: F101 branch head `c7080b5e53145840bf3f799cd481760f9918e404`; F100 frozen four-mechanism contract Git blob `79718d11be36ac4742774cf3ab3d502ef2feab59`.
- Original historical negative: Yggdrasil Y-F9, learned role-blind frozen model **0/192** typed counterfactual pairs, coded strong control **192/192**. Preserved as historical evidence, neither replayed nor reclassified as independent scientific progress.
- Separate first F102 commit `15eca660367fb43d0b5143ed2df34899d3ffea40` froze its actual model, new public seed blocks, training budget, success and failure criteria **before** implementation.

## Genuine learned mechanism and baseline controls

The Y100-C1 learned candidate has **18 trainable scalars**: a 4×4 role-query compatibility table (16) plus a learned target-state readout scale and bias (2). It propagates soft, learned, query-conditioned relational state across four edge hops and trains using a full-cohort analytic-gradient binary cross-entropy for **100 updates** on 96 publicly generated pairs. Its inference procedure does *not* call the coded role-path oracle. The oracle is a separate, explicit truth-generator/control only.

Three newly frozen disjoint seed blocks `63400–63415`, `63432–63447`, `63464–63479` generate **144 counterfactual public DEV pairs**. Pairs preserve identical untyped edges and query; exactly one edge's role label changes. The first two blocks (96 pairs) are fitted; the last (48 pairs) is used for a **public diagnostic**, not a protected, first-use or independent holdout. A deliberately simple four-step directed chain is surrounded by disjoint distractors; this construction is not a representative test of difficult general-purpose variable binding or novel relation structures.

Frozen controls are independently trained, parameter-count-matched role-blind recurrence, query-role permutation ablation, always-yes shortcut, and a coded exact typed-role oracle. Node renaming agreement and performance by role family are additional diagnostics. Full controls are required even when the learned candidate fails. Development-only thresholds are ≥75% paired correct, ≥15-point improvement versus the role-blind control and ≥60% minimum role family. **Passing these thresholds does not qualify independent science.**

## Evidence, operations and boundaries

`nativeevidence/f102_yggdrasil_public_roles.py` is fully offline, deterministic CPU training. Adversarial tests in `test_f102_yggdrasil_public_roles.py` reject old seed reuse, missing or altered controls, inflated budgets, post-result threshold changes, unexpected scientific authority, coded-oracle inference, unbounded re-fitting, and source SHA drift.

The existing six-hour FORGE synthetic cycle now runs F102 on both Ubuntu and Windows alongside F99/F100/F101, emitting a checkout-bound JSON proof and SHA-256 manifest. No new GitHub scheduler, FSA, Cloudflare deployment, CKB-plane connection, external LLM, Codex credential or Work scheduled task is needed.

The F102 result is not a new Yggdrasil protected experiment; the Yggdrasil research repository is unchanged. No accepted refs, scientific first-use, model-driven research-policy optimization or autonomous GPT inference is granted.

**Next meaningful research direction:** Test the distinct Y100-C2 learned variable-slot binding mechanism and W100-C2 learned active observation-value mechanism under their own frozen public-development designs. Their future public-development scores cannot be treated as genuine unseen scientific generalization.

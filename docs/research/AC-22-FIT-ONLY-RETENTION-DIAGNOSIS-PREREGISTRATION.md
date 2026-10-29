# AC-22 — Frozen FIT-only local-retention mechanism diagnosis

**Status: preregistered development-only negative-mechanism investigation.** This specification is committed before implementation, and it never authorizes source-first-use, on-policy evaluation, native adoption or DEV-based selection.

## Parent custody and hypothesis

Exact parent AC-21 runnable `693a8c9e3c7df53a3ba9a48b9a3fce9478c5c1d6` independently qualified both OS: [workflow #40834938475](https://github.com/spoonman136668-ai/FORGE/actions/runs/40834938475). Parent initial frozen `8 FIT/4 DEV` source facts: local candidate Brier `0.26488805208875116` on 4 DEV, fully informed logistic `0.1667871159584429`. Parent candidate local retention gate logits after 192 FIT updates `[0.23383985555119507,0.17342094905434616]`. Source is exact Causal-Gymnasium DTR commit `c94e9a4cd3641588b6b8507e71ccee5c27032bdf`, historical Ygg original source unchanged.

Hypothesis: weak local gate amplitudes (sigmoid around 0.55), rather than loss of historical public information after two hops, may slow supervised fitting through attenuated history feature gradients. This is a falsifiable mechanism hypothesis, **not a claim that selecting a higher gate value based on previous DEV would be valid**. Existing DEV already consumed; AC-22 will not access or rescore it.

## Allowed data and experiment

Retrieve the *previously authenticated original AC-15 public FIT* JSON only, from frozen AC-18 GitHub Actions run `40797373953`, verify platform-specific raw SHA256 (Linux `68508db981776033d403094f237c17dbbfbadf822ac9eca011feb05d50cba286`; Windows `071512caf92b82d8b3ed619d79d7741447be72bde29ae9b1b64fd42de2e39077`) and standard original AC-15 schema/information/seed contracts. The 8 FIT records form eight **fixed single-left-out diagnostic folds**: 7 episodes train, 1 remaining FIT episode scored per fold. These are **FIT-only diagnostic leave-one-out scores, not a new clean DEV/holdout or scientific proof**, because parent investigation has already observed DEV. No DEV records are opened; no source reset/do/import and no new source interactions. Reuse the existing fixed 24 chronological passes and learning rates; do **not** optimize or select candidates against prior DEV.

Compare all predeclared models on each of 8 folds, always initializing fresh and training 24 passes on same 7 FIT records:
1. **ac21_learned_local_gates**: unchanged genuine external AC-21 eight-cell/local-retention candidate (10 trained parameters: 8 head + 2 gate logits).
2. **fixed_half_local_gates**: identical two-hop signal transport and eight-head training, but gates frozen exactly at initial 0.0 logit (sigmoid 0.5); 8 trainable parameters. Control for incremental gate plasticity under same attenuated features.
3. **fixed_near_unit_local_gates**: identical source-local packet exchange and eight-head training, gates fixed at `+5.0` logit (sigmoid ~0.9933); **a preregistered diagnostic upper-bound intervention only**, not a trained or selected replacement; 8 trainable parameters.
4. **original_full_history_logistic**: original AC-21 conventional directly read full history, fixed 8 coefficients, 24 passes; it does not incur two-hop transport.
5. **matched_ten_coefficient_full_history_logistic**: a new conventional public-only logistic control with 10 genuinely trained coefficients (original eight terms plus `s1*s2` and `x1*s2`) and same FIT-pass budget, initially matching parent eight weights with two extra zeros. This matches parameter count but not necessarily computational work or inductive bias.

**Measures:** 8 FIT-only left-out predictions/model, Brier, correct-at-half, sample-level predictions and per-fold checkpoint/weight deltas, gate logit and probability changes, no DEV calls, no history-oracle fields, source custody SHA, learning updates (`7*24=168` per fold/model), actual neighbor packet deliveries (forward-only, no true recurrent learning), transport features equal direct AC-21 features on same public tuple, checkpoint restore. Benchmark resource accounting across full eight-fold diagnostic including wall nanoseconds and peak Python allocated bytes, plus model parameter count and packet delivery totals. Native learned first-use remains false.

## Critical boundaries and stop conditions

- Existing AC-21 tag-labelled public packet transport remains a handcrafted external engineering scaffold, **not a learned distributed code**. AC-22 is a diagnostic of the existing scaffold; no redesign of active Ygg model is included.
- Stage 0 receives only real public `s1,x1`, stage1 only public `s2,x2`; no `u`, original environment, `info`, source-private graph, counterfactual outcomes, or new source labels. All stage1 feature construction must replay public events sequentially, not give the terminal cell arbitrary access to all four bits.
- Any observed superiority in this reused FIT sample cannot overrule prior 4-DEV negative; no model selection is authorized without a fresh authenticated independent development sample and later separate untouched unknown-family witness.
- No source-first-use, controller/queue, original/current Wingless or Ygg source mutation, merge, production change, FORGE scientific ingestion or scientific superiority claim.
- GitHub-hosted Windows/Linux bounded source-free qualification must retain failures and cross-platform semantic outcome comparison. Negative results are legitimate.

**Pass:** reproducible source-authenticated FIT-only mechanism comparisons and locality/frozen learning tests with transparent negatives and measured resource costs. **Scientific admission remains NO-GO.**

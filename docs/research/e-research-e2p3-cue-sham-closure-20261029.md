# E Research E2-P3 — cue-specific interaction and FIT closure (2026-10-29)

**Status:** Analytical execution PASS, **associative-learning claim NOT SUPPORTED** for tested two-species Gray–Scott protocol and readout. Advisory only; no independent scientific first-use, FORGE source authentication, acceptance, or native-model promotion.

## Actual action

Executed a new independent Python analysis of E2-P2's **existing** 72 trajectories; **no new simulations** and no HOLDOUT consumed. For each of six existing FIT seeds (12001–12006) and each model (Gray–Scott, passive diffusion), the prespecified response used existing output-region concentration difference, post(t=210) − pre(t=199).

Computed the cue-specific history interaction, in the fixed observed output:
```
[(ABAB cue change - BABA cue change) -
 (ABAB sham change - BABA sham change)]
```

## Executed result

| Dynamics | FIT seeds | Median interaction | Max absolute interaction | Exact-zero comparisons |
|---|---:|---:|---:|---:|
| Gray–Scott | 6 | 0 | 0 | 6/6 |
| Passive diffusion | 6 | 0 | 0 | 6/6 |

Zero here is **exact floating-point equality for the specific readout**, not a statistical inference about unobserved behaviors. Replayed numerical data from previously recorded E2-P2 run (engineering-valid). The P2 residual-history contrast is attributable to physical state/order confounding; cue and sham produce identical measured contrasts. The current protocol cannot demonstrate an anticipatory cue-dependent association.

**Decision:** Close the narrow *E2-P1/P2/P3 two-species chemical associative-prediction test* as **NOT SUPPORTED** under existing FIT conditions. No need to consume valuable held-out splits to rescue this particular readout. This is not evidence that all reaction–diffusion systems or all emergent memory mechanisms cannot learn. An explicitly engineered third-species memory is a **distinct proposed variant**, not a success of unmodified two-species emergence.

## Custody and limits

- Script local path `/mnt/data/e_research/e2p3/analyze_e2p3.py`, SHA-256 `f58a64d777f1e19d1bc73c43586029db4617dc0fb0954e06ae4920e1721a8a66`.
- Results local path `/mnt/data/e_research/e2p3/results.json`, SHA-256 `14d804e15b8077fc3336017ecef8496c9f868af68a453d621e0b1d717e529c7d`.
- Source E2-P2 JSON digest: `f2e59f2e7b068b2fbe030a5f137d0e9cabab18eb99c599d8896ffe931c8ce1fa`.
- These original bytes are **session-local**, not stored by this advisory commit; digests alone do not constitute source custody. Research accepted status UNVERIFIED. No CI/FORGE runner tests or independent scientific review executed in this gate.
- Original response statistic was selected during FIT development; no claim of prospective frozen independent preregistration or general learning incapacity.

## Next eligible science

Consider a **separately labeled E2-M1 mechanism variant** with an independently specified slow internal chemical memory substrate and a clean matched no-memory ablation. Require prediction beyond cue/sham and passive-state controls and explicit disclosure of designed memory functionality. Before any first-use validation, establish authenticated original sources and holdout governance.

**Plain English:** When the same current cue is present or absent, the measured effect of the prior history is unchanged. That is residual chemistry, not demonstrated learning.

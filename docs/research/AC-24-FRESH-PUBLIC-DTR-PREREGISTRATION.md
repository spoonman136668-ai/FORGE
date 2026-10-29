# AC-24 — Authentic NEW public DTR development cohort: frozen protocol

**Preimplementation preregistration, development only.** This is a *new public-development dataset within the already-used DTR family*, not independent original scientific first-use, unknown-family transfer or authorized model promotion. The original upstream source is CausalAILab/Causal-Gymnasium commit `c94e9a4cd3641588b6b8507e71ccee5c27032bdf` (original `causal_gym/envs/dtr.py` blob `6af2371dce21804140ea141ccb7be14e003ba275`, source tree `fd8d8a67c1fc7fa62274dc7e12fb1e77945632f0`); the source itself must remain byte-identical, and source-specific native permissions enforced.

## New public-source episode allocation (immutable before implementation)

- **FIT** seeds **761000–761063 inclusive**, 64 independent two-step source episodes / **128 real public actions**.
- **DEV** seeds **761200–761231 inclusive**, 32 independent two-step source episodes / **64 real public actions**. Do not train, choose a learning rule, or adjust hyperparameters based on DEV. No additional test/final split claimed.
- The original AC-10/AC-15 reserved and consumed 759*** and 760*** seeds remain untouched. No original unknown-family or protected scientific cohorts. These new seeds are explicitly **public developmental**, not an independent scientific first-use witness.
- Every original episode is created by actual pinned `DTRPCH()` with `Task(learning_regime=LearningRegime.do)`, real `reset(seed=seed)`, and two original `do(lambda *_: specified_action)` calls. Predeclared **source-scripted** actions: for each phase's local index `i`, stage0 `a0=i%2`, stage1 `a1=(i//2)%2`; four action-pair allocations balanced in FIT and DEV. This is **not a model-selected policy**, and learned on-policy returns are NOT measured.
- Strict output fields per public transition: `stage, observation, action, next_observation, reward, terminated, truncated, valid_actions`. No latent source `u`, raw `info`, graph, action callback arguments, environment state, private SCM or counterfactual outcomes forwarded. Verify `ctf_do()` is permission denied, and fail closed if permissions/real source facts drift. Preserve real `next_observation=None` at terminal and reward 0/1 exactly; no fake state or reward mapping. Report attempted/completed source calls; a failing subprocess MUST declare source counts UNKNOWN, not fabricated zero.
- **No local source substitute:** all observations/labels derived from authentic imported external source, its Git commit, tree and blob verified pre-use and unmodified thereafter, and actual package imports/successful dependency receipts. Never use a synthetic DTR generator to pass acceptance.

## Frozen model comparison (one FIT training run; no DEV retuning)

All models observe the same original public `(s1,x1,s2,x2)` history; native-style signals are delivered to the site5 reward head only by actual two-stage cell state and two rounds of neighbor packets. All starting parameters and FIT update orders are fixed **before** new source use.

1. **AC-23 local pulse-reconstruction candidate**, 8 logistic head weights `W0=(.05,.08,-.03,.04,-.04,.02,.03,-.02)`, two local gate logits 0, unsupervised independent reconstruction step `0.20*p²*g*(1-g)²` for each stage0 source pulse `p`, terminal head `ETA=.06`, **24 chronological passes** on 64 FIT public episodes = **1,536 terminal reward updates**; 3,072 local-pulse update calls; frozen before DEV. Local gate updates never depend on rewards/DEV/remote values.
2. **Original AC-21 learned reward-modulated gate**, original ten-parameter predictor with exactly the same 24 FIT passes and 1,536 rewards, as a historical native-development control (not the genuine Ygg original).
3. **Predeclared AC-22 fixed near-unity `theta=+5`** eight-head local gate source-transport *diagnostic control* with 24 passes and 1,536 rewards. It is not eligible for new native selection.
4. **Original AC-21 fully informed direct eight-coefficient logistic**, same W0/LR/FIT passes and examples.
5. **AC-22 fully informed direct ten-coefficient logistic**, same 8 W0 weights plus two coefficients initially 0; same LR/FIT passes and 1,536 rewards; matched parameter count but **not FLOPs or causal architecture**.
6. **Full-public-history conventional FIT-fitted Laplace tabular** `(pos+1)/(count+2)`, plus keyed FIT-only EMA update alpha=0.5, and FIT-pooled prior. No DEV or hidden labels as inputs.

## Frozen metrics and qualification

For **all 32** DEV terminal outcomes, preserve seed, full public history, true terminal source reward, each frozen model's probability, Brier, correct-at-half, FIT support; additionally per-model train examples, updates, local gate logits and amplitudes, packet deliveries, checkpoint and cold restore, wall time and peak Python allocated memory. Include source run inputs, true source event counts, original immutable source hash, prohibited-information negatives, receipt SHA256 and cross-OS deterministic prediction parity. Operating system wall and checkpoint bytes may differ; compare semantic metrics, not byte hashes for floats.

No original model receives DEV gradient updates. Compare results honestly even if the native candidate loses. **Acceptance:** development-only execution and fair cross-OS control proof, not native scientific superiority or autonomy. A possible candidate win on this same DTR family is not unfamiliar-family transfer or scientific acceptance; require separate owner-approved external unknown family and FSA first-use before any promotion. All original active native Wingless/Ygg, FORGE F139 owner authority/controller/queue, protected main and scientific steering are read-only.

## Execution safety

Original dependency installation may be expensive and fail. Install dependencies of the **unchanged original** in isolated GitHub-hosted Windows/Linux qualification, verify exact SHA/blobs before and after, then require original source-owned interactions. No generated substitute imports or “lite” DTR. Fail closed with diagnostic provenance. No CKB-plane, paid API, new scheduler, production mutation, merge or original source alteration. Keep this PR draft until qualified; preserve all negative runs and resource accounting.

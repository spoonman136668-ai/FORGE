# Eureka F31 — Coverage-complete causal-factor contrast (DEV only)

**Prospective protocol freeze:** November 9, 2026. This document is committed as an immutable ancestor **before** F31 code, tests and score inspection. Exact F30 parent `0f979891553edb6c08da0e2426f288a5768c75a5`, tree `16cac535253333750f42ec4ad6a0138b616d2e83`. F30 classification `F30_ACTION_UNDERCOVERED`; preserve F22–F29 NO_GO. Continue only existing draft PR #1614; do not merge or integrate into live owner.

## Falsifiable question and causal mechanism

F30 showed zero `do(1)` training examples in two B-world cue cells and a 0.398-nat mean self-convolution penalty. F31 tests a fixed new *coverage-complete training intervention schedule* and **uncertainty-preserving direct-observation causal contrast**: preserve original learned P(delta | do(1)) for AA and BB rather than unnecessarily convolving with a separately estimated and then subtracted baseline. For novel AB/BA compositions, infer an action effect by the modular difference of MAP-estimated do(1) and do(0) deltas from the source bank and shift the target bank's **full original do(0) posterior** by that effect, with no second baseline convolution. This is a preregistered model hypothesis, not F29 retuning. No hard-coded true causal effect, hidden state or phase is available to learner.

## Training, transfer and observation custody

New disjoint synthetic DEV training worlds: 301=A and 303=B, each 64 real state transitions. For t=0..63, public `cue=(t/2)%4`, real `action=t%2`. Thus, for **each world** there are exactly **8 real actions at each (cue, action) cell**, including do(1) on all cues. Both A and B underlying laws are exactly the independently fixed simulator-only F28 `f28Law('A'/'B',cue)` definitions, not new post-hoc laws. Persistent hidden state `s[t+1]=(s[t]+base[cue]+action*effect[cue])%4`; offset and initial hidden state derive from public seed through `f27Mix(seed XOR 0x6d2b79f5)` and `f27Mix(seed XOR 0x4cf5ad43)` mod4 but these values are **never passed to models**. Two noisy four-way sensors use exactly F28's 90/6/4 and 80/10/10 emissions and hash salts, with separate deterministic streams. Each policy gets the same cue, prescribed action, previous two sensors, then credited next two sensors. Nobody receives clean state, true phase, future event, or hypothetical counterfactual observation.

Never-trained DEV transfer seeds, independent cold starts from the same 128 training actions per model:
- 307 balanced A→B→A→C
- 311 skewed B→A→B→D
- 313 balanced A→B→A→D
- 317 skewed B→A→B→C.

Each has four contiguous, hidden 12-decision physical-law phases, exactly 48 decisions. Simulator-only laws C/D are precisely F28's preregistered cross-component recombinations. Transfer action `t%2`; balanced cue `(t/2+seed%4)%4`; skewed cue `(t/5+seed%2)%2`, except `t%5==4` uses `(t/5+seed%4)%4`. No model sees phase label/switch time, despite scorer logging each phase. All methods run on identical real action/sensor traces. First-use 59/83 excluded.

## Frozen portfolio and model capacity

Eight independent frozen training/evaluation arms:
1. **direct-contrast (candidate):** train two cue/action/four-delta Dirichlet tables A/B from *credited* noisy sensor-difference posterior (same evidence as F28). For each cue, maintain a 4-way Bayesian weight over candidate causal components (AA, AB, BA, BB), initially uniform and updated only with actual attributed action-effect evidence. Hazard 0.05 toward uniform each credited transition. At `do(0)`, use the selected source's full P(delta|do(0)); at `do(1)`, AA/BB use **direct** P(delta|do(1)), while AB/BA use P(delta|do(0) from baseline source) shifted by MAP(do1_effect_source) - MAP(do0_effect_source) mod4. Convolve with a recurrent filtered four-state belief and update that belief on genuine subsequent sensor evidence.
2. **stationary-delta:** F27's 32-parameter recurrent Bayesian causal-delta model, retrained from scratch on exactly the new 128 real transitions, no frozen F27 training reuse.
3. **markov-bayes:** F27's trained first-order four-way transition Bayesian filter, retrained on the same trace.
4. **online-softmax:** F27's 4-pass SGD 4-way predictor with original hyperparameters, trained on the same trace.
5. **factorized-bayes:** F28's same A/B archive plus scratch Bayesian policy, retrained on the same 128 observations.
6. **direct-bank:** conventional no-cross two-bank source mixture, with identical two-bank capacity but AA/BB only, online weight updates and full original action-conditioned delta posterior.
7. **no-cross ablation:** identical candidate except AB/BA pair hypotheses disabled, AA/BB renormalized.
8. **wrong-action ablation:** identical candidate except posterior weight credit attributes `1-action` rather than actual chosen action; physical actions and sensors unchanged.

Every arm receives the same 128 observed training transitions and 48 transfer transitions, fixed actions and sensors. Baseline models are fully trained on those transitions. Model parameter counts and measured approximate work are reported; **matched compute and wall-clock economy are not established** by matched information. No hidden-law/exposure, hindsight model selection or cross-world feedback in online policies. World labels A/B in training may be used to retain archives; transfer labels are unavailable.

## Frozen scoring and stop rule

For all four transfer seeds, compute 48-way clean next-offset-state mean **NLL** (nats per transition; probability floor 1e-9) and MAP correct count, return-phase (t24..35) and novel C/D phase (t36..47) MAP counts, exact actions/sensors/predictions hash, training checkpoint SHA256, terminal SHA256, parameter/work counts. The clean target is scorer-only. Pretraining coverage table must equal **8 observations per (A/B,cue,action)**. Independently cold restore at training boundary and require byte-identical predictions/scores/terminal model versus uninterrupted warm continuation. Negative controls reject unknown seeds, first-use, corrupted/reordered checkpoints and forged passing scientific claims.

Declare `F31_DEV_SIGNAL_UNVERIFIED` **only if** all four worlds have candidate NLL **at least 0.05 lower** than the strongest of five independently fully trained conventional controls (models 2–6), candidate return-phase MAP at least equal to the highest conventional return, novel-phase MAP **at least +1/12** better than the highest conventional novel, and candidate NLL **at least 0.10 lower** than **both** ablations; all source/cold/negative/capacity checks pass. Otherwise `F31_DEV_NO_GO`. A ceiling, tie, partial run or failure of any arm is NO_GO. All thresholds, seeds, architecture and control selection are frozen *before* results. Never tune F31 after scoring. A synthetic DEV signal still is **not** independent scientific qualification, autonomous intelligence, RSI, first-use or deployment.

## Scope and engineering authority

Exactly three additive files: `docs/NATIVE-DISCOVERY-F31-CONTRASTIVE-COVERAGE.md`, `nativediscovery/f31_direct_contrast.go`, `nativediscovery/f31_direct_contrast_test.go`. Keep F30/F29 and all earlier negatives unchanged; commit protocol separately from code/scores then do one optimistic-CAS draft branch update. No CKB-plane, first-use, scientific/owner activation, GitHub workflow edits, G141 timeout edits, new runner, controller, schedule, queue, paid API, other research lane changes, merge or main mutation. Local isolated Go checks DEV only. Exact-head original **full eight-job Linux/Windows regression** and frozen F4 two-platform evaluator are separate mandatory engineering gates.

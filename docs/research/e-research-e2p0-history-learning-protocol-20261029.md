# E Research E2-P0 — preregistered chemical-history learning challenge

**Date:** 2026-10-29  
**Status:** Design/preregistration candidate; **NOT run, NOT scientifically accepted**.  
**Relationship:** Supersedes no E1 empirical result. E1-C4 closed claims of adaptive self-maintenance *for the tested system* as NOT SUPPORTED. E2 tests a different, prospective proposition.  
**Location:** Documentation-only draft FORGE PR; no controller, F139 policy, owner/witness, model weights, live research selection, or queue changes.

## Question and falsifiable hypothesis

Can local reaction–diffusion dynamics express **history-dependent prediction** of an omitted future environmental signal beyond state persistence, stimulus artifacts and simpler explicit-memory controls?

- **Primary H1:** At a fixed probe time, the same current public stimulus produces an objectively measurable anticipatory response that differs depending on the earlier cue–outcome association, and predicts the held-out outcome better than shuffled-label, exposure-only, untrained and no-memory controls.
- **Null H0:** All apparent anticipation is explained by residual cue concentration, passive relaxation, phase dynamics, stochastic stimulus history, evaluator leakage or controlled explicit memory.
- **Do not interpret** visually persistent patterns, recovery, fixed input-output discrimination, or evolution-only adaptation as within-individual learning.

## Candidate physical system and numerical admissibility

64×64 periodic two-species Gray–Scott grid with fixed, source-frozen feed/kill and diffusion coefficients; dt=0.25 nominal, or a finer convergence-verified dt if required before freeze. No post-step concentration clipping or privileged pattern-recognition rules. Any added slow internal chemical species, writable scalar or learned parameter constitutes a **separate mechanism variant**, not implicit evidence that the unmodified two-species system learned. Fix the perturbation injection and removal physics explicitly; stimulus amplitudes must preserve nonnegative concentration. Abort and preserve invalid trajectories, never silently repair data.

Before science: demonstrate physical-time equivalence across dt, finite/nonnegative intermediate-substep states, deterministic replay, cue-clearance, and no post-reset retained information except explicitly declared internal state. The E1-C4 fixed-random anomalous sensitivity precludes using terminal-pattern convergence as a proof of functional memory.

## Prospectively defined task

**Two-context delayed association with counterbalancing.** Present cue A or B at one of two spatial input ports, followed after delay D by an environmental consequence at a separate output port. Association mapping is randomized across independent organism histories, then held stable within each lifetime; in some sessions reverse it after FIT training. Observe a preconsequence **anticipatory output** in a predeclared output region from concentration change during a probe interval where the consequence is absent. Do not provide a direct stimulus that encodes the requested outcome at probe time.

For every paired test, construct a counterfactual twin with the **same** present cue, probe environment, random streams and time, but an alternate earlier association history. Match cumulative cue exposure, outcome exposure, dose, presentation order and delay where feasible. Include **cue-only probes** after washout. Preregister exactly how the output-region statistic and direction are chosen from FIT; no tuning or sign selection using HOLDOUT.

**Primary metric:** balanced, cross-validated ability to predict the actually paired consequence from the prospective preregistered anticipatory output, assessed on independent held-out worlds/assignments against H0 baselines. Report both accuracy and proper scoring rule where applicable, per-world and per-seed; no winner by post-hoc metric switching. Include a direct paired history contrast at equal current input. Include output magnitude and uncertainty intervals and run-level resource cost.

## Controls (same observable information and interaction budgets)

1. Untrained, no pairing history: identical present probe.
2. Shuffled pairing/label history with matched cue/outcome counts.
3. History-state reset before probe (check whether retained internal state is necessary).
4. Residual-state passive diffusion and fixed-random chemistry, same stimuli, geometry and budget.
5. Explicit small finite-state / tabular associative memory; disclose capacity and update rule, no privileged test mapping.
6. Purely reactive cue-to-output lookup without memory.
7. Evolutionary-only fixed-parameter model (if population optimization is introduced) trained on the same FIT data, with no within-lifetime updates.
8. No-consequence and delayed-consequence sham probes to detect direct leakage.

**Critical negative test:** randomize the history mapping while preserving final observable cue and physical state as much as possible. If test labels can be read from injection schedule, temperature/position, time indices, residual cue particles, or test seed, the experiment is INVALID rather than PASS.

## Frozen partitions and first-use custody

- **FIT:** 12 existing developmental seeds from E1 (12000–12011), for debugging and coefficient selection only; none may be labeled HOLDOUT. The E1 seeded variants are not independent confirmation.
- **VAL:** A new, source-frozen disjoint seed cohort and mapping permutations, created only when the exact code/protocol is immutable. May tune or decide whether to proceed; do not merge outcomes with final test.
- **HOLDOUT:** Independently generated unfamiliar mappings, spatial rotations, cue delays, consequence-port layouts and at least one unfamiliar challenge family. Must be independently sealed/authenticated before first use and consumed once under FORGE's applicable scientific first-use controls; **not created, disclosed or consumed by this draft**.
- Record original seed-generation mechanism, environment and outcome generator source SHA, FIT/VAL/HOLDOUT manifests and cryptographic hashes, and both failures and successes. Do not claim independence if one PR or author has inspected all splits.

## Decision rule

**E2-P0 is a design gate only; no scientific PASS.** Before FIT execute, precommit response statistic, washout criterion, valid-run criterion, negative-state policy, interaction count, computational budget and sample-size/power plan. Default family-wise false-positive control for all prespecified primary contrasts: Holm-adjusted alpha 0.05, with 95% confidence intervals clustered by environment/history family. This is a proposal until an exact immutable protocol and sample plan are sealed.

- **Support for experience dependence:** positive preregistered paired-history contrast across novel development/validation histories, not explained by residual cue/pattern timing, and competitive against no-learning/reactive controls.
- **Support for useful learning:** positive held-out predictive performance and retention across delay/cold restart; any claims require independently authenticated scientific approval.
- **Falsify H1 at available budget:** preregistered meaningful effect bound fails against shuffled/reset/passive baselines or effects disappear at matched washout; report null/inconclusive if not statistically resolved.
- **Never claim architecture-independent cognition** simply from an explicit memory species; report mechanism-specific capacity and its cost.

## Required engineering and scientific evidence

Immutable original source and raw results (including stderr/exit codes), per-seed trials/measurements, all candidate-control identities, exact dt/physics parameters, 24h-style continuous? **No**: use bounded runs only; CPU seconds, maximum resident RAM, wall time, reproducible deterministic environment, source SHA/tree, toolchain and environment provenance. Separate ordinary CI PASS from science PASS and holdout-first-use clearance. No paid API or controller/queue/scheduler implementation.

## Immediate next execution-eligible step

**E2-P1 FIT pilot** in a non-repository isolated environment: implement the stimulus/washout/probe physics and a minimal paired-history readout, validate all sham/reset controls on existing FIT seeds, and measure whether direct history decoding is even possible. If no evidence, retain the negative and test a *separately named* third-species internal-memory variant; don't retroactively call it the original two-species system.

**Plain English:** Next we test whether chemical states can learn that one cue predicts an event, and whether the same present cue produces a different response after different histories. We will reject apparent memory if it is just leftover chemical stimulus, time dependence, or a hidden answer key.

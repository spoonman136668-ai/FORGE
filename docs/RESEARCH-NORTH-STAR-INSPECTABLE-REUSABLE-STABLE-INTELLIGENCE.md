# Wingless + Yggdrasil Research North Star
## Inspectable, reusable, stable learned structure under rigorous generalization tests

**Status:** Research strategy and experimental design priorities, **not** a scientific result, activated optimizer, merge approval, new worker, or change to any frozen F99–F116 experimental protocol. This is FORGE-native research governance: GitHub Actions for reproducible experiments, independent Wingless/Yggdrasil architecture development, and Mind Palace as the existing *read-only advisory* research-knowledge bridge. No CKB-plane connection or Codex default runner.

### Central claim to test

**Learning a local correlation is not equivalent to learning a reusable causal relationship or developmental rule.** A viable alternative architecture must explain its decisions, reuse learned structure on unseen task families, preserve stable learning over repeated cycles, and match or beat strong ordinary neural and symbolic systems for at least some comparable quality/resource frontier. Neither lower parameter count nor excellent scores on constructor-generated examples alone establishes the claim.

Recent negative evidence is deliberately preserved:

- Wingless F112 achieved excellent source lookup, but query depth accidentally revealed the requested source. F113 PR #408 removed that shortcut; a six-weight learned engine reached 144/144, **but identical engineered features with fixed weights also reached 144/144**. This is *retrieval competence, not evidence of learned structure*.
- F114–F115 source ambiguity and information acquisition were solved by explicit symbolic certificates or a hard-coded charged query; valuable design evidence, but not transferable learned knowledge.
- F116 PR #414 measures TRAIN-only learned channel usefulness vs the **same-data empirical Bayesian estimator**, empty and misleading signals and variable costs. Its eight-logit decision trace is a transparent *value-of-information controller*, **not** a causal explanation of an entire memory system.
- Yggdrasil's learned memory-selection and near-miss variable-binding results must be evaluated against fixed retention/strict relation controls. A negative can come from insufficient information, representation mismatch, a weak objective, optimization failure, dataset shortcuts, or source contamination. **Do not assign “overfitting” or “unstable gradients” as causes without diagnosis.**

## A. Make causal attribution part of the substrate

Each architecture should produce a stable, versioned **decision provenance record**, under bounded resource cost and without leaking protected answers or unrelated private context:

`decision_id -> immutable source identity -> relevant memory cells / graph edges -> relation and variable bindings -> active module/role -> state transitions -> action / answer -> confidence or abstention`.

For each answer, include explicit **what was used, when, why eligible, and what would change if it were unavailable**. A score/attention heatmap alone is a correlation, not causal attribution.

Predeclare causal interventions, not post hoc examples:

1. Remove a retrieved relation edge, replace its role, or scramble endpoint identity. Hold all remaining data and resource limits fixed; record the prediction delta.
2. Mask one memory cell, one cell class, one module, or its learned update rule; record effects on new/familiar tasks and developmental persistence.
3. Replace a learned weight or gate with a frozen neutral or randomized counterpart under the **same inference information**.
4. Perform reversible counterfactual swaps of relationship composition (e.g., `A→B` and `B→C` vs role-reversed links), testing whether the reported evidence graph tracks the true dependency.
5. Preserve **negative** and untraceable outputs and fail closed if required provenance is missing.

Store ablation vectors and their costs as first-class research artifacts, not only troubleshooting logs. Do not use an internal trace as an independent external custody attestation.

## B. Optimize reusable structure instead of storing new answers

Primary test: **Can a frozen learned rule or compact representation solve a genuinely new relation family without adding a new lookup pattern for every case?**

Hold training source families fixed; evaluate on unseen symbol systems, role labels, graph topology, query grammar, and source identities. Include:
- Role renaming, reversible and noncommutative relation composition, variable reuse and recombination.
- Four-hop to six/eight/twelve-hop transfers with controlled distraction, branch collisions, anti-shortcut twins, and scrambled presentation order.
- New source-ID alphabets and independently generated graphs, not only new PRNG seeds following the identical grammar.
- Few-shot/zero-update transfer **and** bounded adaptation curves measured separately; track new bits stored per new task.
- Catastrophic interference and preservation of old capabilities after exposure to each new family.

A learned relation representation only earns a **transfer** claim if it beats a fixed untrained same-feature policy, a full-information symbolic algorithm when applicable, and a memorizing source-ID lookup **under explicitly comparable observation access**. Matching a perfect symbolic control can be a valid useful result but not a learned-superiority result.

## C. Isolate learning stability, especially in Yggdrasil

Run the **same frozen learning task** through a controlled intervention matrix, varying **one** stability feature at a time: gradient clipping (with logged unclipped/clipped norms), normalization, residual state updates, plastic-state learning rates, bounded developmental depth, and update scheduling. Declare each mechanism's exact active/training graph and representation capacity.

For every cell of the matrix record:
- Per-step gradient and update norms; NaN/Inf frequency; saturated gates; state magnitude and convergence/oscillation.
- Train, validation and never-tuned GUARD loss trajectories **without repeated GUARD model selection**.
- Repeated learning-cycle retention, recovery, new-task interference, run-to-run variance and resource budget.
- Cold starts and multiple genuinely independent initialization seeds, not one lucky run.
- Distinguish divergence, vanishing signals and oversensitivity from **irreducible missing information** using separate information-oracle controls.

Control depth/capacity changes: if stability improves only because effective compute or memory increases, account for that separately. Negative training outcomes are part of the accepted engineering evidence, not reasons to move thresholds.

## D. Prove out-of-distribution and resource-constrained generalization

No promotion from synthetic rehearsal to accepted scientific progress without an appropriately frozen independent source/first-use design. Within publicly synthetic development, use disjoint source names, **generator families**, latent graph origins, relationship roles, and formal task templates.

Required challenge axes: novel roles, changed relationships, longer reasoning, compositional depth, variable binding, misleading or missing observations, memory pressure, bounded processing, and repeated online adaptation. Score each separately; report worst-family performance and negative transfer, not just pooled accuracy. Preserve answer-blind baselines and independent provenance. Frozen GUARD must not become feedback for a new policy on the same cases.

Record **performance vs training examples, parameters, inference steps, wall time, bytes of active memory, retained new bits per task, energy/compute proxy when available, and query cost**. A claimed efficiency improvement needs a Pareto-frontier comparison, not merely fewer weights.

## E. Compare both architectures fairly with conventional systems

Select conventional neural baselines **before test**: appropriate small MLP, GRU/LSTM, Transformer and, for graph-relational tasks, a message-passing GNN. Use a separate symbolic graph solver, nearest-neighbor/memorization and fixed-retention control where relevant.

Match or sweep:
- Training examples and task families, information channels, allowed memory, updates, wall time and inference compute.
- Parameter counts *and* resource-envelope-equivalent variants; no one-sided best-effort tuning.
- OOD GUARD identities and task difficulty; same negative examples, outcome scoring and evaluation time.
- Multiple random seeds and confidence intervals; explicit pareto dominance or tradeoffs rather than a single leaderboard.

Wingless and Yggdrasil need not become neural networks. We are comparing their native learning mechanisms against neural models, not asserting all are mathematically the same architecture. Model-free/symbolic controls remain essential.

## F. Mechanism-specific research hypotheses

**Wingless.** Hypothesis: relational composition can support unfamiliar source and query structures without memorized source IDs. Compare structural relation updates, trainable generic composition and attention-based retrieval under strong edit-distance, exact-lookup and full-information algorithmic controls. Introduce controlled role swaps and previously unseen relation compositions; obtain traceable graph-edge counterfactuals.

**Yggdrasil.** Hypothesis: developmental memory/plasticity rules encode information with *future causal value*, not only recent local predictiveness. Train candidate retention on **downstream counterfactual utility** across delayed multi-step consequences, not only immediate reconstruction or next-step reward. Compare fixed recency/importance rules; ablate memory slots, learned update gates, state norm/clipping and developmental depth. Verify whether stored structures transfer to longer and structurally altered chains. Track identity-binding correctness and memory-byte efficiency.

**FORGE.** Treat optimizer policies as *scientific hypotheses*: frozen strategy, authentic evidence intake, paired independent controls, honest null outcomes and bounded mutation authority. Keep query-value learned calibration (F116) a small subexperiment, not a proxy for general autonomous intelligence. Mind Palace may provide source-linked history through the existing read-only integration, but does not substitute for experiment proof.

## G. A falsifiable progression (proposal, not authorization)

1. **Interpretability contract**: define immutable decision provenance and deterministic causal edge/memory/module ablation interfaces; test fabricated and missing provenance fail-closed. Source-only qualification first.
2. **Stability intervention study**: independently preregister one Yggdrasil repeated-learning task, baseline and orthogonal clip/norm/residual/depth interventions with resource-matched variants. Freeze TRAIN/VALIDATION/GUARD identities before code or outcome access.
3. **Structural transfer comparison**: independently preregister novel multi-hop/role-binding tasks and matched Wingless/Yggdrasil vs neural+symbolic controls. Evaluate frozen learned rules on truly new generators and longer chains.
4. **Continuous scientific improvement**: only after verified provenance and independent first use, test repeated fresh experiments and policy adaptation. No accepted original may be manufactured out of synthetic or retrospective cases.

For *each* study, specify source-disjoint training and evaluation, before-code prereg, predeclared threshold/uncertainty interval, information-equivalent baselines, model/update budget, signed vs unsigned custody boundary, machine-readable causal trace and negative-result retention. A **failed** superiority test can still be a successful experiment. No automatic PR merge or accepted-ref mutation follows from passing a source-only regression.

**North-star decision rule:** prefer architectures that deliver inspectable, causally supported and reusable relationships with stable learning and independently demonstrated OOD transfer at a competitive resource frontier. Do **not** confuse low memory use, a deterministic certificate, an eight-logit calibration controller or perfect synthetic accuracy with that end state.

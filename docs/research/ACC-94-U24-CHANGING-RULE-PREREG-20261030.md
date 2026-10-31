# ACC-94 — U24 Changing-Rule Local Adaptation (pre-execution freeze)

Status: **PREPARE_ONLY / NOT EXECUTED / NOT SCIENTIFICALLY ACCEPTED**. This is an independent unconventional-method research protocol. It does not modify or qualify native Wingless/Yggdrasil, GPU ACC, F139, or protected main.

## Source custody and non-duplication
- Pinned FORGE base: `0810ecf3df6378bcbfe5239d30df836b7e12a602`.
- Original AC-06 source: `research/ac06_sourcefree/restricted.py`, Git blob `19c5ce8f485900f06adaffe97f998c83c78aab4c`.
- Original AC-08 source: `research/ac07_sourcefree/ac08_portfolio.py`, Git blob `5126c860771fb024ccfc14c3f7ee8925edf29787`.
- ACC-73 selection: draft PR #1317; its evidence classification remains advisory, 19 historical methods not requalified.
- Original U24 demonstrated eight-entry table reconstruction with a same-rule longer lattice. This is not unfamiliar rule learning and is not native distributed cognition. Do not repeat this demonstration as a positive result.
- The native ITD-02 Wingless/Yggdrasil research lanes and their experiments remain separate. No original-world or protected holdout access.

## Prospective hypotheses
H0: At matched information and resources, distributed local-plasticity does not improve post-switch prediction or retention over a well-fitted exact 8-entry counting table.
H1: A bounded distributed local learner improves post-switch predictive error **and** cost-normalized recovery over that exact-table control on independently held-out rule-switch sequences.
H2: Any apparent benefit disappears when access to rule-switch cues and the exact observation budget is equalized.

### Identifiability limit
An arbitrary elementary binary cellular-automaton rule maps just eight three-bit neighborhoods to eight output bits. A counted lookup table is an information-efficient exact reference once all neighborhoods have been observed. A distributed learner is not expected to beat a fully observed, noiseless table on static rules. Therefore: positive claims MUST be restricted to predeclared partial-observation/switch regimes, and FULL-OBSERVATION controls MUST expose trivial lookup parity. No claim of general causal intelligence or first-use follows.

## Source-free deterministic development design (no protected data)
- Periodic 1-D binary lattice; neighborhood width three, synchronous update, no hidden global oracle supplied to any learner.
- Rule IDs (Wolfram local truth tables): FIT: 90,110,30,184; DEV: 54,150; RESERVED TEST: 22,126. RESERVED TEST rules must not be read for tuning or used until a separate frozen, authorized implementation and evaluation boundary. Different rule IDs are **not** independent environmental provenance; external unfamiliar-source transfer remains UNVERIFIED.
- FIT seeds 601,607,613,617; DEV seeds 701,709; RESERVED TEST seeds 809,811. Split seed sets are disjoint; implementation must derive independent streams with SHA256(domain || rule || seed || episode) and store trace digests. Explicitly reject accidental collisions or source/split contamination.
- Train sequences of lengths 25,63 and development evaluation length 127; a longer lattice alone is not considered transfer.
- Two regimes: stationary/noiseless full-observation (negative control) and partial-observation changing-rule episodes. A change occurs after 128 update steps, previously concealed to every learner; fixed 64-step adaptation window. Each learner receives exactly the same set of visible per-cell transitions (25% per step chosen without learner feedback) and equal rule-change cues (none).
- Evaluate each learner using the same held-out query neighborhoods, never its own chosen queries. Include 128-step pre-switch, 64-step recovery, and 128-step post-switch segments. No trainer sees reserved TEST outcomes for method selection.
- Cold restart: serialize after the first 64 post-switch updates, restore into a fresh process, and check exact continuation at matched observation counts; a blank-restart ablation is required.

## Frozen arms and equal-information controls
A: distributed local-only update with no globally coordinated gradient, parameter copy, or rule identity; candidate's communication, state bytes, serialization and CPU are charged.
B: eight-entry Beta-Bernoulli/majority counting table using exactly the same visible transitions, with reset and non-reset variants; use the best preregistered variant chosen on FIT/DEV only.
C: exponentially weighted eight-entry online counts with a DEV-frozen forgetting rate from [0.02,0.1,0.3,0.7].
D: fitted 16-state recurrent predictor on identical visible transitions and equal or larger parameter/storage budget, fully charged including fitting and tuning.
E: full-observation oracle table, clearly labeled *information-unmatched upper bound*, never used as a fair comparator.
No leakage via rule ID, full lattice state, future observations, neighbor truth table, or evaluator labels. All arms must process equal observations in identical order. If exact interface parity is not auditable: INVALID, not PASS.

## Measurements and decisions
Primary: matched-question post-switch bit prediction accuracy and cumulative 64-step adaptation error (lower is better). Secondary: first recovery step reaching 90% post-switch correctness, cold-restore exact continuation, worst-rule accuracy, communication bytes, peak RSS, process CPU seconds, wall seconds, fit cost, energy if physically measured, and serialized state bytes.
Paired comparisons at all DEV seeds and rule transitions; keep per-seed raw predictions, no selective reporting. Any missing process or communication costs is RESOURCE_UNVERIFIED.
**Candidate positive threshold, DEV screen only:** at least +0.05 absolute mean post-switch accuracy over the strongest fair baseline AND at least 10% lower cumulative adaptation error, no individual rule worse by more than 0.02, exact cold-restart continuation, and no more than 1.10x total CPU, peak RSS, or state+communication bytes relative to that strongest fair baseline. All conjunctive, no post-outcome threshold adjustments.
If the baseline reaches exact accuracy across all matched questions, report SATURATED_NO_ADVANTAGE. If any resource, split, identity, or output parity is unverified, report BLOCKED/INVALID rather than PASS.
Reserved TEST is sealed for a separately authorized prospective qualification and does not become a second DEV set.

## Execution and acceptance boundaries
This commit freezes **only the proposal**, not runnable experiment code, dataset contents, first-use, or acceptance. Before execution, independently qualify runner authority and derive immutable input/manifest hashes, exact dependency/runtime identities, clean checkout, implementation tests, negatives and complete resource instrumentation. A new execution implementation must be qualified on the frozen FIT/DEV protocol without modifying this prereg after reading results. Required final integration/full regression and independent science witness remain separate.
No paid APIs, no new controller, no queue dispatch, no protected-main mutation, no native-model integration or promotion.

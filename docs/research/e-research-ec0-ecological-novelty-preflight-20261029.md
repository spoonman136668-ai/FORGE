# E Research E-C0 — ecological novelty research preflight (2026-10-29)

**Status:** Protocol drafted, NOT an executed ecological experiment, scientific outcome UNVERIFIED. **Advisory-only** in existing draft PR #1194. No FORGE owner/controller/queue/first-use/model selection changes.

## Hypothesis

At equal observations, energy and interaction budgets, evolving computational organisms in changing local ecologies acquire *functional behavior that transfers* to unfamiliar resource layouts better than static-environment evolution, random selection, fixed policies and local reactive heuristics. Increased lineage diversity or appearance alone is NOT intelligence.

## Frozen candidate world for E-C1 FIT

- 24×24 periodic tile world; renewable bounded 0..1 local resources; 12 organisms, each state (x,y,heading,energy,age) and a four-weight local sensory genome with action threshold.
- Actions: left, right, forward, harvest. Observations: local and adjacent resources only, no global map/answer oracle.
- Example proposed energy accounting: base cost 0.025 per step, movement surcharge 0.015, harvest energy capped by actual local resources, offspring receives half of parent energy; mutation bounded to declared genome parameters. These numbers are **proposed, not yet calibrated or qualified**.
- Dynamic ecology: local resource patches change by independently seeded fixed Markov schedule; no environment response to hidden success labels. Static control freezes patch transitions. All controls share frozen world generator and budgets.

## Independent matched controls

1. Evolvable organisms + changing ecology.
2. Same mutation/selection + static ecology.
3. Same changing ecology + random-parent selection.
4. Non-evolving fixed policy + changing ecology.
5. Resource-greedy reactive policy + same observable input and interactions.
6. Shuffled-history ecology with transition frequencies preserved.

Ensure reproduction, interaction and total energy supply are accounted consistently across controls; if a comparator lacks evolutionary reproduction, log effective population-time and organism-step budgets rather than misleading equalities.

## Measurements and falsification

**Primary:** survival duration and energy-constrained harvesting efficiency in previously unseen resource geometry, without further evolutionary selection. Report matched per-seed delta versus every control and uncertainty; score withheld transfer separately from development. **Secondary:** lineage depth, action novelty from prospectively frozen behavioral descriptors, retained function after patch relocation, resource/CPU/RAM/wall consumption, and extinction/invalid-run rates.

Falsify the proposed advantage if the evolving changing-ecology arm fails to surpass appropriately matched random-selection and reactive controls on functional unfamiliar transfer. If only a novelty descriptor improves, classify **novelty only**, not intelligence. Do not infer within-lifetime memory or learning from evolution across generations.

## Splits and validation

- **FIT-only prospective engineering seeds:** 31000–31011, not holdout.
- Disjoint validation seeds, source-frozen unfamiliar geometry families, and independently sealed HOLDOUT first-use require their existing authority and independent custody; not created, inspected or consumed here.
- Before science: deterministic replay; per-step energy accounting including metabolism/replenishment losses; no negative resources/energies or illegal movement; identical observable information and bounded interaction budgets; seed/source/toolchain provenance; all positive, negative and invalid terminal artifacts.
- Scientific first-use and integration into FORGE/ Wingless/ Yggdrasil remain **UNVERIFIED and NOT AUTHORIZED by this protocol**.

## Gate disposition

**E-C0 design PASS; E-C1 execution NOT RUN.** Next E-C1: build minimal isolated world with tests for accounting/parity and run a bounded FIT-only control comparison. Do not create a competing scheduler or modify FORGE autonomy.

Plain English: we will test whether organisms evolving in a changing world acquire useful behaviors that survive a *new kind* of world; greater diversity alone does not count.

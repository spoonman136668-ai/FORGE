# E Research E-D12 — consequential intervention model, FIT diagnostic (2026-10-29)

**Engineering PASS. Intervention-outcome knowledge demonstrably changes behavior. Advantage over a conventional contextual learner NOT SUPPORTED. Scientific first-use UNVERIFIED.** Documentation-only research advisory; no FORGE owner, autonomy, controller, queue, native model, research selection or scientific admission change.

## Executed experimental design
Standalone Python executable runs a deterministic two-gate causal choice environment. Each trial presents two physically sealed chambers and one material unit. One selected intervention removes one barrier, consumes 4 energy and the only material unit, and enables resource harvest of 10 **only if** the opened gate leads to the stocked chamber. Neither action earns intrinsic building reward. Public observation has binary environment cue and gate orientation (two bits). Neither controller receives the target chamber identity. The environment generator sets a fixed but undisclosed cue/orientation-to-food relation. A randomized matched-cost training intervention reveals only its own outcome (harvest 10 or 0). Every context-action combination was observed at least 20 times, so the agent can learn the direct mapping.

**Train:** 240 development seeds 61000–61239, one observed intervention per seed. **Evaluate:** 120 different deterministic development seeds 62000–62119, five policies each = **600** evaluation trajectories; no training on evaluation seeds. This is NOT an independently sealed or externally sourced holdout; world design is deliberately simple, the relation is stable, and no data-source provenance or environment-family transfer is claimed.

| Policy | Successful / 120 | Mean net harvest minus energy spend |
|---|---:|---:|
| Empirical learned context/action consequence table | 120 | 6 |
| Scrambled learned consequence-to-action table | 0 | -4 |
| Reset to no retained table, random equal choice | 60 | 1 |
| Standard empirical contextual bandit baseline | 120 | 6 |
| Fixed first-gate choice | 61 | 1.0833 |

Each action costs 4 energy and one material unit; net reward = harvested units minus energy cost, a simplified objective not evidence of organism fitness. Per-step energy and material accounting invariants PASS, exact full seeded evaluation replay PASS. Local experiment ~0.019 s. No multi-step movement, model-based planning, ecological reproduction, new structural world transfer, native Wingless/Yggdrasil learning or neural/cell mechanism tested.

**Interpretation:** The learned table is *decision-relevant* because scrambling it reverses correct choice and resetting it removes the advantage. This is a positive intervention-consequence sensitivity check missing from E-D11. But the strong conventional contextual learner is identical and solves all contexts. Therefore this gate does not support *novel causal intelligence* or superiority to controls; the world is solvable by finite lookup. No statistical population inference or independent replication.

## Local original-byte identity

`/mnt/data/e_research/ed12/run_ed12.py` SHA-256 `59f8866a267b5f465259143c90eae5f2ec0fd78b4982fd5243ef229971dae501`
`/mnt/data/e_research/ed12/results.json` SHA-256 `803e91857c574c1a84d090cf104d2932a817ba769002145efbca97b16055e2ff`

The original source and complete raw JSON are local, not committed to this documentation-only branch. Their digests do not independently authenticate FORGE source custody or scientific first-use.

## Decision / E-D13
**E-D12 sensitivity PASS; advantage beyond conventional learning UNVERIFIED.** Next test should move from static binary lookup to a multistep hidden-state physical intervention with partial observability and delayed causal consequences. Compare recurrent/history-dependent conventional Bayes or model-based controls, exact action-replay memory, reset/shuffled transition models and resource costs, with identical interaction budgets and no privileged state. Define a first-use source/holdout protocol before advancing scientific evidence into FORGE.

**Plain English:** When the agent learns which intervention works, it chooses correctly. That matters, unlike the earlier experiment. But a standard learning method does equally well, so this is not evidence of a new intelligence mechanism.

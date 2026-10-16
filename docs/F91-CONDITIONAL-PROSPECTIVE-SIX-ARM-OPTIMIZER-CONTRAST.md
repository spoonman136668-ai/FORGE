# F91 — prospective six-arm outcome contrasts, independently sourced but never self-authorizing

**Scope:** Optimizer workstream only; F89/F90 owner-side execution and autonomy remain separate from the research-selection evaluation. No CKB-plane connection, scheduler, Cloudflare mutation or live research original.

## 1. Frozen comparison

For each Wingless/Yggdrasil lane, F89 fixes the four control policy identities plus the Dream-RSI and Shinka/Pareto policy identities. The assignment probability is exactly **1/6 for each *policy arm***, not Dream-RSI's action-level conditional probability.

F90 verifies record/signature *consistency* from source-supplied Ed25519 public keys, frozen assignment identity, claimed sequence, source hash and signed predecision. This by itself does not establish genuine early registration, ownership, first-use or completeness.

F91 consumes the F89/F90 records through `ReviewF91`, validates both lanes first, and computes **eight contrasts per lane** (Dream vs each control, Pareto vs each control). Score contrasts are *exact rational* inverse-propensity estimates:

`DifferenceIPS = 6 * (sum(candidate outcome score) - sum(control outcome score)) / N`

The same estimator applies to compute cost, which is reported separately, rather than treating a raw score improvement as compute-adjusted superiority. Keep each research lane separate; different source families must not be pooled to manufacture gains.

The design assumes outcome scores are bounded in `[0,100]`. The conditional, simultaneous 95% *familywise* Hoeffding half-width for the complete **16** planned contrasts is

`1200 * sqrt(log(16 / 0.05) / (2 * N))`.

It assumes true independent unbiased assignment, all planned original outcomes and proper preregistration. Consequently this bound is **diagnostic only until those assumptions are independently proven**. With small samples the bounds are intentionally very wide. They are not a substitute for a frozen independent causal-analysis protocol or actual confidence in a policy improvement.

## 2. External prospective source interface

An optional `F91ExternalVerifier` receives the entire F89 freeze, F90 signed outcome cohort, and separately supplied identities for the owner ledger, witness archive, preregistration archive and content-addressed cohort. F91 enforces distinct source pins and two-lane source separation.

**A source-accepting verifier is not by itself proof of independent custody.** It may be a test mock or share the producer's authority. The F91 output describes only a source claim validated by that interface. Independent externally qualified owner custody must happen outside this pure optimizer library. No records claiming authority are taken at face value.

Every possible F91 return **always leaves false**: independently qualified scientific source, genuinely witnessed pre-outcome first-use, proven randomness/completeness, scientifically established causal gain, Dream or Pareto policy promotion, ThetaEvolve accepted-result learning, science dispatch and accepted-ref mutation.

## 3. Missing results and unsafe shortcuts

- If any outcome is `MISSING`, F91 will not compute contrasts for that lane; no silent zero outcome or complete-case bias.
- If any of the six arms is unobserved, F91 will not compute contrasts for that lane.
- Reject reused witness receipts, assignment draws, cross-lane signer/source identities, improperly signed source, changed outcome bytes under an external pin, altered preregistration/slate and duplicate owner ledgers.
- Mixed, negative, invalid and indeterminate scientific outcomes remain differentiated, not converted into accepted successes.
- F90's source-only signed-cohort cap is increased from 128 to **16,384** rows per lane so a future sufficiently powered experiment is possible without breaking memory bounds; this is not permission to run one.

## 4. Authentic verification and scientific stop

The F91 GitHub-hosted workflow re-reads the **authentic F90 source-qualification run** [38960496153](https://github.com/spoonman136668-ai/FORGE/actions/runs/38960496153), pinned to `5c65ff5727fdcfedcc4f6f37bfbd2cf126a2c660`, then exercises negative/falsification tests and the complete FORGE regression on the exact F91 branch.

That authentic GitHub run only establishes **source qualification**, not authentic prospective outcomes. As of this gate, no two-lane independently witnessed, once-only, complete six-arm prospective trial has been presented. Therefore the correct scientific disposition is **NOT YET DETERMINABLE**, not a Dream-RSI/Pareto win.

**Future operational handoff:** The separately governed FORGE-native science-owner pathway must submit qualified pre-outcome registration, actual independent witness, monotonic original first-use and complete frozen-protocol outcomes. At that point the independent causal review can use the prepared F91 contrasts, then separately decide whether any promotion is scientifically justified. ThetaEvolve must remain disabled for supposed successes until the newly accepted scientific result is independently admitted.

**Workstream division:** This thread develops optimizers. FORGE Gate Advancement develops autonomous execution/authority. Mind-Palace is advisory only. There is no CKB-plane dependency.

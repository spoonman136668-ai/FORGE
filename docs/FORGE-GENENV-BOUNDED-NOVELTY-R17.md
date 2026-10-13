# FORGE R17 — bounded DGM/GenEnv-inspired novelty screening foundation

Source starting point: FORGE `c0400ca4c271d4bf3e336791de1e4aea53e5d291` (merged R16).

**Scope is source-only.** This adds a deterministic, frozen environment-mutation/novelty filter. It is neither DGM self-improving agent behavior, qualified GenEnv scientific environment generation, autonomous search, nor real evidence admission.

A frozen plan binds Wingless/Yggdrasil, exact source commit and historical training digest, original environment vector (1–16 features), level bounds, epoch, 1–16 candidate requests and no more than 64 single-step mutation operations globally. Caller-provided training records have immutable ordered identities and retain negative, mixed, invalid and consumed/indeterminate classifications. Duplicate or out-of-domain history, changed source/cohort, false training-only labels, repeated candidate vectors, capacity drift and unbudgeted operations fail closed. The novelty number is a deterministic Manhattan distance to the frozen base and archived historical vectors, **not** a claim of scientific novelty or performance. All output candidates are labeled `UNTESTED_PROPOSAL` with zero execution/acceptance/heldout flags.

Real DGM/GenEnv qualification still requires an independently authenticated historical source, a falsifiable preregistered novelty/validity benchmark, matched non-generative and diversity baselines under the **same total screening budget**, prospective heldout evaluation, preservation of failed experiments, and independent FSA custody/admission. No scientific original, live model API, scheduler, private secrets or accepted-ref mutation occurs in this change.

Qualification: exact-head Linux full Go test/race/vet/build and public isolation, native Windows full Go test/vet/build, adversarial identity/duplicate/budget/negative checks, post-merge final regression. This does not change existing CKB-plane, Wingless or Yggdrasil operations.

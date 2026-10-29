# F139 V19 — renewable research eligibility SHADOW (not activated)

**Status:** review-only, source-only, nonexecuting V19 successor feasibility. It neither changes, starts, replaces nor dispatches from the existing original F139 Windows controller. No PR merge, issue-807 policy, source release, ledger/SQLite event, remote inference, GitHub write, research first-use, or producer authority is granted.

## Exact reason this gate is necessary

Original V17 and proposed V18 call `f139/nci04_owner_free_reasoner_proposal.py`; the production free route is finite, with `MAX_LIFETIME_REQUESTS=8`, `MAX_DAILY_REQUESTS=2`, `MAX_DAILY_PER_LANE=1`, one sticky original custody event before a request, and immutable source targets from old Wingless R8 / Yggdrasil G29. `FREE_REASONER_SCOPE_ALREADY_ATTEMPTED_NO_REPLAY` is a safe terminal decision, not a provider problem. The V18 source transition and read-only steering fix alone cannot yield unattended repeated new model development.

**Do not remove these limits from V17/V18, use a clock rollover to replay old evidence, or silently change source targets.** A genuine next native training/experiment terminal result for the SAME lane must be independently authenticated before a new proposal may be eligible.

## Inert V19 shadow candidate

- Source: `f139/nci04_v19_research_renewal_shadow.py`; tests: `f139/test_nci04_v19_research_renewal_shadow.py`. Imports stdlib, no network, subprocess, Git, credentials, runner, database access, controller hook, or outside-file writes.
- Inputs are hypothetical *already verified* lane-specific terminal evidence: ticket, strictly increasing original terminal sequence, original native evidence hash, source pin, `VERIFIED` stage and chain-verified flag; historical original-attempt records must be provided in custody order. **A boolean from an arbitrary caller is never authentication.** The currently inert helper cannot independently prove it; the original-owner adapter must do so separately in a future qualified release.
- Scope digest includes original FORGE SHA, lane, public candidate commit/path and the exact lane-specific terminal ticket, sequence, native source and evidence hash. Same ticket, equal/older sequence, malformed or ambiguous input, duplicate historical scope, backward clock or unexpected source path fails closed. A new FORGE release SHA or same-day rollover alone can never redeem spent original evidence.
- Renewable but bounded ADVISORY budget: max 2 total per UTC day, 1 per lane per day, 40 in sliding 30 days, 20 per lane in sliding 30 days. Prior attempted/failed/ambiguous provider requests count toward budgets; changing the date does not make them retryable. These are explicit shadow defaults to independently review, not applied provider policy.
- Output may say `ELIGIBLE_SHADOW_ONLY_NOT_AUTHORIZED`, but always sets original-owner request authorization, worker dispatch and scientific first-use to false, provider requests/paid calls to zero, accepted-ref mutations/controller changes zero.

## Real V19 integration requirements (not yet built)

1. Complete V18 exact-head main/ref ruleset qualification and original single-owner cutover without relaxing its immutable release ref. The connected GitHub App lacks repository Administration:write for installing the separate release ruleset; this source-only PR cannot solve that administrator boundary.
2. Add an original-Windows-owner-only adapter under existing `SingleOwner` mutex, performing cold SQLite event-chain verification, original owner SID/source/task identity, actual NEW per-lane `VERIFIED` terminal evidence, actual original scientific steering manifest, exact independent public candidate source/allowlist and occupied lane ownership. Shadow booleans and untrusted GitHub comments are NOT admissible witness.
3. Treat the existing V17/V18 lifetime record as preserved history (no deletion or reclassification). Preregister a separate V19 attempt schema/rollout under the original owner; ensure never double-counting or reusing a legacy scope even across V19 history. All duplicate detection must examine both histories.
4. Compare and reserve budget **atomically inside** the authenticated original SQLite transaction, write the canonical append-only `ATTEMPT` event BEFORE any HTTP POST, and revalidate the source after reservation. A 429, timeout or ambiguous publication result consumes the attempted scope; zero automatic retry.
5. Only separately permitted public/free model route, zero paid model fallback, no provider credential exposed to researchers. A model proposal must use existing owner source auth, candidate validation, independent deterministic Windows/Linux qualification and original scientific authority; the helper cannot dispatch, merge, accept science or select unseen data.
6. Prove at least two consecutive naturally scheduled new-feedback cycles for EACH Wingless and Yggdrasil; include negative outcomes, recovery after failed request, retained ledger integrity, exact owner and source locks, no unauthorized source change, resource/cost accounting, independent scientific controls, and an actually observed next eligible research decision. Do not claim autonomous science from a green shadow test.
7. Continue independent native research while the V18 release and V19 integration are qualified. Do not replace or compete with the currently running original Windows F139 task or CKB-plane.

## Specific negative acceptance

- No new native terminal evidence -> zero new request.
- An old terminal retargeted under a new FORGE SHA -> REPLAY BLOCKED.
- Another lane's terminal cannot renew this lane.
- Two requests in the same lane/day or over the rolling quota -> BUDGET BLOCKED.
- A fresh authentic lane-specific terminal after a previous complete scope -> ADVISORY eligible with **zero real calls or writes**.
- Unqualified/ambiguous source/owner/chain, duplicate ticket, terminal sequence rollback, malformed or unsafe path -> FAIL CLOSED.
- All old `FREE_REASONER_ATTEMPTED` event semantics and deployed original controller behavior remain unchanged.

This file is a design/qualification artifact, not a signed acceptance or production permission. Do not merge into protected main or turn on provider interaction as a byproduct of this PR.

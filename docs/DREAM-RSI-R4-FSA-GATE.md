# Dream-RSI R4 — native FORGE FSA archive-backed eligibility boundary

**Status:** Source-only, read-only FSA admission preflight; **not an active FSA, not a deployment, and not a new scheduler**. This R4 work extends the qualified Dream-RSI R3 source branch, using FORGE's existing private scientific archive and independent trust-anchor interface rather than inventing a competing execution authority.

## Real architectural integration

`dreamrsi/fsagate.ReviewAtAuthenticatedHead` binds four independent surfaces before allowing even an unprivileged selection recommendation to pass **for further FSA review**:

1. **Optimizer output:** The existing `dreamrsi.FSASelectionRequest`, with `ScientificAdmitted`, `DispatchAuthorized` and `AcceptedRefMutation` all false. It must match the policy SHA, lineage SHA, independently pinned authenticated training/validation history SHA, frozen optimization specification, lane, candidate ID and cohort pinned in a separately supplied FSA `Scope`.
2. **Predecision evidence:** The R3 Ed25519-signed `prospective.Selection` verified with *externally supplied*, independently pinned exact digest and signer key, evaluated against the exact policy's predecision choice. It must match source, original FSA epoch, prereg hash, policy, choice, cohort, lane and frozen resource ceiling. A signed `RANDOMIZED_UNAUDITED` proposal still does not qualify as a randomized scientific intervention.
3. **Real FSA high-water and physical archive boundary:** Calls existing `fsatrust.Recover` with an independently provisioned `fsatrust.Authority` and `fsatrust.Identity`. That code authenticates the external pinned monotonic archive head and physical archive binding, verifies the *whole* FORGE-private `privatearchive.Store` journal and retained raw science, then re-reads the anchor to reject mid-review advancement or fork. An absent, unresponsive, mismatched or unreadable external authority blocks all review; no local SHA is substituted.
4. **Actual scientific qualification and first use:** Scans the verified `researchlog.Journal` for an exact lane, generation and experiment ID, frozen prereg and cohort and an unrevoked source qualification witness. Hypothesis, prereg and qualified implementation commits are independently pinned (they may legitimately differ). Rejects `SOURCE_REPAIR_REQUIRES_REQUALIFICATION`, any prior `PRIMARY_STARTED`, terminal/review/archive, all cohort reuse (including cross-lane), missing, drifted or corrupt qualifications. The caller receives the source-qualified FSA high-water version and candidate identity **only as a read-only snapshot**, not a reservation or an instruction to execute.

The resulting `forge.dreamrsi.fsa-review-snapshot.v1` explicitly sets `EligibilityForFSAReviewOnly=true` while **scientific acceptance, cohort reservation, first-use consumption, dispatch, accepted-ref mutation, external physical independence proof, original/source audit and randomization audit remain false**. A review snapshot is ephemeral and can become stale immediately: FSA must recheck source and state at its *own* protected atomic consume/authorize transaction. This package exposes **no signer, CAS, Admit, Start, Run, dispatch endpoint or runner**.

## Scope and security assumptions

The FSA `Scope`, full canonical SHA-256 pin, FSA identity, qualified source witness and public signing pins must come from independent FSA eligibility/trust records. An optimizer cannot elevate itself merely by inventing a scope and hashing it. This R4 module deliberately does not create those issuers. The current `fsatrust.Authority` interface includes a remote mTLS implementation in FORGE, but its physical independence, protected key custody, remote atomic CAS and rollback-resistant external floor are *not verified/provisioned* (physical issue #20). The unit-test FSA archive and authority are controlled in-process fixtures with no physical-independence claims. A passing unit test proves contract behavior, not off-host durability.

The FSA remains the sole owner of independent scientific eligibility, preregistration, budget caps, protected first-use CAS, original STARTED/raw/terminal retention, independent scientific acceptance and next-experiment authorization. The optimizer may recommend; it may **never** dispatch or reserve.

## Failure matrix exercised by independent source qualification

- Genuine FORGE archive with three different hypothesis/prereg/qualified-source immutable Git commits and frozen source witness: accepted **only for further review**; no archive mutation
- Exactly two external FSA high-water reads: verified and stable; externally observed head replacement, outage, missing binding and rollback/fork: blocked
- Started original, uncertain original, duplicate cohort, missing qualification, repair requiring requalification, source drift: blocked
- Modified proposal or signed candidate identity, FSA privilege escalation, drifted frozen compute ceiling or scope SHA, duplicate/cross-lane use: blocked
- Two distinct Wingless/Yggdrasil mock eligibility snapshots: remain isolated; no shared budget/authority/runner
- Native Linux/Windows focused tests, one full Go regression, vet/build, Linux race and exact parent/patch-path guard

```sh
go test -count=1 ./dreamrsi/fsagate
go test -count=1 ./...
go vet ./...
go build ./...
go test -race -count=1 ./dreamrsi/fsagate
```

There is deliberately **no original science run or authenticated real FSA-issued approval** in this R4 qualification. F1/F2 consumed experiments remain untouched and never gain retroactive randomized policy probabilities. No change to CKB-plane, KTRADE, existing FSA checkpoint sources, scientific archive format or GitHub scheduler.

## Remaining gate to the north star

The next architectural R5 is an **independently controlled FSA-owned, atomic** before-STARTED first-use reservation and authorization integrated with the existing protected checkpoint service, with a verified source/receipt witness and distinct signing key custody. A separate candidate recommendation must be rechecked at commit time to defeat time-of-check/time-of-use races. Original outcomes and costs then flow into independently attested chronological histories; the optimizer may select the next eligible study only via FSA. Independent external randomized-policy data, real gain-per-compute evaluation, temporally disjoint heldout, two unattended fresh generations, restart/partition/fault tests and 24-hour soak remain necessary for scientific effectiveness or autonomous progression claims. No system is activated solely because R4 source qualification succeeds.

**Disposition: SOURCE-QUALIFIED INACTIVE REVIEW-ONLY FSA ADAPTER.** This is substantive native FSA integration, not a second authority, but cannot legitimately be called protected FSA activation.

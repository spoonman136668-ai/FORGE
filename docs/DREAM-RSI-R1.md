# FORGE Dream-RSI R1 — independently authenticated offline exploration optimization

**Status: source-only shadow; no FSA activation, scientific dispatch or authority.** Native FORGE subsystem; no dependency on old controller/queues, production systems, private scientific records or F1/F2 consumed experiment replay.

## Evidence contract

`dreamrsi.VerifyEnvelope` validates a domain-separated Ed25519 signature against an **independently pinned public key** and a separate canonical-history SHA-256. The chronological decision-time menu, selected cohort, historical cost, original SUPPORTED/MIXED/NEGATIVE/INVALID/CONSUMED_INDETERMINATE label, provenance Git SHA and receipt, logged action propensity and randomization proof hash are retained. Signed assertions do not themselves prove attestor custody, actual randomization, source authenticity or experimental causality: FSA must independently audit those.

Policies see **only predecision features**. The replay is **one-step contextual**, not an unrestricted multistep simulator: future experiment states following a different prior decision are unknown. An unobserved action has an `unsupported_counterfactual` count, not an invented result.

`OBSERVATIONAL` histories support only concordance and original class counts. They are prohibited from causal policy optimization. `RANDOMIZED_PROPENSITY_AUDITED` histories may support bounded inverse-propensity-weighted (IPS) estimates when the log probability was genuinely assigned before the decision, verified and at least 10%. Unmatched rows contribute zero to the *IPS estimator*, not a fabricated zero-outcome. Outputs give estimated quality, compute, ratio, uncertainty, effective sample size, match rate and outcome counts. Even signed randomized claims retain `randomization_audit_required=true`.

## Recursive policy optimization

An **independently hashed frozen spec** binds each lane, epoch, exact training and validation history IDs, chronologically disjoint windows, mutation seed, generation count, population, evaluation and replay-operation budgets, support and ESS thresholds. The sealed heldout must be a **separate** history never passed into `Optimize` or retuned against.

Four baselines: existing FORGE portfolio (4 impact + 2 novelty + robustness − cost), balanced, static impact/cost, and deterministic uniform. Bounded content-addressed mutations preserve policy-parent provenance. Every evaluated candidate, not merely winners, is retained in an exact SHA-linked train/validation ledger; survivor selection preserves weight diversity. No hidden budget increase, favorable relabeling or cross-lane borrowing.

The validation-selected champion is **a prospective policy recommendation, not a proved discovery improvement**. Nonclustered normal-approximation 95% uncertainty intervals are exploratory; repeated tuning on validation is not confirmation. Actual improvement needs independent, sealed temporal holdout, randomization audit and prospective FSA review.

## Persistence and handoff

`PersistLineage` uses exclusive-create monotonically numbered local files and verifies previous records on recovery; tampered, torn, missing, symlinked or divergent copies fail closed. It is a local restart-safety fixture, not a rollback-resistant multi-host FSA floor. FSA's external monotonic protection remains separate ([gate #20](https://github.com/spoonman136668-ai/FORGE/issues/20)).

`ProposeSelection` returns an **unprivileged FSA review request** identifying a proposed cohort, selected frozen policy, history and lineage SHA. Its preregistration, independent provenance approval, scientific acceptance, external generalization, dispatch and accepted-ref mutation flags are all false. The optimizer does not start jobs, create workflow branches, schedule workers, issue admission, touch trading or operate FSA.

## Reproducible source qualification

```sh
go test -count=1 ./dreamrsi ./cmd/forge-dreamrsi
go test -count=1 ./...
go test -race -count=1 ./...
go vet ./...
go build ./...
go test -run '^$' -bench BenchmarkReplaySyntheticFixture -benchtime=60x ./dreamrsi
```

CLI inputs are absolute, separately supplied signed training and validation envelopes, independent attestor public key and SHA pins, frozen spec with independent SHA pin, immutable output filename and optional local lineage directory. No network requests, secret generation, private dataset access or original experiments are necessary. Do not upload real protected histories or private keys into public CI.

### Baseline comparisons and honest compute accounting

Public CI's signed **synthetic logging fixtures** are code tests, not authenticated historical scientific discoveries. Their measured replay operations and CPU time are meaningful **implementation** efficiency measurements only. The two prior FORGE F1/F2 science originals lack recorded randomized policy-choice propensities and do not qualify as supported off-policy replay data. Do **not** assert gain-per-compute improvements, scientific compute savings or exploration superiority until independent genuine randomized historical logs, sealed holdout evaluation and FSA-controlled prospective validation exist.

### Independent FSA integration still required

1. FORGE-owned signed historical import with authenticated actual source, randomized action propensities and prior consumption ledger.
2. Temporally disjoint training/validation/once-unsealed holdout and appropriately powered uncertainty analysis, with no historical or sealed leakage.
3. Qualified protected FSA, one-shot first-use consumption, independent admission, frozen science, budgets, reproducible original raw evidence and negative retention. This shadow implementation does not create FSA.
4. Two or more genuinely unattended fresh experiment generations, restart/partition/race/fault and concurrent-lane qualification, full integration regression and 24-hour soak before separately authorized activation.

**R1 exit:** source-qualified historical contextual replay + bounded optimizer + persisted policy lineage + unprivileged FSA handoff. **Not** independently improved real discovery efficiency or autonomous dispatch.

# FORGE Dream-RSI R3 — prospective evidence-bound experiment selection

**Status: source-only, inactive FSA integration contract.** This implements exactly the missing *prospective recording boundary* identified by qualified R2 archival import. It is not a scheduler, original experiment, remote FSA signer, or scientific admission capability.

## What is frozen before outcome

A `Selection` records the FORGE lane (Wingless/Yggdrasil), monotonic epoch and tick, source Git commit, independent scientific preregistration SHA, selected optimizer policy SHA and immutable policy-lineage head, full decision-time candidate option list, cohort identities, independently documented context, selected candidate, original **maximum** compute budget, and logging mode.

In `OBSERVATIONAL` mode the selected candidate must equal the deterministic frozen optimizer policy's decision from exactly the recorded pre-outcome menu. Propensity entries and pseudo-random commitments are forbidden.

`RANDOMIZED_UNAUDITED` explicitly records *all* assignment weights in basis points summing to 10,000 with positivity (at least 10% per option), and a commitment to externally sourced randomness. It does **not** establish the randomness was actually unpredictable, independently administered or assigned before the decision. Its outcomes are permanently **ineligible** for IPS or causal replay absent a *separately qualified* FSA attestation/audit. No R3 function can flip this eligibility flag.

A domain-separated Ed25519 signature of the canonical selection JSON is verified against **both** a separately provided complete SHA-256 pin and a separately supplied public-key pin. Neither key nor asserted source is self-trusted. The selection signer is independent of the later result signer. The optimizer never obtains FSA signing keys.

## After-original join

`OriginalLink` is a separate, signed source/result record. It includes the complete predecision digest, prereg/source/tick/lane/cohort binding, original run ID, one attempt, STARTED digest, raw original SHA, postraw disposition SHA, the **unchanged** original scientific class, and actual observed compute units. Missing values, mismatched source or lane, modified classification, unrecognized classes, exceeded frozen budget, second original attempt, or a reused signing key fail closed. The join also rehashes *already verified* objects to detect post-verification mutation.

The only result is `forge.dreamrsi.prospective-observation.v1`, which explicitly records **false** for protected chronological ordering, independently audited original science, independent randomization, causal replay eligibility, FSA acceptance, dispatch and accepted-ref mutation. A valid signature alone **cannot prove** that an artifact was persisted before scientific execution; that needs an externally maintained, timestamped/monotonic FSA witness.

`ToObservationalDecision` can project genuinely paired fields to an **OBSERVATIONAL-only** Dream-RSI historical row. FORGE's existing independently authenticated history compiler must separately authenticate/source-sign the full history and preserve original labels. A randomized-looking signed selection is **not** automatically authorized as `RANDOMIZED_PROPENSITY_AUDITED` merely because numbers sum to 10,000. There is no path for R3 alone to claim an experimental policy benefit.

## Isolation, retention and restart

`VerifyChronologicalLane` rejects repeated cohort or predecision/original evidence, out-of-order or reused ticks and epoch regression. `CompareLaneIsolation` rejects cross-lane cohort collisions. Local `PersistOnce` uses exclusive creation and writes a single read-only observation; a second attempt fails even for identical content. This is **local** conflict exclusion, not multi-host atomic consumption or protected rollback-resistant storage. If the output write is incomplete, a subsequent write must stop rather than silently rewrite or replay. F1/F2 original cohorts remain consumed and **cannot** supply historical logged randomized policy decisions.

## Invocation and reproducible qualification

```sh
go test -count=1 ./dreamrsi/prospective
go test -count=1 ./...
go vet ./...
go build ./...
go test -race -count=1 ./dreamrsi/prospective
go test -run '^$' -bench BenchmarkDecisionVerifyJoin -benchtime=100x ./dreamrsi/prospective
```

The CLI `forge-dreamrsi-prospective` requires absolute local paths `-selection`, `-original`, `-policy` and `-output`, plus `-selection-sha`, `-selection-public-key`, `-original-sha` and `-original-public-key`, all obtained out-of-band. Both Ed25519 signatures must come from truly distinct externally controlled signers. It rejects unknown or concatenated JSON and writes a new observation file, never modifies the input, and never contacts a runner, scientific repository, FSA service or network.

**Readiness gate beyond R3:**
1. Independently qualified, active FORGE FSA issues protected signed high-water witness **before** experiment STARTED, with predecision candidate information sourced only from eligible/preregistered state; scientifically justified assignment design and independent randomness custody.
2. Independently signed original STARTED, raw and classification lineage, verified actual compute-meter units and one-shot consumption. These records cannot originate from the optimizer itself.
3. Distinct train, validation and once-sealed heldout prospective decision histories; audit randomization and conditional support; compare baselines with uncertainty and valid causal assumptions, without repeatedly optimizing sealed data.
4. Independent cross-platform integration/full regression, controlled fault matrix, two genuine **unattended** fresh Wingless/Yggdrasil cycles, 24-hour soak, and explicit activation authority.
5. FSA stays sole preregistration, eligibility, once-only dispatch and acceptance authority. This source-only contract has **no live original execution**, new cloud provisioning or modification to existing research or KTRADE.

The final design goal is operational experiment selection by a qualified Dream-RSI policy **through the FSA**, not indefinite observation-only operation. This R3 component advances the interface but does not misrepresent an inactive FSA as deployed.

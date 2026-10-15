# FORGE optimizer integration: existing Cloudflare, no new controller

**Stage:** source-only, read-only dual-lane qualification. NOT real policy promotion.

The existing FORGE research worker/controller remains the only research orchestrator. Cloudflare is **the user's pre-existing durable evidence/custody infrastructure**, not a replacement orchestrator or a reason to build another FSA cluster. This change provisions no Cloudflare accounts, buckets, credentials, worker service, new cron, or scientific first-use authority. No GitHub Actions secret is read.

The shared `optimizerbridge` composes existing `dreamrsi`, `evoportfolio` R8 Pareto, `promptlineage`, `thetaadapt`, and `genenv` under separately provided exact evidence/source pins. It refuses missing/nonmatching trust roots; fails atomically across Wingless and Yggdrasil; retains negative/mixed/invalid/consumed evidence, per-family diversity, frozen budgets, training-only proposals and `UNTESTED` labels. It issues **no execution claims**.

## Fit to existing Cloudflare

Do not invent Cloudflare account IDs, bucket names, R2 endpoints, namespaces or signer keys. The existing authorized evidence ingestion path can *supply* to the read-only bridge: (1) immutable evidence and train/validation manifests retrieved from the existing private Cloudflare store; (2) their SHA-256s + verification key(s) from an independently held/pinned trust source, not inferred from the retrieved objects; and (3) separate Wingless and Yggdrasil frozen portfolio, generator plans, compute caps and first-use high-water. The output is a content-addressed shadow selection comparison; the existing authorized retention pathway may replicate it back to Cloudflare with immutable object naming and original-source metadata.

**Never treat R2 object existence, bucket operator ownership, an ETag or a key name as independent signing, immutable retention, CAS, FSA control, or proof that experiments were randomly assigned.** Ed25519 history signatures and independently pinned source hashes must verify. For causal improvement, Dream-RSI demands genuine audited randomized logging probabilities and prospectively qualified independent evaluation. Ordinary GitHub experimental result histories are observational and do not qualify causal counterfactual improvements. Cloudflare billing/usage caps remain governed by the existing user setup; no new continuous polling or bulk duplication is activated by this source gate.

## Honest operational gates

1. Source-only merged/qualified five-enhancement shadow composition via synthetic signed histories; no original science.
2. Bind read-only Cloudflare-backed **authentic** evidence manifests through the already-authorized worker; require independent original byte digest and verified remote retention, full consumed-first-use reconciliation, accurate propensity audit. If incomplete, output `NOT_QUALIFIED`, not an optimizer recommendation.
3. Compare frozen optimizer proposals versus existing selection on **prospective**, distinct science, under exact per-lane compute budget. No sealed first-use without existing authority. Require meaningful advantage and negative controls before promoting any optimizer.

No FORGE engineering R32/R33 modification, duplicate research controller, Cloudflare provisioning, paid API or KTRADE changes. F3 stays `NOT_ADMITTED`. Research can continue independently while this bridge is qualified.


## Implemented source-only read-only export seam (stage 2 preparation)

`optimizerbridge.EvaluatePinnedExport` and `cmd/forge-optimizer-shadow` now accept canonical, immutable **already-exported** Wingless/Yggdrasil evidence JSON supplied by the **existing** authorized Cloudflare evidence worker. No endpoint/account/bucket/namespace is invented or accessed by this source patch. The CLI reads five separate **absolute regular-file** inputs:

```text
forge-optimizer-shadow \
  --wingless-evidence ABSOLUTE_PATH/w.json \
  --yggdrasil-evidence ABSOLUTE_PATH/y.json \
  --signed-export ABSOLUTE_PATH/export.json \
  --independent-anchor ABSOLUTE_PATH/anchor.json \
  --independent-lane-pins ABSOLUTE_PATH/pins.json
```

The first two files are canonical serialized `optimizerbridge.LaneEvidence` objects; the third is `optimizerbridge.SignedExport` with two immutable object-key/digest/first-use/source-birth observations. The last two files MUST come from independent trusted pins outside the Cloudflare export and outside the FORGE working repository; they correspond to `optimizerbridge.ExternalTrust` and `[]optimizerbridge.LanePins`. Sign the canonical JSON serialization of `SignedExport.Manifest` using a separately held custodian Ed25519 key with signature domain `FORGE-OPTIMIZER-CLOUD-EVIDENCE-V1\\x00`. Never provide private signer keys to the FORGE runner.

The verifier enforces exact bytes, detached signed manifest digest and trust key, monotonic minimum revision, distinct lane evidence/keys/source-birth ledgers/consumed-first-use ledgers, independently pinned first-use high-waters, and all five existing signed-history and frozen-budget gates. Export evidence from a genuinely independent worker and preserve original negative/invalid histories. A signature that was generated by this CI or derived from the fetched object is **not independent source custody**.

**Current operational truth:** Neither the export files nor separately held real pins have been provided to this source branch. FORGE's existing GitHub archive manifests enumerate byte-verified originals but do not furnish the independently audited randomized Dream-RSI histories or complete first-use ledger required to run this gate on authentic science. Consequently no authentic Cloudflare read, zero accepted prospective comparisons, zero optimization-authorized science, and no live successor claim can be made from these tests. The CLI emits no advisory if any input is incomplete. Its successful result always marks remote operational custody, complete first-use reconciliation, scientific improvement and dispatch authorization **false**. Genuine operational proof must be attached from the pre-existing worker by its legitimate owner and separately verified before any further gate.

**Usage cap:** Manual/event-triggered invocation only on an existing evidence batch. No polling, new Cloudflare bucket, Worker, scheduled task, automatic replication or paid API. Never store sealed histories, private trust anchors, credentials or raw private evidence in public CI logs/artifacts.

## New bounded qualification: independently signed selection-claim audit

The read-only CLI now additionally requires `--wingless-selection-audit`, `--yggdrasil-selection-audit`, and `--independent-audit-pins` from the **same existing independent custody/review pathway**. It refuses a successful report if the evidence is not independently signed or if signed randomization claims, first-use receipts, logged probabilities, source history, or assignment-event identifiers disagree. These are separate per-lane inputs and do not create a new signer, controller or service.

This additional review verifies **claim consistency**, not actual randomized assignment. An Ed25519 attestation of a claimed probability, or an event digest lacking independently validated source bytes and timing, does not establish randomized logging or unbiased causal estimates. Output therefore always retains `actual_randomization_independently_demonstrated=false`, `scientific_improvement_established=false`, and `prospective_science_authorized=false`. An authentic operational custodian must confirm the actual selection process, source-birth time, independent event custody and propensity-generating mechanism before prospective comparison. If those are unavailable, do not promote selection or invent a shadow improvement.

The external files are supplied exclusively to the existing worker. No live Cloudflare read occurs in public CI; no secret, private evidence, protected cohort, or signing key is published.

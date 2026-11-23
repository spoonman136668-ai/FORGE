# RSH-02 — six-lane source index × read-only FORGE FSA observation

**Purpose:** advance one shared-memory/one-FORGE-research-hub architecture without preempting F139 (currently enabled for Wingless/Yggdrasil) or reassigning already-accepted science. This is a bounded *negative-only* source gate, not live FSA admission.

## Implemented boundary

`researchfeed.ObserveFSA(ctx, rawIndex, reader, ownerPin)` takes the exact **untrusted six-lane submission bytes** from RSH-01 and revalidates them *before* any authority read. A separately provisioned `ReadonlyFSA` has only `ReadAnchor` and `ReadBinding` methods, matching the current `fsaservice.AuthorityStore` **read-only** interface. No `CompareAndSwap`, network client, controller, background worker, scheduler or scientific first-use permission is available.

It requires an **externally authenticated operator** identity pin (archive ID, key ID, Ed25519 public key, epoch, minimum sequence, binding SHA-256). It reads FSA anchor, verifies the pinned identity and monotonic minimum, observes separately protected binding to exactly the pinned digest, rereads the FSA anchor and denies advancement if anything changed. The supplied FSA reader must itself validate transport authentication and independent witness custody; an arbitrary worker-created adapter or merely matching a hash is **not** an acceptable live trust source.

The returned `forge.six-lane-fsa-readonly-observation.v1` describes only the pinned source-index SHA-256, observed research-lane names and the consistent archive-head identity. The output sets `advisory_only=true`, `archive_binding_observed=true`. All of `original_bytes_authenticated`, `first_use_authorized`, `scientific_accepted`, and `dispatch_authorized` remain **false**. No scientific conclusions are silently relabeled.

## Verification

`go test -count=1 ./researchfeed`; `go test -race -count=1 ./researchfeed`. Existing `.github/workflows/qualify.yml` executes repository-wide Linux and Windows source regressions and Go build/vet without private evidence, tokens or a new workflow. Unit-test FSA endpoints are **synthetic fixtures only**, not real externally hosted FSA proof. The complete suite also verifies F139 and FORGE's isolated-controller contract.

Reject invalid index **before reading FSA**; bad owner identity, key/epoch/sequence, missing binding, changed head, missing source or canceled context all fail only the *new optional observation*. They do not pause or cancel running F139 or other existing research work.

## What remains before operational authority

1. An independently provisioned FSA read-only service with signed witness and authenticated independent archive binding must be reachable through existing authorized FORGE custody; this source change does not provision one.
2. Authenticate actual original research bytes, signer and first-use history for each independent lane against a frozen source, not against submitted or retrieved Mind-Palace summaries.
3. Prove a realistic operator-approved **prospective** FSA scientific intake and acceptance flow with untouched negative/frozen histories and dual independent controls; never authorize execution from read-only metadata.
4. Measure an improvement and no-progress-regression against the existing F139/qualified science baseline; retain the old operating path until proven. Cross-lane incoming evidence alone is not scientific advancement.
5. Mind-Palace unified North Star policy PR #101 still requires protected qualification and real multi-agent readback. No FORGE-to-CKB-plane dependency is allowed.

**At RSH-02:** No private credentials, original experiments, existing F139 intake, accepted references, signer, publisher, controller or runner is changed or activated.

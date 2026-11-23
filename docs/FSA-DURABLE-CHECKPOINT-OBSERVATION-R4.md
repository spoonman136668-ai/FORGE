# FSA R4 — independent durable checkpoint observation (source-only)

Status: **implementation and synthetic qualification only; no FSA service is deployed and no scientific authority is transferred.**

This increment connects the existing `fsaanchorstore.Store` and separately signed `fsawitnessstore.Store` to the already-qualified mutual-TLS read-only API via `fsaservice.NewObservedAuthority`. The adapter requires **two** caller-provisioned observations: a checkpoint backend implementing `fsatrust.Authority` and an **independent physical archive-binding attestor** implementing `IndependentBinding`. The checkpoint's self-reported archive ID is NOT by itself accepted as evidence of physical binding.

Binding is assessed with two checkpoint reads around the independent attestation. Archive-ID mismatch, missing attestation, a false binding, canceled requests, changes to the checkpoint, and absent/ambiguous stores reject. The existing client independently validates the witness Ed25519 signature, separately pinned mTLS server identities, authority head equality and minimum witness revision.

## Synthetic integration evidence

The `fsaservice` integration test uses **real distinct mTLS test servers** plus **two independent local test directories**. It checks:
- Signed genesis accepted, then checkpoint-ahead-of-witness denied
- Witness-ahead-of-checkpoint denied
- Matching signed high water accepted
- Each persistent backend reopened under independently supplied immutable genesis/revision pins
- Complete checkpoint tail deletion rejected against intact signed witness
- Missing/failed/false physical binding, foreign archive and checkpoint change during attestation rejected

Tests use synthetic keys and untrusted local fixtures only. The direct synthetic `fsaanchorstore.CompareAndSwap` in this test is not a qualified scientific admission path, and `POST /v1/fsa/cas` remains unavailable. No worker dispatch, first-use reservation, FSA signer, new scheduler, queue consumer, broker, production secrets or CKB-plane authority mutation is introduced.

## Required before autonomous execution

A physically independent service/key custody deployment, actual immutable physical archive attestation, hardware-backed/independent monotonic checkpoint and witness retention, signed scientific CAS validation, atomic worker epoch fencing at the execution boundary, one-shot original-first-use custody, owner transfer/revocation, Windows crash/power-cut qualification and full isolated cutover regression remain mandatory.

**In particular:** two test TLS origins or local directories do not establish different protected failure domains. The adapter is not itself an independent archive-binding attestor. Green unit tests must not be equated with deployed autonomy.

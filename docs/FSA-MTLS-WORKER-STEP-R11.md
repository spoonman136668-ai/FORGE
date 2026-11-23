# FORGE FSA R11 — authenticated worker step-consumption HTTP boundary

**Status: public source-only, unregistered handler with synthetic mTLS qualification. NOT deployed FSA, actual worker action authorization, scientific execution or accepted result.**

R8 introduced an independently pinned, signed step-consumption receipt contract. R10 added local append-only owner-epoch and step ordering. R11 joins them to a bounded, versioned **mTLS worker request** at `POST /v1/fsa/consume-step`.

## Boundary and acceptance

1. A worker presenting a separately **SPKI-pinned client certificate**, different from FSA read-only and signed-checkpoint writer certificates, submits a canonical, strictly decoded, size-bounded claim (max 4096 bytes). No unsigned or reader/writer impersonation fallback exists.
2. The service calls a caller-provisioned **independently authenticated first-use/original-custody attestor**. A missing or negative attestor blocks. This public package supplies only its interface, not a real all-lane FSA first-use service.
3. With a separately supplied trusted server clock, the existing `workerfence.Observe` checks owner epoch, worker lease, archive binding, independent signed FSA high-water and two distinct pinned mTLS peers.
4. The R10 immutable store checks the same owner epoch and lease, verifies its own trusted clock, and durably consumes the exact original/worker/step identity, creating a separately signed one-shot receipt. Duplicate requests fail closed.
5. The handler verifies the signed receipt under an independent pinned step public key, checks original custody again, compares epoch and owner again, and re-observes the independent signed remote high-water before returning.
6. The only positive response includes `execution_authorized=false`. An uncertain receipt/transport/readback remains a non-retryable consumed risk, NEVER an instruction to start an experiment.

## Synthetic qualification

Real mTLS with **three distinct client identities** (read-only, checkpoint writer, worker) and a separate server. Positive tests verify a signed receipt through the actual remote dual-FSA witness client plus R10 durable local epoch journal. Negative cases include reader/writer privilege confusion, missing original custody, duplicate JSON fields, invalid archive head, expired claim, exact repeated step, signed owner revocation and a new owner before independent FSA epoch propagation.

## Why this remains non-operational

- This handler is **not registered with a production network listener**. It does not provision a service, identities, signer, physically independent authority or real first-use evidence source.
- An authenticated owner step claim is not independently attested worker executable identity. The current clock and custody are synthetic fixtures in tests.
- Read/consume/read can detect drift but **cannot eliminate a race** between returning the receipt and a real external side effect. Mandatory worker-side action mediation, independent atomic cutover/revocation, distributed linearizability, external monotonic witness, protected credentials, crash recovery and cross-platform soak remain required.
- No worker dispatch, real scientific primary, production KTRADE/broker, CKB-plane authority, Mind-Palace write, sealed holdout, accepted ref or independent research queue is touched.

FORGE must not claim active scientific autonomy from a green unit test or this negative-only endpoint. A separate qualified authority process enforcing actions in the same trust boundary as the epoch CAS remains the next hard integration gate.

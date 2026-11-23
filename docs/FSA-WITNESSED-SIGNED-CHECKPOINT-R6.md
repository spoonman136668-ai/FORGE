# FSA R6 — witnessed signed-checkpoint gate (source-only)

Status: **synthetic qualification primitive, not a deployed signer, scientific controller, research admission server or execution permission**.

`fsaservice.NewCheckpointGate` composes existing, independently qualified components into a bounded source-level checkpoint protocol. It requires an externally pinned Ed25519 FSA identity, a complete retained `privatearchive`, a `fsatrust.Authority` durable checkpoint backend, an independent physical archive-binding attestor and the existing dual-peer read-only mutual-TLS `fsaremote.Client`.

## Write acknowledgement protocol

1. Verify independently witnessed remote head and compare it with the locally supplied checkpoint backend. Confirm external binding commitment via both independent attestor and pinned mTLS authority.
2. Read the witnessed head again to reject preflight drift. Verify the FSA-signed proposed archive head against the **entire** private scientific archive, including original bytes and predecessor.
3. Invoke `fsatrust.Advance`: it repeats full verification before exactly one monotonic CAS, and verifies the committed checkpoint by a separate readback.
4. Require independent signed high-water witness to match the newly committed checkpoint, re-confirm external binding, and re-read the witnessed head **before reporting a positive result**.
5. If any write/readback/witness/physical-binding step is indeterminate after a possible commit, latch `INDETERMINATE_NO_RETRY` for the lifetime of the source-only gate instance. An operator-controlled fresh recovery with separate pins remains necessary; neither an HTTP retry nor a second primary launch is allowed.

## Synthetic tests

Real distinct mTLS test servers and separate fixture directories back the archive, checkpoint and witness stores; separate fixture keys sign the scientific head and high-water witness. A **test fixture** links synthetic witness issuance to a successful backend CAS, exercising the positive case. Separate negative tests withhold the witness after a committed CAS, reject forged signatures, foreign binding digests, absent physical attestations, mismatched archive heads, canceled contexts and racing duplicate signed proposals.

## What this does NOT establish

- The positive synthetic case uses fixture-only synchronous signing and deliberately **does not represent independently deployed witness retention, multi-host linearizability, power-cut atomicity, signer custody or failure-domain independence**.
- Nothing here exposes POST `/v1/fsa/cas`. The public `fsaremote.Client.CompareAndSwap` still cannot commit through the strictly read-only FSA services. A separately qualified authentication/write-side protocol is required.
- A valid checkpoint only records already-submitted scientific evidence. It is not original experiment approval, FSA execution authority, worker lease renewal, active cohort custody, runtime launch or accepted-ref promotion.
- CKB-plane/KTRADE services, queues, controller, original experiments, research budgets and Mind-Palace remain untouched.

Next gates remain: physically independent monotonic CAS+signed witness deployment; immutable external binding; authenticated signed-checkpoint HTTP write protocol; atomic worker epoch fencing and crash-recovery; native Windows filesystem fault cuts; two-lane unattended synthetic and then separately authorized real-science cutover.

# FORGE R9 — independently verify native worker-signed synthetic custody

**Correction to the R4/R8 trust model.** Earlier versions said each synthetic native worker created signed STARTED/TERMINAL receipts, but the outer two-lane generation controller only verified file presence and byte hashes. The child itself validated its own ephemeral signature; that was not independently reverified by the controller. This qualification fixes that gap without enabling or replaying any original science.

## Exact narrow change

- The existing pinned `forge-sandbox-worker` now includes its **ephemeral, non-authoritative Ed25519 public key** in its canonical JSON stdout. It never returns or persists its private key.
- The existing `cyclecontroller` writes that exact stdout public witness once, next to the worker's immutable original-attempt journal. It is covered by the content-addressed terminal-head chain and external cross-runner checkpoint.
- Before reporting a completed generation, and on **every complete restart replay**, `cyclecontroller.verifyNativeReceipts` independently reads that witness, strict canonical signed STARTED receipt and write-once original-attempt record, reconstructs the precise lane, source/prereg, intent, worker, original ID and owner epoch, checks original STARTED Ed25519 signature and SHA fingerprint, and invokes the preexisting `syntheticsupervisor.Recover` to verify the signed TERMINAL receipt and source-bound original custody. It also requires all three worker files to be present. No unsigned or unverifiable terminal is a success.
- Negative tests mutate STARTED signature, TERMINAL signature, public key, original-attempt state and delete the public-key witness; all must be denied and retain a sticky no-replay quarantine. Native two-lane and cross-runner full resume acceptance must run again, as the evidence hash schema changes to include the key witness.

## Provenance limit

The ephemeral public key is emitted by the child binary, and is **not** a separately provisioned scientific trust root. A compromised first-launch worker could mint its own identity; the binary SHA pin and externally anchored original snapshot are still required. This is signed-evidence *readback integrity* under synthetic test authority, **not** a real signed FSA scientific STARTED/TERMINAL, independent owner transition, production signer, globally durable CAS, or scientific execution admission.

No CKB authority transfer, private CKB ledger access, original Wingless/Yggdrasil dispatch, scientific result mutation, KTRADE change or new credentials. Existing independent research stays running.

## Gate

Full Go Linux tests/race/vet/build and native Windows tests/vet/build at the exact branch head, and post-merge actual two-runner R8 acceptance (original two parallel synthetic generations, externally anchored checkpoint, two more parallel synthetic generations, no replay) plus normal native two-lane acceptance on both OSes. A green source test alone is **not** acceptance of cross-runner recovery or real science.

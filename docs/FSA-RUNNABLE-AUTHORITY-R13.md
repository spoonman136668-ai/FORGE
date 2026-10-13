# FORGE FSA R13 — runnable read-only authority checkpoint host

**Source-qualified executable only. Not deployed or independently provisioned. No live scientific authority, original-first-use clearance, write endpoint or worker execution.**

Together with R12, FORGE now has *two buildable processes*: a read-only checkpoint authority server and an independently signed witness server. Both are explicit TLS 1.3 mTLS endpoints. Tests place them in separate loopback listeners; tests DO NOT prove independent physical hosts or operator-owned secret custody.

```
go build -o forge-fsa-authority ./cmd/forge-fsa-authority
forge-fsa-authority -config /absolute/protected/path/authority-public-config.json
```

No default listener or signing key exists. The executable reads a strict, versioned, canonical config (`forge.fsa.readonly-authority-host.v1`) with these externally provisioned fields:

- `listen_address`: explicit IP and port, loopback by default; `allow_remote` requires explicit opt-in, plus separate firewall/host isolation.
- `checkpoint_root`: existing dedicated `forge-fsa-trust` store created with independently pinned genesis. Local store is **NOT** an independently linearizable durable authority.
- `archive_id`, `key_id`, `authority_public_key_hex`, `authority_epoch`, `binding_sha256`, `witness_public_key_hex`, `minimum_witness_revision`: immutable externally authenticated FSA identity and separate witness public key.
- `minimum_sequence`: separately retained latest known checkpoint sequence. A rollback below this floor rejects startup; a running instance also remembers the largest checkpoint it has already observed.
- `binding_proof_file`, `binding_signer_public_key_hex`, `minimum_binding_revision`: **external signed binding proof** with schema `forge.fsa.external-binding-proof.v1`, domain `FORGE-FSA-EXTERNAL-ARCHIVE-BINDING-V1\n`, a bound archive ID/epoch/physical binding commitment and independent revision. The authority verifies the Ed25519 signature and pinned revision on every binding request and poisons the process on regression or forgery.
- `allowed_client_spki_sha256`, `client_ca_file`, `server_cert_file`, `server_key_file`: independently provided TLS 1.3 client CA, pinned reader identity, server certificate and protected server private key.

Importantly, verifying a signed **assertion** of physical archive binding does not establish the truth of that assertion. The separate attesting operator/process MUST itself validate the actual physical archive identity using independently protected evidence. This repository does not supply an attestation signer or filesystem binding authority, and a local JSON file or synthetic signature is not physical independence.

## Exposed operations

Only `GET /v1/fsa/anchor` and `GET /v1/fsa/binding?archive_id=...`. No checkpoint write, original dispatch, owner transfer, worker side effect, step-consumption POST, source promotion or accepted-ref API is registered in this executable. All other methods and paths reject.

## Integrated qualification

Real TLS loopback listeners host the R13 checkpoint server and existing R12 signed witness server with separate server certificates. One `fsaremote.Client` uses the **exact independent authority and witness SPKI pins** to verify signed genesis, independent binding, checkpoint-ahead-of-witness failure, signed witness catch-up, and rollback rejection. Additional tests reject forged binding signatures, stale independent binding revisions, restored older checkpoint floors, signer reuse and non-opted-in public listening.

Full Linux tests and race, vet, build, isolation, and native Windows tests/vet/build must pass on the exact code tree. Test-only keys are disposable and are not deployed to any real runner.

## Operational gates still missing

Two local test listeners are not separate hosts. Before any live science: physically isolated FSA primary+secondary services, externally protected monotonic floor and CAS (including epoch), independent signer and archive attestation authority, immutable global all-lane original-first-use custody, protected worker binary and **mandatory per-side-effect epoch enforcement** without a time-of-check/time-of-use gap, verified old-owner revocation, restart/power-cut qualification and isolated Wingless/Yggdrasil unattended cycles.

The present R12/R13 servers are deliberately **read-only**. This increment does not activate FORGE, interfere with CKB-plane/KTRADE, use live scientific inputs or mutate accepted source references.

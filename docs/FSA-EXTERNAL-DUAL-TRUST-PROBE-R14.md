# FORGE FSA R14 — external dual-host read-only trust verification

**Qualified source-only diagnostic; no authority, execution, activation or production credential provisioned.**

R12/R13 provide two distinct buildable FSA server roles. R14 adds a third, standalone **external observer** process which verifies both processes over real TLS 1.3 mutual authentication instead of trusting a server's local green status.

```
go build -o forge-fsa-probe ./cmd/forge-fsa-probe
forge-fsa-probe -config /absolute/protected/path/external-trust-probe.json
```

The `forge.fsa.external-trust-probe.v1` config has no defaults. It pins:
- `archive_id`, `key_id`, `authority_public_key_hex`, `authority_epoch`, `binding_sha256`, `witness_public_key_hex`.
- Independently retained `minimum_witness_revision` and `minimum_checkpoint_sequence`.
- `client_cert_file` and protected `client_key_file` (absolute PEM paths, no symlinks; Unix group/other key access rejected).
- Distinct `authority` and `witness` objects, each with independently provided `base_url`, `client_ca_file`, and `server_spki_sha256`. Both peer SPKI pins must be different. The trusted endpoints must be on separate protected failure domains; disjoint URLs alone cannot prove that.

The diagnostic invokes the pinned dual-peer `fsaremote.NewClient`: it reads and verifies the authority head plus the separate witness Ed25519 signature, rejects stale/rollback checkpoints, independently confirms the binding commitment, and repeats the signed authority observation to detect a changed head during verification. Any unavailable server, missing secret, bad TLS identity, witness mismatch, unbound physical archive, replay or minimum-floor violation stops without retrying a scientific step.

A successful output is structured JSON with `mode="READONLY_DUAL_FSA_TRUST_OBSERVED_NOT_DEPLOYMENT_ATTESTED"`, the signed archive identity, authority epoch, sequence, head, `binding_verified=true`, and **all** of:
- `deployment_independence_verified=false`
- `execution_authorized=false`
- `science_activated=false`

It **cannot** attest that services are physically independent, secrets are hardware protected, signer custody is real, an externally monotonic CAS has been deployed, CKB ownership is revoked, or worker actions are guarded against epoch loss.

The integrated test invokes this exact observer against both runnable source-level server roles over distinct real TLS listener sockets with separate server certificate SPKI, and rejects wrong witness pin, peer reuse, checkpoint-ahead-of-witness, false minimum checkpoint/revision floors and later corrupted independent binding evidence. All evidence uses disposable synthetic keys.

## Remaining operational work

1. Obtain distinct protected hosts, service identities, operator-held FSA/witness/binding signing custody, physical archive attestation and external monotonic high-water pins.
2. Provision FSA's independently durable write/epoch service with atomic cross-node original and step consumption; current read-only hosts never become writers by configuration.
3. Enforce ownership **within** every real worker side-effect boundary and prove halt on revocation; two-sided reads before or after an action are insufficient.
4. Perform first-use original custody migration/reconciliation, CKB-plane old-owner revocation, and native Linux/Windows crash/power-cut/fault-injection qualification for Wingless and Yggdrasil.
5. Complete the controlled cutover and unattended independent scientific cycles, preserve all negative findings and frozen budgets.

This probe is a mandatory independent observer to aid deployment qualification, not a substitute for deployment evidence or scientific activation. Nothing in this change contacts brokers, writes CKB/KTRADE, reruns an original or promotes an accepted scientific reference.

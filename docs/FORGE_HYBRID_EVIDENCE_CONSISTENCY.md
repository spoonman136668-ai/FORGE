# Hybrid evidence consistency adapter — no research activation

This package is a small standalone **read-only** step for the prospective
TTT-Hybrid-Lab research track. It adds no controller, task, runner, credentials,
network dependency, queue, workflow, first-use, merge, or scientific acceptance.

## What it verifies

- An **out-of-band, caller-supplied** Ed25519 public key verifies a detached
  signature over the exact canonical engineering-attestation bytes.
- Expected source commit, PR identity and frozen protocol path are supplied
  **separately** from the signed statement; an untrusted statement cannot
  choose a different project or silently change the expected experiment.
- Hashes of the supplied frozen protocol and engineering artifact must match
  the signed statement. Protocol-only receipts cannot claim an executed run;
  engineering receipts must name a run and attempt.
- Duplicate/ambiguous JSON keys, unexpected fields, malformed provenance,
  foreign repository, path traversal, payload mutation, invalid signature
  and substitutions fail closed.
- Output contains only sanitized metadata and explicitly flags
  `github_source_authenticated=false`, `first_use_authenticated=false`,
  `execution_authorized=false`, and `scientific_accepted=false`.

**Crucial distinction:** The signature establishes consistency with whichever
public key the caller trusts. It does **not** prove that key is an authorized
project witness, that the source bytes were independently retrieved from
GitHub, that the run was qualified, or that scientific training succeeded.
The signing key must be authorized *independently* before this adapter is used
with real custody evidence. No signing or secret key is created or stored here.
The only key in tests is a deterministic synthetic development fixture.

## Existing tracked hybrid studies

- S24 source PR #39: `experiments/g7_s24_frozen_good_views.json`
- S25 source PR #40: `experiments/g7_s25_frozen_contradiction_ttt.json`

This adapter does not read the private hybrid repository. The separate
authorized hybrid project must verify its exact upstream SHA, protocol blob,
and workflow artifact identity before producing an attestation. Do **not**
commit private protocol payloads, scientific data, model weights, or keys
into FORGE.

## Future integration gate

Qualify project-specific signer/issuer custody and an independently authenticated
GitHub artifact transport, then add a disabled runner adapter with resource,
no-replay and recovery tests. A third research lane may be activated only after
all relevant full regressions and scientific first-use controls pass. Existing
Wingless/Yggdrasil operation and all frozen S24/S25 scientific splits remain
unchanged.

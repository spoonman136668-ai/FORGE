# FORGE FSA R8 — bounded worker step-consumption fence (source-only)

**Status: synthetic qualification. No active worker, scheduler, production signer, independent step authority or scientific-execution permission.**

## Why

FORGE's existing `workerfence.Observe` authenticates a remote checkpoint and separately signed witness through two real mTLS peers. That is useful but **not an atomic fence** at an irreversible worker step. A worker could lose its epoch or lease immediately after observation. Neither a successful remote read nor a local process mutex permits executing science.

## New bounded boundary

`workerfence.InspectStep` composes:

- The existing real, strictly pinned `fsaremote.Client` with a before-and-after `workerfence.Observe` of signed authority head, immutable archive binding, precise owner epoch and nonexpired lease.
- A canonical `StepClaim` tied to FORGE archive high-water, Wingless or Yggdrasil lane, original identity, frozen intent SHA, owner ID/epoch, worker ID, worker binary SHA, lease sequence/expiry and unique step SHA.
- A `StepAuthority.ConsumeOnce` interface which **must** atomically and durably reject duplicate, superseded, expired and foreign steps at the separately deployed FSA authority. It is an interface contract, **not a provided production implementation**.
- A domain-separated Ed25519-signed `SignedStepReceipt` from an independently provisioned step-receipt key, distinct from the scientific archive signing key.
- Mandatory fail-closed treatment of stale lease, first-use ambiguity, issuer mismatch, bad signature, missing authenticated witness, request ambiguity, duplicate consumption and owner/head change observed after consumption.

A consumed step returns `SOURCE_ONLY_STEP_CONSUMED_NO_EXECUTION_AUTHORITY` with `worker_dispatch_authorized=false`, `scientific_execution_authorized=false`, and `first_use_replay_authorized=false`. The step is never retried following an uncertain response. It does not clear original first-use custody.

## Synthetic qualification

The `fsaservice` test runs this boundary through the existing distinct mutual-TLS authority and witness servers. An isolated, test-only in-memory signer and mutex-serialized consumed-step map tests both lanes, one-shot behavior, two racing consumers, expired/stale leases, wrong signer, lost acknowledgement, revoked/head drift during consumption and missing remote. No real scientific work or durable production artifact is created.

## Still required

An independently authenticated **linearizable** step-consumption service must enforce owner-epoch revocation and expiry atomically with its consumed-step ledger; receipt signatures alone cannot prove it. Worker isolation must ensure that **every external side effect** is mediated at the irreversible action boundary (not merely checked before calling an arbitrary action). Time sources, multiple nodes, crash/power-cut persistence, old-owner revocation, independent worker executable attestation, first-use state, CKB interlock and physical FSA deployment remain unqualified.

A network call followed by an arbitrary worker action is subject to time-of-check/time-of-use races. This increment only records a validated synthetic observation and **does not expose an execution callback or adapter**. It does not activate FORGE, touch CKB-plane/KTRADE or modify accepted scientific references.

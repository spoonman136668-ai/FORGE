# Hybrid GPU runner — disabled admission preview only

This FORGE package evaluates a **prospective** TTT-Hybrid-Lab GPU proposal,
without starting or reserving anything. It does not modify FORGE F139,
Wingless, Yggdrasil, TTT-Hybrid-Lab, scientific lifecycle, first-use custody,
schedulers, owner leases, or existing GitHub workflows.

## Grounded target

The Hybrid project owns the runner `TTT-HYBRID-GPU-WIN`, label
`ttt-hybrid-gpu-isolated`, and its own workflows. The source-only
`g7-existing-runner-admission.yml` is a protected-main, manual-only
**read-only inventory** workflow, *not* a general training entry point.
FORGE must not reuse FORGE, Wingless, or Yggdrasil runner labels or assume
repository access to this independent private project.

## What is checked

- Exact Hybrid repository, canonical PR URL, syntactic source and protocol
  pins, bounded original identity, correct dedicated runner label/name.
- One proposed GPU job maximum; requested VRAM from 1–4 GiB; prospective
  wall budget at most eight minutes. These are a **preview envelope**,
  not scientific model-training resource requirements or authorization.
- Caller-supplied host observation at most 60 seconds old, consistent
  GPU capacity, a 2 GiB *claimed* reservation for other research,
  1 GiB claimed safety margin, and no active foreign or Hybrid GPU jobs.
- Any recorded attempt for the same original ID, including
  `START_RISK`, `CONSUMED` or `QUARANTINED`, blocks planning. New
  original IDs do not retroactively clear old scientific first-use risk.
- All outputs explicitly deny dispatch, GPU reservation, independently
  authenticated origin, independent no-prior-attempt custody, and execution.

## What is NOT proven

Local observations and a supplied attempt-history array do **not** prove
complete custody, owner authority, global GPU fairness, available VRAM, or
actual absent concurrent workloads. A successful `REVIEW_ONLY` result is
**not a permit**. No method for dispatch, network access, CUDA, process
execution, queueing, signing, or resource reservation exists in this package.

Real activation requires separately authenticated project-scoped source and
original-first-use witnesses; a verified worker identity; durable, independent
GPU resource arbitration; exact-source full qualification; and the existing
FORGE authority's affirmative approval. Existing S24/S25 frozen science and
all independent research lanes remain untouched.

## Disabled evidence-reference handoff (engineering follow-up)

The pure `BuildDisabledHandoff` contract now binds an exact request hash,
a fully checked review status/reason, and syntactically valid source, protocol,
signed-attestation, artifact, signer-fingerprint and first-use ledger **references**.
All references are untrusted until independently authenticated at their
native sources. The produced `Handoff` explicitly requires independent source
and first-use witnesses and always denies execution, GPU reservation, and
source/first-use authentication.

The projected GPU capacity check now subtracts the other-project reserve
from both **total** and **currently free** VRAM, preserving a separate 1 GiB
safety margin. This deliberately rejects apparently available memory that
could already be reserved for Wingless/Yggdrasil or other work.

The report validator now accepts only exact known review reasons and bounded
attempt counts; arbitrary `BLOCKED` text is no longer accepted.

The read-only handoff is **not** the actual signed-evidence verifier from
draft PR #1565 and does not consume any source, API, GPU, secret, or scientific
first-use. It is an integration seam only and will require an independently
qualified real issuer/ledger/witness before any future execution handoff.

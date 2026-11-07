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

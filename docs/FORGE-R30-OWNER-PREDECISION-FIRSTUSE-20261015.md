# FORGE R30 — owner predecision → existing original first-use (source integration)

**Status:** Qualified owner-call-site library is being staged separately from the installed scientific owner. No live scientific original or genuine Dream-RSI optimizer trial was executed by this gate.

## What changed

The existing `originalclaim.Consume` implementation already durably consumes a *local* original once, but it has no evidence that a research policy was chosen before an outcome. R30 adds `originalclaim.ConsumeWithPredecision` as a **direct future owner call site**. It is not another GitHub observer, scheduler, signer, FSA, queue, or new scientific authority.

The prospective authorized owner supplies an exact original `Claim`, a signed `Predecision`, and **independently provided** immutable `PinnedTrust`:
- Exact experiment, source commit, intent, source/frozen identity, worker, run, lane, and owner epoch.
- Frozen research selection policy SHA-256, disjoint frozen four-baseline policy SHA-256s, candidate-set SHA-256, selected candidate SHA-256, actual logged probability (1–10,000 basis points), randomization-evidence SHA-256 and nonzero decision sequence.
- Existing owner and separately controlled witness Ed25519 signatures over the identical canonical event using a domain-separated signature format. Expected event digest and both trusted public keys arrive from **external pins**; they are never created or learned from the proposed worker record.

**Exact local order:** verify all identity pins and signatures; create a unique, write-once predecision record; fsync record and directory; call the existing `originalclaim.Consume` (which also fsyncs its write-once original-risk claim). Duplicate attempts, tampering, interrupted decision writes and source/epoch/candidate drift all **deny execution**. If predecision was written but the claim did not complete, the record is left in place and requires external investigation; never automatically retry.

`ReadPredecision` re-reads exact canonical signed predecision bytes, all external identity pins and the existing original first-use claim, but reports all scientific-authority booleans **false**.

## What this does *not* claim

This hook does **not** call any live original worker, modify CKB-plane, mutate accepted refs, change an existing R8/F2/E3 frozen historical workflow, or consume a genuinely new scientific original. The current `originalclaim` Go package is not yet invoked by the installed real-science owner controller; a passing package test is **not** live integration.

This hook proves cryptographic correspondence to caller-supplied keys, **not** that the witness private key is independently protected, that the event actually preceded a future outcome, that probability logging reflects true randomized choice, or that the local filesystem is a globally monotonic consumed-first-use ledger. The qualified external source-birth/high-water authority must still fence an actual original *before dispatch* and own the irrevocable first-use decision.

The historical six archived ZIPs and the F34–F37 train-only research cannot be upgraded to genuine Dream-RSI prospective history. Existing Cloudflare D1 holds guarded research archives; it is not redefined as an owner approval ledger. This change does not use D1 or change Cloudflare resource limits.

## Honest next operational step

The current separately authorized scientific owner must **adopt this exact native first-use call site** in its own genuinely active original-release path and supply its real, independent pinned keys, owner epoch and external first-use clearance. Before permitting any research execution, prove one original's actual signed predecision, exact external owner CAS and STARTED/TERMINAL evidence in the existing trusted owner. Only then allow fresh research trials and use R27's qualified four-baseline reader. Without a live owner call and authentic independent anchor, leave originals blocked; do not replace missing proof with another synthetic test or create a competing research controller.

## Qualification

Native Linux focused and full Go regression with race/vet/build; native Windows focused and one full regression/vet/build, all on exact candidate source. Test signatures are synthetic and are *not* scientific credentials. The PR stays draft/unmerged pending installation evidence and existing authority acceptance.

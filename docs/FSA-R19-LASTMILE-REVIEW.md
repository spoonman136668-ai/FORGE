# FORGE R19 — live native review, rules and last-mile source fence

**Foundation:** exact qualified R18 source `fad7d369c8454e9c760a945f06721b145865203a`, which incorporates qualified R17. R19 adds only a read-only preflight; the existing 10-minute scheduled source merge workflow is **unchanged and hard-disabled**.

## Real boundary

The GitHub repository currently has active ruleset **25031517**, `FORGE main qualified-source only`, protecting `refs/heads/main`: strict Linux and Windows GitHub Actions checks (integration 15368), merge method `merge` only, dismiss stale reviews, resolve threads, deletion and non-fast-forward restrictions, no bypass actors. GitHub itself requires zero approvals; FORGE's additional exact 40-hex-character GitHub-native Codex APPROVED review is therefore a separate, stronger project predicate, not a platform default.

The read-only collector `scripts/fsa_lastmile.py` reuses R18's native GitHub PR/review snapshot plus R17's Go decision, then obtains real GitHub PR and branch source metadata, enumerates and fetches the actual active branch ruleset, verifies its exact frozen policy, and **re-reads both source refs and rulesets** to reject concurrent drift. Unknown or additional rulesets, bypass/permission changes, missing CI contexts, changed review contract and base/head movement fail closed.

The separate REST branch-protection endpoint returns HTTP 403 under the linked GitHub installation. Accordingly, this gate **does not assert complete GitHub enforcement**, and cannot be an independent source-merge authorization; it only proves the observed ruleset contract.

## Qualification and authority

- Focused fake-transport tests cover exact native review provenance, identical source and base SHA before and after, restrictive rulesets, no bypasses, strict exact CI contexts and all fail-closed cases.
- The GitHub-hosted workflow runs a **genuine read-only** branch-ruleset/PR readback, but reports `NativeReviewQualified=false` if its current sampled draft PR lacks a full-head authentic approval. Do **not** turn fixture approval into a live attestation.
- One final Linux and Windows full Go regression is required for R19 exact head. CI is source qualification, not scientific acceptance.
- Always `MergeAuthorized=false`; even a hypothetical `WouldSatisfyObservedGate=true` is **not** a GitHub atomic merge guarantee. The active workflow still contains the hard `continue` gate.
- Before a future authorized merge, independently establish native full-head bot review on an eligible non-draft source PR, complete branch protections/rules, GitHub's final current-base/check/review status and a server-side merge with exact expected source SHA through the existing authorized authority. No scientific first-use, Cloudflare evidence, research optimizer, KTRADE or CKB-plane state changes are authorized by this work.

**R19 disposition:** Engineering source-only and read-only probes may pass while real independent approval/automatic merge authority remain blocked. Do not retire any research loop based on this gate.

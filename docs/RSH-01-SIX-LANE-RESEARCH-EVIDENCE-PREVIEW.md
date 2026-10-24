# FORGE RSH-01 — six-lane source-evidence preview (no execution)

**Owner-approved target:** one shared Mind-Palace memory, one FORGE research operations hub, six independent research/learning lanes, one North Star. Preserve active FORGE development and all original scientific custody.

## This bounded gate

`researchfeed.PreviewCandidates([]byte)` provides an **offline-only, source-index validation contract** for six lanes: Wingless, Yggdrasil, BIO, Optimizer Work, Mass Research, and Language Research. No scheduler, F139 dispatcher, background collection, new controller, Mind-Palace writer, paid model call, GitHub network request, direct CKB-plane access or protected-ref mutation is introduced.

Every input entry names a research ID, lane, allowed original-source repository, one 40-character immutable Git commit, relative source path, optionally a reported evidence SHA-256, observed outcome (including **NEGATIVE/MIXED/INVALID**), and explicit evidence-custody uncertainty. It is *untrusted indexing*, not original-source authentication. Source pointers or reported digests do not establish verified original bytes, first-use, scientific authority or live code.

All returned previews set `advisory_only=true` and **never** set scientific accepted, first-use cleared, execution authorized or original bytes authenticated. JSON input is bounded, strict and rejects duplicate/case-alias keys, unexpected execution/authority claims, ambiguous paths, CKB-plane/KTRADE sources and duplicate research IDs. Errors fail the new preview only and **must not halt previously qualified work**.

Wingless and Yggdrasil must use their own repositories for native source; BIO/Optimizer/Mass/Language can cite only permitted FORGE source paths or research archive paths in privately held Mind-Palace. This deliberately cannot read/cross-authenticate private bytes from public FORGE qualification. Preserve source custodians, independent sealed cohorts, unchanged original experiments and existing FSA guards.

## Qualification and next dependent step

Tests are in `researchfeed/preview_test.go`, covering six-lane results, record fidelity, deterministic selection, reported-hash limitations, source/path attacks, conflicting research claims, denied authority, duplicate keys and bounds. Reuse existing FORGE `.github/workflows/qualify.yml` full Linux+Windows source and race/integration regressions, plus Go vet and builds. Nothing is added to the existing automation.

This enables **an additive metadata input surface**, *not actual FSA admission*. Before activating any intake:
1. Qualify original raw evidence custody and source refs for each independent producer. Unresolved retention is explicit.
2. Wire a new eligible submission boundary through the **existing** FORGE FSA with authenticated signer, one-shot protocol custody, independent witness and original-source novelty controls.
3. Test that already-running Wingless/Yggdrasil FORGE F139 development continues unchanged, with no existing queue/work order altered.
4. Show one matched, reproducible gain in cross-lane scientific throughput or reduced human handoffs before program-wide activation. No auto acceptance from PR status, memory or reported hash.
5. Source-pin the unified North Star policy once private Mind-Palace governance PR #101 has protected qualification. FORGE's merged read-only `researchsteer` reader stays nonexecuting until a separate qualified planning boundary exists.

**At this gate:** Existing F139 two-lane feeder is enabled independently under FORGE's own operator scope. It is NOT expanded or modified by `researchfeed`.

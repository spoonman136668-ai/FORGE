# FORGE R5 — exact original science artifact inventory

Status: **real source bytes observed, scientific authority inactive.**

This implementation reads two previously completed *original* research artifacts; it does not execute or repeat either experiment.

| Lane | Run | Source Git commit | Raw SHA-256 | Reported finding |
|---|---|---|---|---|
| Wingless W-R39 | 38381594390 | ad3ade26204b14c372022bbed69dd59f91a3d02f | 33946f9f33d17539aadac42b05a4ebc4fb856dd3e5dafa8a4e43a11cdd5eb8e0 | NATIVE_VERIFIER_BOUNDARY; local mocked responses |
| Yggdrasil Y056 | 38381070805 | 7e61f1c234c21ff0617075bea40c39afa5d11e89 | 5ea4485afdeccd82e4d175eb01e56a696202d797a0136d21545ef568f7d9cd49 | NO_BENEFIT, preserved negative |

The manifest in `reference/research-originals/20261013-dual-lane-manifest.json` also pins each lane's exact GitHub artifact ID, name and inner filename. The package rejects mismatched bytes, substituted sources, malformed or duplicate top-level JSON classification fields, foreign lanes, and altered historical findings. It emits a complete **non-authorizing** report, retaining the negative class.

A read-only GitHub-hosted workflow compares the original run SHAs, retrieves the exact public archived files, verifies their bytes and preserves a bounded copy. Qualification requires Linux native tests/race/vet/build, Windows native tests/vet/build, and a separate successful real-artifact workflow run.

**Limits:** Two artifacts are not complete historical lineage. The current manifest is not an externally signed original-custody attestation; GitHub metadata and raw SHA do not prove frozen preregistration, source birth, sealed independence, first-use ownership or accepted scientific benefit. The collector returns `original_scientific_executions_authorized=false`, `scientific_accepted=false` and `accepted_ref_mutation=false`. No CKB/KTRADE access, science rerun, queue write or owner transfer occurs.

Next required operational gate: import the rest of the externally authenticated original-start/terminal evidence and CKB consumed ledger, reconcile S14 and then connect a qualified persistent two-lane controller to real scientific workers without duplicate original execution.

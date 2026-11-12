# FORGE F139 V41 consolidated development candidate

**Source-only; no original-owner installation, source event commit, policy
mutation, native dispatch, release issuance, scheduled task or scientific
first-use.** This is a review candidate, not owner authority.

## Frozen inputs

- Original live Windows owner: source `2c7caad5a4502d4b874a11d57207a35cf033eb08`, ledger event 1826 with hash `71fd4554315093d74f5a9968b4766191413cfd18d6b1ce81863f8451d379d769`, 153 verified, 56 quarantined and no admitted pending local tasks, documented in [read-only original owner run #43182527036](https://github.com/spoonman136668-ai/FORGE/actions/runs/43182527036).
- Catalog exact-200 fix merged: `main=7fb1bb9e0fe9439a6a7da8b66c6b0ef7acdc7595` via [PR #1719](https://github.com/spoonman136668-ai/FORGE/pull/1719); still not installed in the Windows task.
- Source transition / complete authenticated issue catalog / v36 SQLite replay: pinned [PR #1723](https://github.com/spoonman136668-ai/FORGE/pull/1723) candidate `704f409c63821acd11440218fc268911cb40d372`.
- Original unadmitted Yggdrasil issue #1715 source-bound preservation and optional *read-only* successor comparator: pinned [PR #1724](https://github.com/spoonman136668-ai/FORGE/pull/1724) candidate `62f292d14e4974c8a2e9981e964b386bc68c111e`.
- Original-owner cold-copy all-table/ZIP/binary manifest verifier: existing [PR #1722](https://github.com/spoonman136668-ai/FORGE/pull/1722).

## Integration and guarantees

The consolidated candidate uses one canonical `nci04_v41_catalog_recovery_preflight.py` to verify live original read-only SQLite/source/policy/provider identity. The old duplicate `nci04_v41_recovery_preflight.py` is removed. The cold-copy verifier calls the canonical original + source checks and additionally authenticates the externally created exact-run backup under the existing mutex: SQLite byte SHA-256, all-table logical state, spent event history, provider ZIPs and generator binary in **copy_files=False** mode. Its local fixtures never claim to be the original Windows ledger.

The v36 cold source-transition parser and Database.verify integrations are lifted unchanged from #1723. They verify event shape, predecessor source, original historical failures, spent calls and read-back lineage, but **provide no event writer, deployment CLI, transition approval, source policy update or activation**.

The separate #1715 read-only source-bound issue verifier and semantic reissue comparator are lifted unchanged from #1724. Neither creates nor authorizes a reissue. Original pending #1715 remains under its original source until a separately owner-authorized disposition.

## Mandatory remaining original gates

- Fresh original live task SID/lease/runner, current ledger head, all archives, exact main/candidate SHA and binary, owner-issued scoped approval, immutable release and source-bound negative controls.
- Genuine original Windows **offline** cold-copy replay with no history rewriting, plus restart/evidence-custody qualifications. Synthetic fixture CI is not acceptance.
- One guarded same-task source transition and explicit read-back. Reconcile pending #1715 without uncertain-effect replay. Original owner and designated integrator retain exclusive deployment and protected merge authority.
- Native scientific first-use and Hybrid admission remain denied.

The frozen V40 release agreement was for predecessor `42c70d74...` and must not be reused. Do not merge three independent overlapping source implementations; use one independently reviewed qualified candidate, with unmerged predecessor PRs closed or marked superseded only by their responsible owners.

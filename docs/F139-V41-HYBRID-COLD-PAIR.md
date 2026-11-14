# F139 V41 → public Hybrid: current-backup SQLite freshness

**Source-only; no owner execution or live release authorization.**

The original V41 owner is pinned to `1a40fe4e3ec6e93a1631d59863b95e90981d734e`.
Existing Hybrid source PR #1660 is pinned here to `788673aae2d1b42a0c9152395a866e910191cbdd`.
Both identifiers must be requalified if either source moves.

The older genuine V41 backup (run 43502062840) was captured at event 1826.
The new owner after V41 installation was observed at event 1829. Those are
**not the same recovery state**; never reuse the old preinstall backup to
justify the Hybrid release.

`f139/nci04_v41_hybrid_cold_pair.py` implements a bounded, source-pinned,
read-only SQLite component for a FUTURE authorized owner-created fresh backup.
It requires the genuine original query-only `Database` under its existing
`SingleOwner` kernel mutex; it verifies the original cold ledger, V41
identity, idle state and absence of Hybrid migration. It only accepts a
standalone owner-scoped backup file with no WAL/SHM/journal sidecars, snapshots
the opened bytes into private temporary storage, checks SQLite integrity and
**all logical tables**, and rechecks original and backup identity/bytes
before returning hashes. The authentic 1829-event floor is mandatory.

This proves only SQLite parity. A complete recoverable release additionally
requires **independent cold restore of provider ZIPs and generator binaries**,
backup producer and runner/SID/lease evidence, original policy and GitHub
authorization, protection of the new immutable worker ref, exact-source
Linux/Windows CI, a genuine V41-successor source ledger event writer and
rollback, an original-owner one-time schema migration, guarded three-lane
policy update and signed-worker readback. These are NOT performed by this
component. No scheduling, controller, queue, model training, first-use,
merge/promotion, live task pause or repository visibility edit is authorized.

The unit positive is synthetic parity only, not a claimed original Windows
acceptance receipt. In particular an offline copy and source CHECK do not
authorize live three-lane admission or scientific success.

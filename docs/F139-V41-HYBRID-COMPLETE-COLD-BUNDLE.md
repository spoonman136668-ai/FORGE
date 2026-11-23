# FORGE F139: current-V41 Hybrid complete cold backup + detached recovery (source only)

Baseline: protected FORGE V41 main and installed controller source
\`1a40fe4e3ec6e93a1631d59863b95e90981d734e\`. The earlier V41
pre-install bundle captured event 1826. The verified installed V41 owner was
at event 1829; previous bundle MUST NOT justify this successor.

The new source-only \`f139/nci04_v41_hybrid_cold_bundle.py\` reuses the existing
owner-SQLite online backup and V41 cold-custody readers, but binds to the exact
current public Hybrid PR #1660 head obtained from the authenticated native
provider. It rejects stale protected main or PR base, incorrectly leased or
writable original, running tasks, invalid native two-slot activation, migrated
schema, missing original ZIP/binary/negative custody, provider manifest drift,
SQLite WAL/SHM/journal sidecars, unlisted files, symlinks and path aliases.
The backup is create-only by run ID: a partial failure never becomes a reusable
sealed archive.

The sealed bundle contains the **current WAL-inclusive SQLite snapshot**, all
the existing immutable V2/V3 provider ZIP+manifest groups, the actual
V41-source generator binary, and the two historically negative original
custody ZIPs where applicable. Every file is individually SHA-256 bound and
the canonical manifest is separately anchored. Detached restoration verifies
the original full historical event chain and all logical tables twice in
independent scratch databases, with negative ZIPs restored into scratch
alongside the SQLite state; provider and generator archive bytes are checked.
No original database, original provider archive, or source checkout is
overwritten or restored in place. Stage requires existing original owner
SingleOwner lease; **task quiescence and owner SID remain caller obligations**.

Neither a synthetic positive nor a detached hash receipt proves a genuine
original Windows backup or grants live deployment. This source contains no
owner task controls, GitHub writes, issue POST, worker dispatch, protected
reference update, source-transition writer, schema migration, policy mutation,
science first-use, GPU training, or independent project execution.

Next distinct authorized gates: original owner task/SID/lease and backup
maintenance approval; actual owner-run fresh cold bundle and independent
restore receipt; protected source release ref and separately qualified V41
successor transition; original SQLite/policy migration; actual signed
three-lane development-worker receipts; later separate scientific evaluation.
Failure means **HOLD**, never replay or rollback an uncertain-effect action.

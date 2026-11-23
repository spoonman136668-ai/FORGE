# Per-catalog immutable commit identity reuse

Accepted baseline: `63ffa6394ec69adbc56ae5fe3b72d085cdbfff0a`.
Installed original owner remains `3dd63467d649a347692b6b42cd5074ff1038d3de`.

Original-host status42128990618/job127600501523 read the unchanged ledger1241
at23:22:12Z on2026-11-05. The first completed post-install tick,23:16:57Z,
failed F139_GITHUB_API_FAILED. Installation success does not prove resumed
development. The failing route/status is still unknown; this change does not
claim to resolve that failure.

The current public native-eligible catalog was independently read as100+35
issues. It referenced14 distinct repository/commit pairs; all14 Git commit
identities were independently readable. Multiplicities were
111,3,2,1,2,1,4,1,1,1,1,3,1,3. Mutable catalog observations are historical,
not an original-ledger admission receipt or immutable scientific cohort.

The accepted method fetched commit identity once per issue. The candidate
reuses only a validated `(repository, full commit SHA) -> tree SHA` within
one catalog call. Every issue body, source pin, owner identity, duplicate
check and historical ledger binding is still validated. Separate repositories
and commits never share entries; the map expires before the next call.
Malformed/missing provider evidence fails closed. No negative is cached.

A synthetic two-page control with that observed multiplicity exercised the
actual accepted method extracted from the pinned source and the candidate
method. Both returned identical135 typed records. Commit GETs fell135->14;
including catalog pages, total GETs fell137->16 (88.321% fewer). This is a
deterministic request-count result, not measured live latency, whole-cycle
speedup, improved qualification yield or scientific learning. Twelve focused
catalog tests passed, including repository/commit separation, per-call expiry,
mutable-body rejection after a reused identity, historical drift and duplicate
controls. Mandatory exact-candidate hosted regression remains required.

No original task, policy, database, source or release scope is changed by
this proposal. The consumed V37 release must never be replayed. No new
controller, worker, scheduler, paid API or scientific authority is introduced.

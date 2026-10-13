# Inactive original-to-worker integration rehearsal

The `shadowexecution` adapter closes a source-only integration gap between the durable signed first-use custody ledger and the existing fixed synthetic worker. It is **not** a generic scientific launcher.

The adapter enforces exact lane, frozen experiment, intent, original ID, owner epoch, fixed synthetic owner, expected public worker key, and new worker directory before any execution. It durably records irreversible custody **before** creating the directory or invoking the fixed worker. Once a reservation is written, any worker error, crash, cancellation or missing receipt leaves the original permanently non-replayable. A later original must have a new immutable experiment identity and separately qualified preregistration.

Native Linux/Windows tests demonstrate two synthetic runs for each of the original Wingless and Yggdrasil lane identities, signed start/terminal receipt verification, restart-resistant no-replay, and rejected worker-key preflight without original consumption.

**These are synthetic test computations, not new scientific results or real unattended research cycles.** They confer no FORGE execution authority, do not switch off CKB, and do not create research lanes. For actual science, an independently witnessed durable authority, real runner fence, sealed source cohort, authorized original worker integration, provenance and end-to-end scientific acceptance are still required. The private CKB first-use ledger, including ambiguous S14, must be reconciled before any controlled cutover.

# V19 next gate — original-owner read-only native-terminal authentication

**Review-only stacked on FORGE #1038 at source `9e28f316ab5d6eb4513e0742ca73e1af5443c73a`.**

This gate does not edit `f139/local_controller.py`, old free-reasoner limits, original SQLite, original Windows owner task, protected `main`, model source or FSA. It adds only an opt-in source-only adapter and tests. No new scheduler or queue.

The previous V19 shadow helper accepted a `chain_verified=true` flag in hypothetical input. That flag by itself is not a scientific or custody witness. An autonomous successor must learn about new authentic native terminal feedback **from the existing original SQLite event chain** before allocating even a future free-model request.

## Read-only trust boundary

`f139/nci04_v19_original_terminal_witness.py` requires an actual `f139.local_controller.Database` instance under its already-held `SingleOwner` mutex. It invokes the native original `db.verify()`, validating the original SHA chain, native source-authorized admission, owner event ancestry and relevant terminal/negative evidence. A fake object or caller-supplied `chain_verified` field is not accepted.

The adapter traces `NATIVE_DEVELOPMENT_ADMITTED` to the same ticket's `PROVIDER_VERIFIED_TERMINAL`, matches task identity, stage `VERIFIED`, lane, original source, native source path, training target commit, manifest, run ID, evidence SHA and original event order. It rejects duplicate terminal/admission, malformed source identity, non-authorable paths and missing owner custody. It refuses a terminal that predates or equals the last original `FREE_REASONER_ATTEMPTED` or `MODEL_DRAFT_ATTEMPTED` sequence, even when a new FORGE release SHA or UTC day appears. Pending work remains blocked.

When an authentically fresh terminal survives these checks, the adapter only computes the already inert V19 per-lane, budgeted advisory shadow. The original runtime remains unchanged. **Even positive projections always set** `owner_request_authorized=false`, `provider_requests=0`, `worker_dispatched=false`, `scientific_first_use=false`, `paid_model_calls=0`, `ledger_mutations=0`, `source_mutations=0`. There is no provider call, remote GitHub write, task dispatch, model update or acceptance authority.

## Not yet integrated

- This is NOT a readout from the live original Windows owner's SQLite. Tests use original source's isolated deterministic ledger fixtures; they cannot establish whether live new terminal feedback exists right now.
- Hypothetical V19 attempt rows still need an original-owner-only append-only custodian. Unverified external lists cannot authorize a production request. Future source must preserve all legacy free-reasoner attempt evidence and count ambiguous failures.
- The V18 combined release #1039 and protected release ref administrator operation remain independent prerequisites. This draft cannot replace their owner cutover and cannot be merged as a shortcut.
- For full autonomy, separately implement original-owner atomic attempt reservation **before** one public/free inference, verified model artifact publication, independent Windows/Linux qualification and FSA-scoped next-decision witness. Demonstrate repeated natural development cycles of both Wingless and Yggdrasil before any operational autonomy claim.

**Promotion disposition:** NO GO for live V19 provider, no authorization for scientific first-use; source-only shadow and negative regression tests.

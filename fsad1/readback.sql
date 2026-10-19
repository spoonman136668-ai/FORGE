-- Read-only structural readback; must be independently reconciled
-- with signed FSA archive, remote witness, monotonic high-water, and the
-- exact global all-lane ledger. Not a self-authorizing receipt.
SELECT cohort_sha256,intent_sha256,frozen_sha256,lane,archive_id,head_sha256,
       owner_epoch,ledger_generation,ledger_sha256,state
FROM forge_fsa_original_firstuse WHERE cohort_sha256=?1;

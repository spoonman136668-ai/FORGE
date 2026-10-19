-- Positional arguments, bound by the protected FSA authority ONLY:
-- 1 cohort SHA256; 2 intent SHA256; 3 frozen SHA256; 4 lane;
-- 5 archive ID; 6 authenticated head SHA256; 7 epoch;
-- 8 global ledger generation; 9 independently pinned global ledger SHA256.
-- A returned row is PENDING_WITNESS and is NOT an executable start receipt.
-- On no row, constraint failure, or ambiguous timeout: NEVER retry as a new
-- attempt, and NEVER dispatch a worker. Reconcile externally.
INSERT INTO original_firstuse
 (cohort_sha256,intent_sha256,frozen_sha256,lane,archive_id,head_sha256,
  owner_epoch,ledger_generation,ledger_sha256,state)
SELECT ?1,?2,?3,?4,?5,?6,?7,?8,?9,'RESERVED_PENDING_INDEPENDENT_WITNESS'
FROM authority_state
WHERE singleton=1 AND reservation_open=1
 AND archive_id=?5 AND head_sha256=?6
 AND owner_epoch=?7 AND ledger_generation=?8 AND ledger_sha256=?9
RETURNING cohort_sha256,intent_sha256,frozen_sha256,lane,
          archive_id,head_sha256,owner_epoch,ledger_generation,ledger_sha256,state;

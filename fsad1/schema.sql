-- FORGE FSA D1 pending first-use primitive. Not a science start authorization.
-- Initialize only within independently provisioned FSA custody after importing
-- the complete all-lane consumed/active and uncertain-start history.
-- The authority_state row is NOT self-attesting and MUST NOT be written by a worker.
CREATE TABLE authority_state (
 singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
 archive_id TEXT NOT NULL CHECK(length(archive_id)=64),
 head_sha256 TEXT NOT NULL CHECK(length(head_sha256)=64),
 owner_epoch INTEGER NOT NULL CHECK(owner_epoch > 0),
 ledger_generation INTEGER NOT NULL CHECK(ledger_generation > 0),
 ledger_sha256 TEXT NOT NULL CHECK(length(ledger_sha256)=64),
 reservation_open INTEGER NOT NULL CHECK(reservation_open IN (0, 1)),
 reservation_sequence INTEGER NOT NULL DEFAULT 0 CHECK(reservation_sequence >= 0)
) STRICT;

CREATE TABLE original_firstuse (
 cohort_sha256 TEXT PRIMARY KEY CHECK(length(cohort_sha256)=64),
 intent_sha256 TEXT NOT NULL UNIQUE CHECK(length(intent_sha256)=64),
 frozen_sha256 TEXT NOT NULL UNIQUE CHECK(length(frozen_sha256)=64),
 lane TEXT NOT NULL CHECK(lane IN ('Wingless','Yggdrasil')),
 archive_id TEXT NOT NULL CHECK(length(archive_id)=64),
 head_sha256 TEXT NOT NULL CHECK(length(head_sha256)=64),
 owner_epoch INTEGER NOT NULL CHECK(owner_epoch > 0),
 ledger_generation INTEGER NOT NULL CHECK(ledger_generation > 0),
 ledger_sha256 TEXT NOT NULL CHECK(length(ledger_sha256)=64),
 state TEXT NOT NULL CHECK(state='RESERVED_PENDING_INDEPENDENT_WITNESS')
) STRICT;

-- The exact insert and closing of the global reservation slot commit within
-- ONE SQLite statement. Another lane cannot consume the same pinned high-water
-- even with a different cohort, and unique indexes reject retries permanently.
CREATE TRIGGER close_global_slot_after_firstuse
AFTER INSERT ON original_firstuse
BEGIN
 UPDATE authority_state
 SET reservation_open=0, reservation_sequence=reservation_sequence+1
 WHERE singleton=1 AND reservation_open=1;
 SELECT CASE WHEN changes()!=1 THEN RAISE(ABORT,'FSA_GLOBAL_SLOT_NOT_OPEN') END;
END;

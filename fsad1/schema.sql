-- FORGE FSA D1 pending first-use primitive. Not a science start authorization.
-- Initialize only within independently provisioned FSA custody after importing
-- the complete all-lane consumed/active and uncertain-start history.
-- The forge_fsa_authority_state row is NOT self-attesting and MUST NOT be written by a worker.
CREATE TABLE forge_fsa_authority_state (
 singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
 archive_id TEXT NOT NULL CHECK(length(archive_id)=64 AND archive_id NOT GLOB '*[^0-9a-f]*'),
 head_sha256 TEXT NOT NULL CHECK(length(head_sha256)=64 AND head_sha256 NOT GLOB '*[^0-9a-f]*'),
 owner_epoch INTEGER NOT NULL CHECK(owner_epoch > 0),
 ledger_generation INTEGER NOT NULL CHECK(ledger_generation > 0),
 ledger_sha256 TEXT NOT NULL CHECK(length(ledger_sha256)=64 AND ledger_sha256 NOT GLOB '*[^0-9a-f]*'),
 reservation_open INTEGER NOT NULL CHECK(reservation_open IN (0, 1)),
 reservation_sequence INTEGER NOT NULL DEFAULT 0 CHECK(reservation_sequence >= 0)
) STRICT;

CREATE TABLE forge_fsa_original_firstuse (
 cohort_sha256 TEXT PRIMARY KEY CHECK(length(cohort_sha256)=64 AND cohort_sha256 NOT GLOB '*[^0-9a-f]*'),
 intent_sha256 TEXT NOT NULL UNIQUE CHECK(length(intent_sha256)=64 AND intent_sha256 NOT GLOB '*[^0-9a-f]*'),
 frozen_sha256 TEXT NOT NULL UNIQUE CHECK(length(frozen_sha256)=64 AND frozen_sha256 NOT GLOB '*[^0-9a-f]*'),
 lane TEXT NOT NULL CHECK(lane IN ('Wingless','Yggdrasil')),
 archive_id TEXT NOT NULL CHECK(length(archive_id)=64 AND archive_id NOT GLOB '*[^0-9a-f]*'),
 head_sha256 TEXT NOT NULL CHECK(length(head_sha256)=64 AND head_sha256 NOT GLOB '*[^0-9a-f]*'),
 owner_epoch INTEGER NOT NULL CHECK(owner_epoch > 0),
 ledger_generation INTEGER NOT NULL CHECK(ledger_generation > 0),
 ledger_sha256 TEXT NOT NULL CHECK(length(ledger_sha256)=64 AND ledger_sha256 NOT GLOB '*[^0-9a-f]*'),
 state TEXT NOT NULL CHECK(state='RESERVED_PENDING_INDEPENDENT_WITNESS')
) STRICT;

-- The exact insert and closing of the global reservation slot commit within
-- ONE SQLite statement. Another lane cannot consume the same pinned high-water
-- even with a different cohort, and unique indexes reject retries permanently.
CREATE TRIGGER forge_fsa_close_global_slot_after_firstuse
AFTER INSERT ON forge_fsa_original_firstuse
BEGIN
 UPDATE forge_fsa_authority_state
 SET reservation_open=0, reservation_sequence=reservation_sequence+1
 WHERE singleton=1 AND reservation_open=1;
 SELECT CASE WHEN changes()!=1 THEN RAISE(ABORT,'FSA_GLOBAL_SLOT_NOT_OPEN') END;
END;

-- First-use records are irreversible. A repaired source, restored database,
-- mutable administrator or UPDATE/DELETE query cannot silently recycle them.
CREATE TRIGGER forge_fsa_no_update_firstuse
BEFORE UPDATE ON forge_fsa_original_firstuse
BEGIN
 SELECT RAISE(ABORT,'FSA_FIRSTUSE_APPEND_ONLY_NO_UPDATE');
END;
CREATE TRIGGER forge_fsa_no_delete_firstuse
BEFORE DELETE ON forge_fsa_original_firstuse
BEGIN
 SELECT RAISE(ABORT,'FSA_FIRSTUSE_APPEND_ONLY_NO_DELETE');
END;
-- INSERT OR REPLACE must not erase an existing reserved identity even if
-- recursive_triggers is disabled. Distinct identity columns are ALL global.
CREATE TRIGGER forge_fsa_no_replace_firstuse
BEFORE INSERT ON forge_fsa_original_firstuse
WHEN EXISTS(
 SELECT 1 FROM forge_fsa_original_firstuse
 WHERE cohort_sha256=NEW.cohort_sha256
    OR intent_sha256=NEW.intent_sha256
    OR frozen_sha256=NEW.frozen_sha256
)
BEGIN
 SELECT RAISE(ABORT,'FSA_FIRSTUSE_IDENTITY_REPLAY');
END;

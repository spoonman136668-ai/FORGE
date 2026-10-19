-- T16-E OPTIONAL D1/SQLite schema candidate: NOT deployed or applied to live DB.
-- Single INSERT is a SQLite atomic constraint gate; do NOT use a Worker
-- read-then-write to decide the next sequence. Pre-verify dual independent
-- signatures and source/custody pins externally before issuing the INSERT.
-- D1 privileged writers can DROP/REPLACE objects: database uniqueness alone
-- does NOT prove independent signer custody or immutable storage.
CREATE TABLE IF NOT EXISTS t16e_source_firstuse (
 lane TEXT NOT NULL CHECK (lane IN ('Wingless','Yggdrasil','MassResearch')),
 original_id TEXT NOT NULL CHECK (length(original_id) BETWEEN 3 AND 80),
 sequence INTEGER NOT NULL CHECK (sequence >= 1),
 external_tree_sha TEXT NOT NULL CHECK (length(external_tree_sha) = 40),
 source_sha256 TEXT NOT NULL CHECK (length(source_sha256) = 64),
 prereg_sha256 TEXT NOT NULL CHECK (length(prereg_sha256) = 64),
 cohort_sha256 TEXT NOT NULL CHECK (length(cohort_sha256) = 64),
 birth_sha256 TEXT NOT NULL CHECK (length(birth_sha256) = 64),
 issuer_key_sha256 TEXT NOT NULL CHECK (length(issuer_key_sha256) = 64),
 witness_key_sha256 TEXT NOT NULL CHECK (length(witness_key_sha256) = 64),
 prior_receipt_sha256 TEXT NOT NULL CHECK (length(prior_receipt_sha256) = 64),
 receipt_sha256 TEXT NOT NULL CHECK (length(receipt_sha256) = 64),
 PRIMARY KEY (lane, original_id),
 UNIQUE (lane, sequence),
 CHECK (issuer_key_sha256 <> witness_key_sha256)
);
CREATE TRIGGER IF NOT EXISTS t16e_source_firstuse_monotonic
BEFORE INSERT ON t16e_source_firstuse
BEGIN
 SELECT CASE WHEN NEW.sequence <>
   COALESCE((SELECT MAX(sequence)
       FROM t16e_source_firstuse WHERE lane=NEW.lane),0)+1
   THEN RAISE(ABORT,'T16E_NONMONOTONE_SOURCE_FIRSTUSE') END;
 SELECT CASE WHEN NEW.prior_receipt_sha256 <>
   COALESCE((SELECT receipt_sha256 FROM t16e_source_firstuse
       WHERE lane=NEW.lane ORDER BY sequence DESC LIMIT 1),
       '0000000000000000000000000000000000000000000000000000000000000000')
   THEN RAISE(ABORT,'T16E_SOURCE_FIRSTUSE_HISTORY_DRIFT') END;
END;
CREATE TRIGGER IF NOT EXISTS t16e_source_firstuse_no_update
BEFORE UPDATE ON t16e_source_firstuse
BEGIN
 SELECT RAISE(ABORT,'T16E_SOURCE_FIRSTUSE_APPEND_ONLY');
END;
CREATE TRIGGER IF NOT EXISTS t16e_source_firstuse_no_delete
BEFORE DELETE ON t16e_source_firstuse
BEGIN
 SELECT RAISE(ABORT,'T16E_SOURCE_FIRSTUSE_APPEND_ONLY');
END;

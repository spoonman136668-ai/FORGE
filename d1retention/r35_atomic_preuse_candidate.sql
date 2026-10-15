-- R35 separate existing-D1 minimal once-only atomic original reservation.
-- CANDIDATE ONLY: never installs itself and never authorizes scientific execution.
-- Requires separate owner/witness signature validation and trusted worker identity.
CREATE TABLE IF NOT EXISTS forge_original_preuse_claims (
  original_key_sha256 TEXT PRIMARY KEY NOT NULL
    CHECK(length(original_key_sha256)=64 AND original_key_sha256 NOT GLOB '*[^0-9a-f]*'),
  lane TEXT NOT NULL CHECK(lane IN ('Wingless','Yggdrasil')),
  owner_epoch INTEGER NOT NULL CHECK(owner_epoch>0),
  source_commit_sha TEXT NOT NULL
    CHECK(length(source_commit_sha)=40 AND source_commit_sha NOT GLOB '*[^0-9a-f]*'),
  frozen_predecision_sha256 TEXT NOT NULL
    CHECK(length(frozen_predecision_sha256)=64 AND frozen_predecision_sha256 NOT GLOB '*[^0-9a-f]*'),
  external_owner_witness_pin_sha256 TEXT NOT NULL
    CHECK(length(external_owner_witness_pin_sha256)=64 AND external_owner_witness_pin_sha256 NOT GLOB '*[^0-9a-f]*'),
  claimed_sequence INTEGER NOT NULL UNIQUE CHECK(claimed_sequence>0),
  scientific_authorized INTEGER NOT NULL DEFAULT 0 CHECK(scientific_authorized=0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER IF NOT EXISTS forge_original_preuse_claims_update_immutable
BEFORE UPDATE ON forge_original_preuse_claims
BEGIN SELECT RAISE(ABORT,'FORGE_R35_CLAIM_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS forge_original_preuse_claims_delete_immutable
BEFORE DELETE ON forge_original_preuse_claims
BEGIN SELECT RAISE(ABORT,'FORGE_R35_CLAIM_IMMUTABLE'); END;

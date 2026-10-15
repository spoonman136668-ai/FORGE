-- R38 isolated additive guard for R35 candidate; NOT DEPLOYED.
-- Unique sequence is insufficient: deny all backwards sequence/epoch writes.
-- Works only within one shared D1/SQLite database, not an external permit.
CREATE TRIGGER IF NOT EXISTS forge_original_preuse_claims_insert_monotonic
BEFORE INSERT ON forge_original_preuse_claims
WHEN EXISTS (
  SELECT 1 FROM forge_original_preuse_claims
  WHERE original_key_sha256 = NEW.original_key_sha256
     OR claimed_sequence >= NEW.claimed_sequence
     OR owner_epoch > NEW.owner_epoch
)
BEGIN
  SELECT RAISE(ABORT,'FORGE_R38_NONMONOTONIC_OR_REPLAYED_FIRST_USE');
END;

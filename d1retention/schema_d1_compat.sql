-- R18B proposed Cloudflare D1 compatibility profile.
-- Reuses the EXISTING D1 database and never edits its existing user table.
-- This is a *structural staging schema*, NOT a qualified append-only archive:
-- its privileged SQL account can UPDATE/DELETE records because immutable
-- SQLite triggers are intentionally excluded from this isolated candidate.
-- Source hashes, independently pinned original bytes, first-use evidence and
-- separate write-path controls are required BEFORE preservation claims.
-- Installing these tables MUST NOT enable optimizer dispatch or accept science.
-- FORGE existing-Cloudflare D1 archive *candidate*, offline qualified only.
-- Apply to the operator's existing database ONLY after explicit identity,
-- schema-collision and authenticated-source acceptance checks. Never treat a
-- successful SQL migration as independent scientific custody.
-- The archive is raw original-byte preservation, not an FSA or scheduler.
CREATE TABLE forge_research_originals (
  archive_sha256 TEXT PRIMARY KEY NOT NULL
    CHECK(length(archive_sha256)=64 AND archive_sha256 NOT GLOB '*[^0-9a-f]*'),
  lane TEXT NOT NULL CHECK(lane IN ('Wingless','Yggdrasil')),
  experiment TEXT NOT NULL CHECK(length(experiment) BETWEEN 1 AND 128),
  repository TEXT NOT NULL
    CHECK(repository IN ('spoonman136668-ai/Wingless','spoonman136668-ai/Yggdrasil')),
  run_id INTEGER NOT NULL CHECK(run_id>0),
  artifact_id INTEGER NOT NULL CHECK(artifact_id>0),
  source_sha TEXT NOT NULL CHECK(length(source_sha)=40 AND source_sha NOT GLOB '*[^0-9a-f]*'),
  frozen_manifest_sha256 TEXT NOT NULL
    CHECK(length(frozen_manifest_sha256)=64 AND frozen_manifest_sha256 NOT GLOB '*[^0-9a-f]*'),
  original_length INTEGER NOT NULL CHECK(original_length BETWEEN 1 AND 4194304),
  chunk_count INTEGER NOT NULL CHECK(chunk_count BETWEEN 1 AND 64),
  scientific_state TEXT NOT NULL DEFAULT 'UNQUALIFIED'
    CHECK(scientific_state='UNQUALIFIED'),
  UNIQUE(lane,experiment),
  UNIQUE(repository,run_id,artifact_id),
  CHECK((lane='Wingless' AND repository='spoonman136668-ai/Wingless') OR
        (lane='Yggdrasil' AND repository='spoonman136668-ai/Yggdrasil'))
);
CREATE TABLE forge_research_chunks (
  archive_sha256 TEXT NOT NULL REFERENCES forge_research_originals(archive_sha256),
  chunk_index INTEGER NOT NULL CHECK(chunk_index BETWEEN 0 AND 63),
  chunk_sha256 TEXT NOT NULL
    CHECK(length(chunk_sha256)=64 AND chunk_sha256 NOT GLOB '*[^0-9a-f]*'),
  chunk_bytes BLOB NOT NULL
    CHECK(length(chunk_bytes) BETWEEN 1 AND 65536),
  PRIMARY KEY(archive_sha256,chunk_index)
);
CREATE TABLE forge_research_seals (
  archive_sha256 TEXT PRIMARY KEY NOT NULL
    REFERENCES forge_research_originals(archive_sha256),
  declared_restored_sha256 TEXT NOT NULL
    CHECK(length(declared_restored_sha256)=64 AND
          declared_restored_sha256 NOT GLOB '*[^0-9a-f]*'),
  declared_restored_length INTEGER NOT NULL CHECK(declared_restored_length>0),
  seal_receipt_sha256 TEXT NOT NULL
    CHECK(length(seal_receipt_sha256)=64 AND seal_receipt_sha256 NOT GLOB '*[^0-9a-f]*'),
  CHECK(declared_restored_sha256=archive_sha256)
);

"""F63 — isolated *local* one-use CKB/FORGE D1 claim simulator.

A durable SQLite first-use INSERT is NOT a scientific approval. This module
has no Cloudflare SDK, Worker route, network, signer, scheduler, or live path.
All callers must keep real owner custody, leased seeds, and execution blocked.
"""
from __future__ import annotations
from dataclasses import dataclass
import re
import sqlite3

import f62_firstuse_readonly as f62

HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
SCHEMA = "forge.f63.local-onceonly-worker-fence-simulation.v1"
SQL = ("INSERT INTO forge_original_preuse_claims "
       "(original_key_sha256,lane,owner_epoch,source_commit_sha,"
       "frozen_predecision_sha256,external_owner_witness_pin_sha256,"
       "claimed_sequence,scientific_authorized) "
       "VALUES (?,?,?,?,?,?,?,0)")
class Denied(ValueError): pass

def reject_if_not(ok: bool, code: str) -> None:
    if not ok: raise Denied("F63_" + code)

@dataclass(frozen=True)
class Candidate:
    original_key_sha256: str
    lane: str
    owner_epoch: int
    source_commit_sha: str
    frozen_predecision_sha256: str
    external_owner_witness_pin_sha256: str
    claimed_sequence: int
    scientific_authorized: bool = False

@dataclass(frozen=True)
class FrozenLocalTestPins:
    # These are fixture comparisons, not real independent custody or science.
    original_key_sha256: str
    lane: str
    owner_epoch: int
    source_commit_sha: str
    frozen_predecision_sha256: str
    external_owner_witness_pin_sha256: str
    claimed_sequence: int

def validate(c: Candidate, p: FrozenLocalTestPins) -> None:
    reject_if_not(type(c) is Candidate and type(p) is FrozenLocalTestPins,
                  "EXACT_INPUT_SHAPES_REQUIRED")
    reject_if_not(c.lane in ("Wingless", "Yggdrasil") and
                  c.scientific_authorized is False, "NO_SCIENTIFIC_AUTHORITY")
    reject_if_not(type(c.owner_epoch) is int and 0 < c.owner_epoch < 2**63 and
                  type(c.claimed_sequence) is int and
                  0 < c.claimed_sequence < 2**63, "MONOTONIC_VALUES_INVALID")
    reject_if_not(type(c.original_key_sha256) is str and
                  HEX64.fullmatch(c.original_key_sha256) is not None and
                  type(c.source_commit_sha) is str and
                  HEX40.fullmatch(c.source_commit_sha) is not None and
                  type(c.frozen_predecision_sha256) is str and
                  HEX64.fullmatch(c.frozen_predecision_sha256) is not None and
                  type(c.external_owner_witness_pin_sha256) is str and
                  HEX64.fullmatch(c.external_owner_witness_pin_sha256) is not None,
                  "FROZEN_SOURCE_OR_PREDECISION_INVALID")
    reject_if_not(all(getattr(c, key) == getattr(p, key)
                      for key in p.__dataclass_fields__),
                  "LOCAL_TEST_PIN_DRIFT")

def require_exact_local_schema(db: sqlite3.Connection) -> None:
    """Reject missing/rewritten immutability or monotonic triggers *inside* lock.

    Source-derived definitions are only a LOCAL qualification. This cannot
    attest the deployed Cloudflare Worker or the currently serving D1 schema.
    """
    require=db.execute(
        "SELECT name,type,tbl_name,sql FROM sqlite_master "
        "WHERE name LIKE 'forge_original_preuse_%' ORDER BY name").fetchall()
    statements, _ = f62.migration_sql()
    with sqlite3.connect(":memory:") as expected:
        expected.executescript("\n".join(statements))
        wanted=expected.execute(
            "SELECT name,type,tbl_name,sql FROM sqlite_master "
            "WHERE name LIKE 'forge_original_preuse_%' ORDER BY name").fetchall()
    reject_if_not(len(require)==4 and require==wanted,
                  "EXACT_LOCAL_FIRSTUSE_GUARDS_MISSING_OR_CHANGED")

def install_isolated_test_schema(db: sqlite3.Connection) -> str:
    """Local SQLite only; never modifies a bound or deployed Cloudflare D1."""
    reject_if_not(type(db) is sqlite3.Connection, "LOCAL_SQLITE_REQUIRED")
    sql, digest = f62.migration_sql()
    reject_if_not(len(sql) == 4 and type(digest) is str and
                  HEX64.fullmatch(digest) is not None, "R35_R38_SOURCE_UNQUALIFIED")
    existing = db.execute("SELECT name FROM sqlite_master "
                         "WHERE name LIKE 'forge_original_preuse_%'").fetchall()
    reject_if_not(not existing, "TEST_SCHEMA_ALREADY_PRESENT")
    db.executescript("\n".join(sql))
    return digest

def local_attempt_once(db: sqlite3.Connection, c: Candidate,
                       pins: FrozenLocalTestPins) -> dict:
    """One *durable* local SQL transaction. Failure or uncertainty never grants retry.

    The irreversible INSERT records consumed intent only. The returned report
    is a diagnosis, not a token/permit or command to execute. The caller has
    no way to mark scientific_authorized=1 under R35.
    """
    reject_if_not(type(db) is sqlite3.Connection, "LOCAL_SQLITE_REQUIRED")
    validate(c, pins)
    reject_if_not(db.in_transaction is False, "UNEXPECTED_OPEN_TRANSACTION")
    try:
        db.execute("BEGIN IMMEDIATE")
        require_exact_local_schema(db)
        db.execute(SQL, (
            c.original_key_sha256, c.lane, c.owner_epoch,
            c.source_commit_sha, c.frozen_predecision_sha256,
            c.external_owner_witness_pin_sha256, c.claimed_sequence))
        # Exactly one atomic COMMIT. A lost acknowledgement cannot be retried:
        # a replay MUST hit the real durable unique/monotonic guards.
        db.commit()
    except (sqlite3.Error, Denied) as exc:
        # If a connection fails after a COMMIT, the result is uncertain; the
        # consumer must reconcile durable state and NEVER retry by itself.
        try: db.rollback()
        except sqlite3.Error: pass
        raise Denied("F63_LOCAL_ATTEMPT_FAILED_OR_UNCERTAIN_NO_RETRY") from exc
    return {
        "schema": SCHEMA, "lane": c.lane,
        "sandbox_intent_irrevocably_consumed": True,
        "external_cloudflare_firstuse_consumed": False,
        "independently_approved_owner_and_history_verified": False,
        "worker_scope_permit_issued": False,
        "real_scientific_execution_authorized": False,
        "originals_dispatched": 0,
        "owner_cutover_authorized": False,
        "disposition": "LOCAL_SQLITE_SIMULATION_ONLY_NO_RESEARCH_PERMIT",
    }

def inspect_local_consumption(db: sqlite3.Connection, key: str) -> tuple:
    """Read-only re-open inspection for crash/restart fault injection."""
    reject_if_not(type(db) is sqlite3.Connection and type(key) is str and
                  HEX64.fullmatch(key) is not None, "LOCAL_READ_INVALID")
    row = db.execute("SELECT original_key_sha256,lane,owner_epoch,"
                     "source_commit_sha,frozen_predecision_sha256,"
                     "external_owner_witness_pin_sha256,claimed_sequence,"
                     "scientific_authorized "
                     "FROM forge_original_preuse_claims "
                     "WHERE original_key_sha256=?", (key,)).fetchall()
    reject_if_not(len(row) <= 1, "DURABLE_DUPLICATE_CORRUPTION")
    return tuple(row)

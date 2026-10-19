"""F139 integration gate for existing Cloudflare D1: LOCAL SQLite compatibility only.

Never connects to the live D1, accesses keys, imports real history or
creates a scientific worker permit. The archive contents below are synthetic
and do not stand in for the six authenticated actual Cloudflare originals.
"""
from __future__ import annotations
import hashlib
import pathlib
import sqlite3
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCHEMA = (HERE / "schema.sql").read_text(encoding="utf-8")
RESERVE = (HERE / "reserve_pending.sql").read_text(encoding="utf-8")
FSA_NAMES = frozenset((
    "forge_fsa_authority_state", "forge_fsa_original_firstuse",
    "forge_fsa_close_global_slot_after_firstuse",
    "forge_fsa_no_update_firstuse", "forge_fsa_no_delete_firstuse",
    "forge_fsa_no_replace_firstuse",
))

def existing_archive():
    """A minimal fixture with the *previously deployed* FORGE namespace."""
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE operator_settings (name TEXT PRIMARY KEY, value BLOB NOT NULL)")
    db.execute("INSERT INTO operator_settings VALUES (?,?)", ("account", b"private-original-settings"))
    # Deliberate exact collisions against the PREVIOUS unprefixed F139 DDL.
    db.execute("CREATE TABLE authority_state (key TEXT PRIMARY KEY, value TEXT)")
    db.execute("INSERT INTO authority_state VALUES ('existing','important')")
    db.execute("CREATE TABLE original_firstuse (id INTEGER PRIMARY KEY, note TEXT)")
    db.execute("INSERT INTO original_firstuse VALUES (1,'existing user data')")
    db.executescript("""
    CREATE TABLE forge_research_originals (
        archive_sha256 TEXT PRIMARY KEY, lane TEXT NOT NULL,
        original_bytes BLOB NOT NULL);
    CREATE TABLE forge_research_chunks (
        archive_sha256 TEXT, chunk_index INTEGER, chunk_bytes BLOB,
        PRIMARY KEY (archive_sha256,chunk_index));
    CREATE TABLE forge_research_seals (
        archive_sha256 TEXT PRIMARY KEY, seal_receipt_sha256 TEXT NOT NULL);
    CREATE TRIGGER forge_research_originals_immutable
      BEFORE DELETE ON forge_research_originals
      BEGIN SELECT RAISE(ABORT,'ARCHIVE_IMMUTABLE'); END;
    """)
    for i in range(6):
        payload = ("synthetic-test-only-original-%d" % i).encode()
        digest = hashlib.sha256(payload).hexdigest()
        lane = "Wingless" if i % 2 else "Yggdrasil"
        db.execute("INSERT INTO forge_research_originals VALUES (?,?,?)",
                   (digest, lane, payload))
        db.execute("INSERT INTO forge_research_chunks VALUES (?,?,?)",
                   (digest, 0, payload))
        db.execute("INSERT INTO forge_research_seals VALUES (?,?)",
                   (digest, hashlib.sha256(b"seal-"+payload).hexdigest()))
    db.commit()
    return db

def old_snapshot(db):
    ddls = tuple(db.execute(
        "SELECT type,name,sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' AND name NOT GLOB 'forge_fsa_*' "
        "ORDER BY type,name"))
    tables = {}
    for name in ("operator_settings", "authority_state", "original_firstuse",
                 "forge_research_originals", "forge_research_chunks",
                 "forge_research_seals"):
        tables[name] = tuple(db.execute('SELECT * FROM "' + name + '" ORDER BY 1'))
    return ddls, tables

class ExistingD1MigrationCompatibility(unittest.TestCase):
    def setUp(self):
        self.db = existing_archive()
        self.addCleanup(self.db.close)

    def test_additive_migration_preserves_existing_archive_and_user_data(self):
        before = old_snapshot(self.db)
        self.db.executescript(SCHEMA)
        self.assertEqual(old_snapshot(self.db), before)
        self.assertEqual(set(row[0] for row in self.db.execute(
            "SELECT name FROM sqlite_master WHERE name GLOB 'forge_fsa_*'")),
            FSA_NAMES)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM forge_fsa_authority_state").fetchone()[0], 0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM forge_fsa_original_firstuse").fetchone()[0], 0)
        # Empty authority is intentional. Even valid-looking input must not
        # automatically create an irreversible first-use or open a slot.
        args = {str(i+1): val for i,val in enumerate((
            "a"*64, "b"*64, "c"*64, "Wingless",
            "d"*64, "e"*64, 1, 1, "f"*64))}
        self.assertEqual(self.db.execute(RESERVE, args).fetchall(), [])
        self.assertEqual(old_snapshot(self.db), before)

    def test_schema_replay_denied_without_changing_previous_content(self):
        self.db.executescript(SCHEMA)
        before = old_snapshot(self.db)
        fsa_objects = tuple(self.db.execute(
            "SELECT type,name,sql FROM sqlite_master "
            "WHERE name GLOB 'forge_fsa_*' ORDER BY type,name"))
        with self.assertRaises(sqlite3.OperationalError):
            self.db.executescript(SCHEMA)
        self.assertEqual(old_snapshot(self.db), before)
        self.assertEqual(tuple(self.db.execute(
            "SELECT type,name,sql FROM sqlite_master "
            "WHERE name GLOB 'forge_fsa_*' ORDER BY type,name")),fsa_objects)

    def test_existing_fsa_namespace_collision_denied(self):
        self.db.execute("CREATE TABLE forge_fsa_authority_state (x TEXT)")
        previous = old_snapshot(self.db)
        with self.assertRaises(sqlite3.OperationalError):
            self.db.executescript(SCHEMA)
        self.assertEqual(old_snapshot(self.db), previous)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM forge_fsa_authority_state").fetchone()[0], 0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE name='forge_fsa_original_firstuse'").fetchone()[0], 0)

    def test_prior_archived_seals_are_immutable(self):
        before = old_snapshot(self.db)
        self.db.executescript(SCHEMA)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM forge_research_originals")
        self.assertEqual(old_snapshot(self.db), before)

if __name__ == "__main__":
    unittest.main()

"""Controlled prototype: run original fixture tests with fresh SQLite DB creation.

This never changes production Database.initialize. Use in separate processes:
  python -B f139_sqlite_fixture_prototype.py --mode original
  python -B f139_sqlite_fixture_prototype.py --mode backup

Every test receives a newly-created, unique writable database path. The
experimental mode only changes how the pristine schema is materialized.
"""
import argparse
import re
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

from f139.local_controller import Database, SCHEMA, ZERO

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "f139" / "local_schema.sql"
META_SQL = (
    "INSERT INTO meta(id,schema,source_sha,epoch,enabled,legacy_suspended,"
    "day,starts,head_seq,head_hash) VALUES(1,?,?,1,0,0,'1970-01-01',0,0,?)"
)
TARGETS = (
    "test_nci04_owner_ledger.py",
    "test_nci04_g32_owner_custody.py",
)


def make_backup_initializer(template):
    seen = set()

    def initialize(cls, filename, source_sha):
        path = Path(filename)
        if not isinstance(source_sha, str) or not re.fullmatch(r"[a-f0-9]{40}", source_sha):
            raise ValueError("F139_G114I_SOURCE_SHA_INVALID")
        if path.exists():
            raise FileExistsError("F139_G114I_REFUSE_EXISTING_DATABASE")
        identity = str(path.resolve())
        if identity in seen:
            raise AssertionError("F139_G114I_DATABASE_PATH_REUSED")
        seen.add(identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        destination = sqlite3.connect(str(path), isolation_level=None, timeout=10)
        try:
            template.backup(destination)
            destination.execute("PRAGMA synchronous=FULL")
            destination.execute(META_SQL, (SCHEMA, source_sha, ZERO))
        finally:
            destination.close()
        # Use the authoritative constructor: fresh connection, busy timeout,
        # synchronous=FULL, foreign_keys, WAL, and complete original verify().
        return cls(path)

    return initialize, seen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("original", "backup"), required=True)
    args = parser.parse_args()

    original_initialize = Database.initialize
    template = None
    if args.mode == "backup":
        template = sqlite3.connect(":memory:", isolation_level=None)
        template.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        replacement, seen_paths = make_backup_initializer(template)
        Database.initialize = classmethod(replacement)
    else:
        seen_paths = set()

    init_paths = []
    def counted_initialize(filename, source_sha):
        path = str(Path(filename).resolve())
        if path in init_paths:
            raise AssertionError("F139_G114I_DATABASE_PATH_REUSED")
        init_paths.append(path)
        if args.mode == "original":
            return original_initialize(filename, source_sha)
        return Database.initialize(filename, source_sha)

    # In original mode, count calls while preserving the exact original
    # classmethod. In backup mode, the replacement already enforces uniqueness.
    if args.mode == "original":
        def tracked(cls, filename, source_sha):
            return counted_initialize(filename, source_sha)
        Database.initialize = classmethod(tracked)

    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for pattern in TARGETS:
        suite.addTests(loader.discover(start_dir=str(ROOT / "f139"), pattern=pattern))
    discovered = suite.countTestCases()
    started = time.perf_counter()
    try:
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        elapsed = time.perf_counter() - started
        init_count = len(init_paths) if args.mode == "original" else len(seen_paths)
        if args.mode == "backup" and init_count != len(init_paths):
            raise AssertionError("F139_G114I_PATH_ACCOUNTING_MISMATCH")
        if result.testsRun != discovered:
            raise AssertionError("F139_G114I_TEST_COUNT_MISMATCH")
        print(f"F139_G114I_MODE={args.mode}")
        print(f"F139_G114I_DISCOVERED={discovered}")
        print(f"F139_G114I_EXECUTED={result.testsRun}")
        print(f"F139_G114I_SKIPPED={len(result.skipped)}")
        print(f"F139_G114I_DB_INITIALIZE_CALLS={init_count}")
        print(f"F139_G114I_UNIQUE_WRITABLE_DATABASES={init_count}")
        print(f"F139_G114I_WALL_SECONDS={elapsed:.6f}")
        print(f"F139_G114I_RESULT={'PASS' if result.wasSuccessful() else 'FAIL'}")
        return 0 if result.wasSuccessful() else 1
    finally:
        Database.initialize = original_initialize.__func__ if hasattr(original_initialize, "__func__") else original_initialize
        if template is not None:
            template.close()


if __name__ == "__main__":
    sys.exit(main())

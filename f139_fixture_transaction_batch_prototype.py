"""Controlled test-fixture setup transaction batching experiment.

Only setup-time fixture writes are grouped. Each test still gets a unique fresh
database. Every test's setup commits before its test method starts. Production
Database.transaction and runtime test-method transactions remain unchanged.
"""
import argparse
import hashlib
import json
import sys
import time
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

from f139.local_controller import Database

ROOT = Path(__file__).resolve().parent
TARGETS = ("test_nci04_owner_ledger.py", "test_nci04_g32_owner_custody.py")


def database_fingerprint(db):
    schema = tuple(tuple(row) for row in db.conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE sql IS NOT NULL ORDER BY type,name"))
    tables = [row[0] for row in db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    contents = []
    for table in tables:
        escaped = '"' + table.replace('"', '""') + '"'
        rows = [tuple(row) for row in db.conn.execute(f"SELECT * FROM {escaped}")]
        contents.append((table, sorted(rows, key=repr)))
    payload = json.dumps(
        {"schema": schema, "tables": contents},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class FixtureResult(unittest.TextTestResult):
    mode = "original"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.snapshots = {}
        self.db_paths = set()
        self.initialize_calls = 0
        self.transaction_calls = 0
        self.commits = 0
        self.rollbacks = 0
        self.original_setups = {}

    def startTest(self, test):
        original_setup = test.setUp
        self.original_setups[test] = original_setup

        def timed_setup():
            original_initialize = Database.initialize
            @classmethod
            def counted_initialize(cls, filename, source_sha):
                path = str(Path(filename).resolve())
                if path in self.db_paths:
                    raise AssertionError("F139_G114L_DATABASE_PATH_REUSED")
                self.db_paths.add(path)
                self.initialize_calls += 1
                return original_initialize(filename, source_sha)

            original_transaction = Database.transaction
            if self.mode == "original":
                @contextmanager
                def counted_transaction(db, *args, **kwargs):
                    self.transaction_calls += 1
                    try:
                        with original_transaction(db, *args, **kwargs) as conn:
                            yield conn
                    except BaseException:
                        self.rollbacks += 1
                        raise
                    else:
                        self.commits += 1
                with patch.object(Database, "initialize", counted_initialize):
                    with patch.object(Database, "transaction", counted_transaction):
                        original_setup()
            else:
                active = {}
                with ExitStack() as stack:
                    @contextmanager
                    def fixture_transaction(db, *args, **kwargs):
                        self.transaction_calls += 1
                        if db not in active:
                            active[db] = stack.enter_context(
                                original_transaction(db, *args, **kwargs))
                        yield db.conn

                    with patch.object(Database, "initialize", counted_initialize):
                        with patch.object(Database, "transaction", fixture_transaction):
                            try:
                                original_setup()
                            except BaseException:
                                self.rollbacks += len(active)
                                raise
                    # ExitStack commits one original transaction per DB only
                    # after setup completed. Each test method begins afterward.
                self.commits += len(active)

            dbs = [value for value in vars(test).values()
                   if isinstance(value, Database)]
            self.snapshots[test.id()] = sorted(database_fingerprint(db) for db in dbs)

        test.setUp = timed_setup
        try:
            super().startTest(test)
        except BaseException:
            test.setUp = original_setup
            raise

    def stopTest(self, test):
        try:
            super().stopTest(test)
        finally:
            # Restore the instance method so only setUp is affected.
            original_setup = self.original_setups.pop(test, None)
            if original_setup is not None:
                test.setUp = original_setup


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("original", "batch"), required=True)
    args = parser.parse_args()
    FixtureResult.mode = args.mode
    suite = unittest.TestSuite()
    loader = unittest.defaultTestLoader
    for pattern in TARGETS:
        suite.addTests(loader.discover(start_dir=str(ROOT / "f139"), pattern=pattern))
    discovered = suite.countTestCases()
    started = time.perf_counter()
    runner = unittest.TextTestRunner(verbosity=1, resultclass=FixtureResult)
    result = runner.run(suite)
    elapsed = time.perf_counter() - started
    receipt = json.dumps(result.snapshots, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(receipt.encode("utf-8")).hexdigest()
    print(f"F139_G114L_MODE={args.mode}")
    print(f"F139_G114L_DISCOVERED={discovered}")
    print(f"F139_G114L_EXECUTED={result.testsRun}")
    print(f"F139_G114L_SKIPPED={len(result.skipped)}")
    print(f"F139_G114L_INITIALIZE_CALLS={result.initialize_calls}")
    print(f"F139_G114L_UNIQUE_WRITABLE_DATABASES={len(result.db_paths)}")
    print(f"F139_G114L_TRANSACTION_CALLS={result.transaction_calls}")
    print(f"F139_G114L_SETUP_COMMITS={result.commits}")
    print(f"F139_G114L_SETUP_ROLLBACKS={result.rollbacks}")
    print(f"F139_G114L_FINAL_STATE_RECEIPT_SHA256={digest}")
    print(f"F139_G114L_WALL_SECONDS={elapsed:.6f}")
    print(f"F139_G114L_RESULT={'PASS' if result.wasSuccessful() else 'FAIL'}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

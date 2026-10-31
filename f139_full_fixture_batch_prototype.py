"""RAR-G114M: opt-in full-F139 setup-only batching comparison.

Runs the unmodified full suite and then the same discovered suite with
transaction batching restricted to five explicitly qualified fixture classes.
The production Database.transaction method and all test methods remain intact.
The experiment fails closed on any per-test outcome or post-setup DB state drift.
"""
import hashlib
import json
import sys
import time
import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from f139.local_controller import Database

ELIGIBLE = {
    ("test_nci04_owner_ledger", "LedgerTests"),
    ("test_nci04_g32_owner_custody", "OriginalOwnerG32Tests"),
    ("test_nci04_v19_original_attempt_schema", "OriginalRequestColdVerifierTests"),
    ("test_nci04_g38_owner_terminal", "G38AtomicOwnerTests"),
    ("test_nci04_v19_original_terminal_witness", "OriginalWitnessTests"),
}


def fingerprint(db):
    schema = [tuple(row) for row in db.conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE sql IS NOT NULL ORDER BY type,name")]
    table_names = [row[0] for row in db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    tables = []
    for name in table_names:
        quoted = '"' + name.replace('"', '""') + '"'
        rows = [tuple(row) for row in db.conn.execute(f"SELECT * FROM {quoted}")]
        tables.append((name, sorted(rows, key=repr)))
    value = json.dumps({"schema": schema, "tables": tables},
                       sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ReceiptResult(unittest.TextTestResult):
    batch_mode = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.current = None
        self.batch = {"eligible_tests": 0, "transaction_calls": 0,
                      "databases": 0, "commits": 0, "rollbacks": 0}

    def startTest(self, test):
        self.current = {"test_id": test.id(), "setup_fingerprints": [], "outcome": "PASS"}
        self.records.append(self.current)
        original_setup = test.setUp

        def wrapped_setup():
            module = test.__class__.__module__.rsplit(".", 1)[-1]
            eligible = (module, test.__class__.__name__) in ELIGIBLE
            try:
                if self.batch_mode and eligible:
                    self.batch["eligible_tests"] += 1
                    original_transaction = Database.transaction
                    active = {}

                    @contextmanager
                    def fixture_transaction(db, *args, **kwargs):
                        self.batch["transaction_calls"] += 1
                        if db not in active:
                            active[db] = stack.enter_context(
                                original_transaction(db, *args, **kwargs))
                        yield db.conn

                    try:
                        with ExitStack() as stack:
                            with patch.object(Database, "transaction", fixture_transaction):
                                original_setup()
                    except BaseException:
                        self.batch["rollbacks"] += len(active)
                        raise
                    else:
                        self.batch["databases"] += len(active)
                        self.batch["commits"] += len(active)
                else:
                    original_setup()

                databases = [value for value in vars(test).values()
                             if isinstance(value, Database)]
                self.current["setup_fingerprints"] = sorted(
                    fingerprint(db) for db in databases)
            finally:
                test.setUp = original_setup

        test.setUp = wrapped_setup
        super().startTest(test)

    def addSuccess(self, test):
        self.current["outcome"] = "PASS"
        super().addSuccess(test)

    def addFailure(self, test, err):
        self.current["outcome"] = "FAIL"
        super().addFailure(test, err)

    def addError(self, test, err):
        self.current["outcome"] = "ERROR"
        super().addError(test, err)

    def addSkip(self, test, reason):
        self.current["outcome"] = "SKIP:" + str(reason)
        super().addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        self.current["outcome"] = "EXPECTED_FAILURE"
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self.current["outcome"] = "UNEXPECTED_SUCCESS"
        super().addUnexpectedSuccess(test)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.current["outcome"] = "SUBTEST_FAIL"
        super().addSubTest(test, subtest, err)


def run(mode):
    ReceiptResult.batch_mode = mode == "batch"
    suite = unittest.defaultTestLoader.discover(start_dir="f139", pattern="test_*.py")
    discovered = suite.countTestCases()
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=1, resultclass=ReceiptResult).run(suite)
    elapsed = time.perf_counter() - started
    receipt = {
        "discovered": discovered,
        "executed": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "tests": result.records,
    }
    encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return result, receipt, digest, elapsed


def main():
    original, original_receipt, original_sha, original_seconds = run("original")
    print(f"F139_G114M_ORIGINAL_DISCOVERED={original_receipt['discovered']}")
    print(f"F139_G114M_ORIGINAL_EXECUTED={original.testsRun}")
    print(f"F139_G114M_ORIGINAL_WALL_SECONDS={original_seconds:.3f}")
    print(f"F139_G114M_ORIGINAL_RECEIPT_SHA256={original_sha}")

    batched, batch_receipt, batch_sha, batch_seconds = run("batch")
    print(f"F139_G114M_BATCH_DISCOVERED={batch_receipt['discovered']}")
    print(f"F139_G114M_BATCH_EXECUTED={batched.testsRun}")
    print(f"F139_G114M_BATCH_WALL_SECONDS={batch_seconds:.3f}")
    print(f"F139_G114M_BATCH_RECEIPT_SHA256={batch_sha}")
    print(f"F139_G114M_ELIGIBLE_TESTS={batched.batch['eligible_tests']}")
    print(f"F139_G114M_BATCH_TRANSACTION_CALLS={batched.batch['transaction_calls']}")
    print(f"F139_G114M_BATCH_DATABASES={batched.batch['databases']}")
    print(f"F139_G114M_BATCH_COMMITS={batched.batch['commits']}")
    print(f"F139_G114M_BATCH_ROLLBACKS={batched.batch['rollbacks']}")

    equal = original_receipt == batch_receipt
    print(f"F139_G114M_RECEIPT_EQUAL={'PASS' if equal else 'FAIL'}")
    print(f"F139_G114M_FULL_REGRESSION={'PASS' if original.wasSuccessful() and batched.wasSuccessful() else 'FAIL'}")
    if (not original.wasSuccessful() or not batched.wasSuccessful()
            or not equal or original.testsRun != original_receipt["discovered"]
            or batched.testsRun != batch_receipt["discovered"]
            or original.batch["rollbacks"] or batched.batch["rollbacks"]
            or batched.batch["eligible_tests"] == 0):
        return 1
    if original_receipt["discovered"] != batch_receipt["discovered"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

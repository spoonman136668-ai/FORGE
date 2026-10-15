"""R38: isolated SQLite monotonicity contract; no live D1 or science."""
import concurrent.futures
import pathlib
import sqlite3
import tempfile
import unittest

HERE = pathlib.Path(__file__).parent
OLD = HERE / "r35_atomic_preuse_candidate.sql"
NEW = HERE / "r38_monotonic_preuse_candidate.sql"


def connect(path):
    db = sqlite3.connect(str(path), timeout=15, isolation_level=None)
    db.execute("PRAGMA busy_timeout=15000")
    return db


def insert(db, key, sequence, epoch=7, mode="INSERT"):
    assert mode in ("INSERT", "INSERT OR REPLACE", "INSERT OR IGNORE")
    db.execute(
        f"{mode} INTO forge_original_preuse_claims "
        "(original_key_sha256,lane,owner_epoch,source_commit_sha,"
        "frozen_predecision_sha256,external_owner_witness_pin_sha256,claimed_sequence) "
        "VALUES (?,?,?,?,?,?,?)",
        (f"{key:064x}", "Wingless", epoch, "a"*40, "b"*64, "c"*64, sequence),
    )


class TestR38MonotonicPreuse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dbpath = pathlib.Path(self.tmp.name) / "existing-db.db"
        with connect(self.dbpath) as db:
            db.execute("CREATE TABLE previous_archives (archive_id INT PRIMARY KEY, seal TEXT)")
            db.execute("INSERT INTO previous_archives VALUES (1,'untouched')")
            db.executescript(OLD.read_text())
            db.executescript(NEW.read_text())

    def test_lower_unused_sequence_rejected_and_state_immutable(self):
        with connect(self.dbpath) as db:
            insert(db, 1, 20)
            for key, seq in [(2, 19), (3, 20), (1, 21)]:
                with self.subTest(key=key, seq=seq):
                    with self.assertRaises(sqlite3.IntegrityError):
                        insert(db, key, seq)
            insert(db, 4, 21)
            self.assertEqual(db.execute("SELECT claimed_sequence FROM forge_original_preuse_claims ORDER BY rowid").fetchall(), [(20,), (21,)])
            self.assertEqual(db.execute("SELECT seal FROM previous_archives WHERE archive_id=1").fetchone(), ("untouched",))

    def test_epoch_rollback_rejected_even_with_increasing_sequence(self):
        with connect(self.dbpath) as db:
            insert(db, 1, 100, 7)
            insert(db, 2, 101, 8)
            with self.assertRaises(sqlite3.IntegrityError):
                insert(db, 3, 102, 7)
            insert(db, 4, 103, 8)
            self.assertEqual(db.execute("SELECT owner_epoch FROM forge_original_preuse_claims ORDER BY rowid").fetchall(), [(7,), (8,), (8,)])

    def test_insert_or_replace_cannot_bypass_immutability(self):
        with connect(self.dbpath) as db:
            insert(db, 1, 3)
            for key, seq in [(1, 4), (2, 3), (3, 2)]:
                with self.subTest(key=key, seq=seq):
                    with self.assertRaises(sqlite3.IntegrityError):
                        insert(db, key, seq, mode="INSERT OR REPLACE")
            self.assertEqual(db.execute("SELECT original_key_sha256,claimed_sequence FROM forge_original_preuse_claims").fetchall(), [(f"{1:064x}", 3)])

    def test_insert_or_ignore_cannot_silence_stale_preuse(self):
        with connect(self.dbpath) as db:
            insert(db, 1, 10)
            with self.assertRaises(sqlite3.IntegrityError):
                insert(db, 2, 9, mode="INSERT OR IGNORE")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM forge_original_preuse_claims").fetchone()[0], 1)

    def test_concurrent_distinct_candidates_preserve_commit_order(self):
        # Writers compete on one real SQLite file, rather than a mock ledger.
        # Whether an older attempt loses depends on which writer obtains the DB lock.
        def attempt(i):
            try:
                with connect(self.dbpath) as db:
                    insert(db, i + 1, 1000 + i)
                return True
            except sqlite3.IntegrityError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(24)))
        with connect(self.dbpath) as db:
            history = [x[0] for x in db.execute("SELECT claimed_sequence FROM forge_original_preuse_claims ORDER BY rowid")]
        self.assertGreaterEqual(sum(results), 1)
        self.assertEqual(len(history), sum(results))
        self.assertEqual(history, sorted(set(history)))
        self.assertTrue(all(1000 <= value < 1024 for value in history))

    def test_no_authority_from_monotonic_storage(self):
        with connect(self.dbpath) as db:
            insert(db, 1, 1)
            self.assertEqual(db.execute("SELECT scientific_authorized FROM forge_original_preuse_claims").fetchall(), [(0,)])
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("UPDATE forge_original_preuse_claims SET scientific_authorized=1")
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute("DELETE FROM forge_original_preuse_claims")

    def test_guard_fails_closed_without_baseline(self):
        with connect(pathlib.Path(self.tmp.name)/"missing-baseline.db") as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.executescript(NEW.read_text())


if __name__ == "__main__":
    unittest.main()

"""Focused H53 negative controls; no live owner or scheduler required."""
import hashlib
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "f139" / "h53_successor_readonly_observer.py"
spec = importlib.util.spec_from_file_location("h53_observer", SOURCE)
h53 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h53)


def make_db(path, *, bad_hash=False, gap=False, source=None):
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE meta (id INTEGER PRIMARY KEY, source_sha TEXT, enabled INTEGER, head_seq INTEGER, head_hash TEXT)")
        db.execute("CREATE TABLE events (seq INTEGER PRIMARY KEY, kind TEXT, payload TEXT, prior_sha TEXT, sha TEXT)")
        previous = "0" * 64
        for seq in range(1, 352):
            if gap and seq == 120:
                continue
            payload = {"ticket": "test-ticket"}
            kind = "TEST_EVENT"
            digest = hashlib.sha256(h53.canonical({"seq": seq, "prior_sha": previous, "kind": kind, "payload": payload})).hexdigest()
            if seq == 350:
                digest = h53.BASELINE_SHA
            if bad_hash and seq == 351:
                digest = "f" * 64
            db.execute("INSERT INTO events VALUES (?,?,?,?,?)", (seq, kind, json.dumps(payload), previous, digest))
            previous = digest
        db.execute("INSERT INTO meta VALUES (1,?,?,?,?)", (source or h53.SOURCE_SHA, 1, 351, previous))
        db.commit()


class H53NegativeControls(unittest.TestCase):
    def test_missing_database_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            h53.ledger_observation(Path(tempfile.gettempdir()) / "h53-nonexistent-test-db.sqlite")

    def test_wrong_source_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            db = Path(root) / "test.sqlite"
            make_db(db, source="0" * 40)
            with self.assertRaisesRegex(RuntimeError, "SOURCE_POLICY_DRIFT"):
                h53.ledger_observation(db)

    def test_sequence_gap_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            db = Path(root) / "test.sqlite"
            make_db(db, gap=True)
            with self.assertRaisesRegex(RuntimeError, "CHAIN_LINK_DRIFT"):
                h53.ledger_observation(db)

    def test_corrupt_event_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            db = Path(root) / "test.sqlite"
            make_db(db, bad_hash=True)
            with self.assertRaisesRegex(RuntimeError, "CHAIN_HASH_DRIFT"):
                h53.ledger_observation(db)

    def test_scheduler_disabled_rejected(self):
        with patch.object(h53.subprocess, "run") as run:
            run.return_value.stdout = json.dumps({"name": h53.TASK_NAME, "state": "Disabled"})
            with self.assertRaisesRegex(RuntimeError, "OWNER_TASK_DRIFT"):
                h53.scheduler_observation()


if __name__ == "__main__":
    unittest.main()

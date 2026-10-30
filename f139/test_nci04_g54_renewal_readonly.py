"""Exercise only G54's new original-ledger renewal readback, no real owner IO."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest


SOURCE = "db7a1d0f324478183c54df417624053448d6b08b"
WORKFLOW = (Path(__file__).resolve().parent.parent /
            ".github/workflows/f139-g54-v9-owner-cutover.yml")


def original_readonly_snippet() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    status = text.split("\n  read-only-status:\n", 1)[1]
    marker = "          $dbReport = @'\n"
    body = status.split(marker, 1)[1].split("\n          '@", 1)[0]
    return textwrap.dedent(body)


def frozen_fixture(path: Path) -> None:
    connection = sqlite3.connect(str(path))
    try:
        connection.executescript(
            "CREATE TABLE meta(id INTEGER PRIMARY KEY,schema TEXT,source_sha TEXT,enabled INTEGER,"
            "legacy_suspended INTEGER,head_seq INTEGER,head_hash TEXT);"
            "CREATE TABLE tasks(ticket TEXT,lane TEXT,stage TEXT,source_sha TEXT,"
            "run_id INTEGER,started_at TEXT,completed_at TEXT,quarantine_reason TEXT);"
            "CREATE TABLE events(seq INTEGER,kind TEXT,payload TEXT,sha TEXT);"
        )
        connection.execute("INSERT INTO meta VALUES(?,?,?,?,?,?,?)",
                           (1,"forge.f139.windows-controller.v1",
                            SOURCE,1,1,332,"c"*64))
        connection.execute("INSERT INTO tasks(stage) VALUES('VERIFIED')")
        kinds = ["FREE_REASONER_ATTEMPTED", "FREE_REASONER_ATTEMPTED",
                 "MODEL_DRAFT_ATTEMPTED", "MODEL_DRAFT_AUTHENTICATED",
                 "PROVIDER_VERIFIED_TERMINAL","NATIVE_V_THREE_PROVIDER_CUSTODY",
                 "UNRELATED_SECRET_EVENT"]
        for seq, kind in enumerate(kinds, 326):
            # Payloads may contain secrets: they must NEVER be printed by
            # this diagnostic, even in its tail.
            connection.execute("INSERT INTO events VALUES(?,?,?,?)",
                               (seq,kind,'PRIVATE_MODEL_KEY_DO_NOT_ECHO',f"{seq:064x}"))
        connection.commit()
    finally:
        connection.close()


class G54RenewalReadOnlyTests(unittest.TestCase):
    def test_renewal_inspection_is_no_mutation_and_no_sensitive_payload(self):
        body = original_readonly_snippet()
        self.assertIn("PRAGMA query_only=ON", body)
        self.assertIn("F139_G54_RENEWAL_READ_ONLY=", body)
        self.assertIn("SELECT seq,kind,sha FROM events ORDER BY seq DESC LIMIT 8", body)
        self.assertNotIn("SELECT seq,kind,payload FROM events ORDER BY seq DESC LIMIT 8", body)
        self.assertIn("len(tail)<=8", body)
        self.assertNotIn("OPENROUTER_API_KEY", body)
        self.assertNotIn("INSERT INTO", body)
        self.assertNotIn("UPDATE events", body)
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "original-test.sqlite"
            frozen_fixture(db)
            before = db.read_bytes()
            r = subprocess.run(
                [sys.executable,"-B","-",str(db),SOURCE],
                input=body,text=True,capture_output=True,timeout=10,check=False)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertNotIn("PRIVATE_MODEL_KEY_DO_NOT_ECHO",r.stdout)
            row = next(s for s in r.stdout.splitlines()
                       if s.startswith("F139_G54_RENEWAL_READ_ONLY="))
            report = json.loads(row.split("=",1)[1])
            self.assertEqual(report["head_seq"],332)
            self.assertEqual(report["head_sha256"],"c"*64)
            self.assertEqual(report["event_counts"]["FREE_REASONER_ATTEMPTED"],2)
            self.assertEqual(report["event_counts"]["PROVIDER_VERIFIED_TERMINAL"],1)
            self.assertEqual(len(report["last_eight_event_kinds"]),7)
            self.assertEqual(report["last_eight_event_kinds"][0]["kind"],
                             "UNRELATED_SECRET_EVENT")
            self.assertTrue(all(set(e)=={"seq","kind","sha"} for e in
                                report["last_eight_event_kinds"]))
            self.assertEqual(db.read_bytes(),before)

    def test_wrong_source_cannot_be_reported_as_valid_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/"original-test.sqlite"
            frozen_fixture(db)
            r=subprocess.run(
                [sys.executable,"-B","-",str(db),"f"*40],
                input=original_readonly_snippet(),text=True,
                capture_output=True,timeout=10,check=False)
            self.assertNotEqual(r.returncode,0)
            self.assertNotIn("F139_G54_RENEWAL_READ_ONLY=",r.stdout)
            self.assertNotIn("PRIVATE_MODEL_KEY_DO_NOT_ECHO",r.stdout)


if __name__ == "__main__":
    unittest.main()

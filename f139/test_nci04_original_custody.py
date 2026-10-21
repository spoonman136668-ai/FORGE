"""A4 issue-specific original custody tests, no owner controller actions."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from f139.local_controller import Database, hash_bytes, store_evidence
from f139.nci04_original_custody import (
    A4CustodyBlocked, EXPECTED, SOURCE, PREFIX_HEAD, audit, verify_one,
)
from test_local_controller import artifact


class FakeProvider:
    def __init__(self, ticket, runid, archives):
        self.ticket, self.runid, self.archives = ticket, runid, archives
        self.calls = []
        self.arts = [
            {"name": "forge-f139-dev-receipt-" + label,
             "id": 1000 + idx, "size_in_bytes": len(raw),
             "digest": "sha256:" + hash_bytes(raw)}
            for idx, (label, raw) in enumerate(archives.items())
        ]

    def protected_main(self):
        return SOURCE

    def candidates(self, ticket, started_at):
        self.calls.append(("candidates", ticket))
        return {"id": self.runid}

    def run_proof(self, run, ticket, source, started_at):
        self.calls.append(("verified", ticket))
        return self.runid, self.arts


class ReadOnlyA4Tests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(prefix="f139-nci04a4-")
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.dbpath = self.root / "state.sqlite"
        self.db = Database.initialize(self.dbpath, SOURCE)
        self.addCleanup(self.db.close)
        self.db.conn.execute("UPDATE meta SET enabled=1, legacy_suspended=1 WHERE id=1")
        expected = EXPECTED[687]
        ticket = expected["ticket"]
        self.started = "2026-10-20T23:10:50Z"
        self.fields = {
            "issue_number": "687", "issue_id": str(expected["issue_id"]),
            "body_sha256": "5a2ecddb" + "d" * 56,
            "target_package": expected["target_package"],
        }
        self.task = {
            "ticket": ticket, "lane": "Wingless", "source_sha": SOURCE,
        }
        with mock.patch("test_local_controller.SHA", SOURCE):
            self.archives = {
                label: artifact(self.task, expected["run_id"], label, issue=self.fields)
                for label in ("ubuntu-latest", "windows-latest")
            }
        folder, evidence_sha = store_evidence(
            self.root, ticket, expected["run_id"], self.archives)
        self.manifest_sha = "c" * 64
        self.db.conn.execute(
            "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
            "run_id,started_at,evidence_dir,evidence_sha) VALUES(?,?,?,'VERIFIED',?,?,?,?,?)",
            (ticket, "Wingless", SOURCE, self.manifest_sha, expected["run_id"],
             self.started, folder, evidence_sha))
        self.admission = {
            "schema": "forge.f139.d2k.issue-work.v1",
            "source_sha": SOURCE, "ticket": ticket,
            "issue_number": 687, "issue_id": expected["issue_id"],
            "lane": "Wingless", "kind": "go-package-test-diagnostic",
            "target_package": expected["target_package"],
            "body_sha256": self.fields["body_sha256"],
            "manifest_sha256": self.manifest_sha,
            "prior_event_head_sha256": "0" * 64,
            "admitted_day": "2026-10-20", "scientific_first_use": False,
        }
        with self.db.transaction():
            for name, payload in (
                ("DEVELOPMENT_WORK_ADMITTED", self.admission),
                ("TASK_INTAKE", {"ticket": ticket,
                                 "manifest_sha": self.manifest_sha}),
                ("BEFORE_DISPATCH_INTENT", {"ticket": ticket,
                                            "started_at": self.started, "starts": 1}),
                ("DISPATCH_POST_RETURNED", {"ticket": ticket}),
                ("PROVIDER_VERIFIED_TERMINAL", {"ticket": ticket,
                       "run_id": expected["run_id"], "evidence_sha": evidence_sha}),
            ):
                self.db.event(name, payload)
        self.events = [dict(x) for x in self.db.conn.execute(
            "SELECT * FROM events ORDER BY seq")]
        self.provider = FakeProvider(ticket, expected["run_id"], self.archives)
        self.spec = {
            **expected,
            "artifacts": {
                label: {"id": 1000 + idx, "size": len(raw),
                        "sha256": hash_bytes(raw)}
                for idx, (label, raw) in enumerate(self.archives.items())
            },
        }
        self.spec["artifacts"] = {
            label: {"id": 1000 + idx, "size": len(raw),
                    "sha256": hash_bytes(raw)}
            for idx, (label, raw) in enumerate(self.archives.items())
        }
        patcher = mock.patch.dict(
            "f139.nci04_original_custody.EXPECTED", {687: self.spec})
        patcher.start()
        self.addCleanup(patcher.stop)

    def verify(self):
        return verify_one(owner_root=self.root, db=self.db,
                          provider=self.provider, spec=self.spec,
                          admission=self.admission, events=self.events)

    def test_receipt_binds_both_original_local_provider_zips(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes()
                  for p in self.root.rglob("*") if p.is_file()}
        report = self.verify()
        after = {p.relative_to(self.root).as_posix(): p.read_bytes()
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(report["run_id"], EXPECTED[687]["run_id"])
        self.assertEqual(report["local_provider_original_bytes"], 2)
        self.assertFalse(report["scientific_first_use"])
        self.assertEqual(len(self.provider.calls), 2)

    def test_second_claim_fails_without_rewriting_original(self):
        with self.db.transaction():
            self.db.event("BEFORE_DISPATCH_INTENT",
                          {"ticket": self.spec["ticket"],
                           "started_at": self.started, "starts": 2})
        self.events = [dict(x) for x in self.db.conn.execute(
            "SELECT * FROM events ORDER BY seq")]
        with self.assertRaisesRegex(A4CustodyBlocked, "LIFECYCLE_OR_REPLAY"):
            self.verify()

    def test_local_zip_corruption_fails_closed(self):
        path = self.root / "evidence" / self.spec["ticket"] / str(
            self.spec["run_id"]) / "windows-latest.zip"
        path.write_bytes(path.read_bytes() + b"x")
        with self.assertRaisesRegex(A4CustodyBlocked, "SIZE_DRIFT"):
            self.verify()

    def test_provider_original_run_identity_mismatch_rejected(self):
        self.provider.runid += 1
        with self.assertRaisesRegex(A4CustodyBlocked, "PROVIDER_ORIGINAL_ATTEMPT_DRIFT"):
            self.verify()

    def test_missing_local_terminal_rejected(self):
        self.db.conn.execute(
            "UPDATE tasks SET stage='WAIT_PROVIDER' WHERE ticket=?",
            (self.spec["ticket"],))
        with self.assertRaisesRegex(A4CustodyBlocked, "ISSUE_TASK_NOT_TERMINAL"):
            self.verify()

    def test_readonly_audit_rejects_missing_sealed_prefix(self):
        with self.assertRaisesRegex(A4CustodyBlocked, "INDEPENDENT_SEALED_PREFIX_REQUIRED"):
            audit(self.dbpath, sealed_23_head="0" * 64,
                  provider=self.provider)

    def test_readonly_audit_rejects_missing_historical_custody(self):
        # Authentic D2C/D2J original custody is a hard precondition;
        # synthetic 5-event issue history may not impersonate it.
        with self.assertRaisesRegex(A4CustodyBlocked, "SEALED_PREFIX_OR_D2K_HISTORY_MISSING"):
            audit(self.dbpath, sealed_23_head=PREFIX_HEAD,
                  provider=self.provider)

    def test_wrong_source_identity_fails_before_owner_db_read(self):
        self.provider.protected_main = lambda: "9" * 40
        with self.assertRaisesRegex(A4CustodyBlocked, "PROTECTED_MAIN_DRIFT"):
            audit(self.dbpath, sealed_23_head=PREFIX_HEAD,
                  provider=self.provider)


if __name__ == "__main__":
    unittest.main()

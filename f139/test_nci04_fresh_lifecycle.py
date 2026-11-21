"""Real temporary SQLite, synthetic provider and synthetic owner key only."""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import hmac
import tempfile
from pathlib import Path
import unittest

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_fresh_native_activation import ACTIVATION_KIND, ACTIVATION_SCHEMA
from f139.nci04_fresh_native_intake import KIND, SCHEMA as INTAKE_SCHEMA
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE as OLD_SOURCE, HEAD_SEQ, HEAD_SHA256,
)
from f139.nci04_fresh_lifecycle import (
    RELEASE_KIND, RELEASE_SCHEMA, RELEASE_DOMAIN, FreshLifecycleDenied,
    reserve_claim, acknowledge_post, read_lifecycle, settle_provider,
)
from f139.nci04_fresh_worker_protocol import (
    SOURCE, TARGET, FRESH_RUN, OS, REPO, WORKFLOW, PREFIX, admission_for_run,
)
from f139.nci04_worker_v3 import receipt_v3
from f139 import test_nci04_fresh_worker_protocol as protocol_fixture
from f139 import test_nci04_original_v3_terminal as terminal_fixture


class FreshLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.fixture = protocol_fixture.FreshWorkerProtocolTests(
            "test_distinct_release_genuine_low_sequence_and_signed_receipt_identity")
        self.fixture.setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name) / "FORGE-F139" / ("f139-fresh-dev-" + str(FRESH_RUN))
        root.mkdir(parents=True)
        self.path = root / "state.sqlite"
        self.db = Database.initialize(self.path, SOURCE)
        self.addCleanup(lambda: self.db.close())
        self.db.enable(legacy_suspended=True)
        act = {
            "schema": ACTIVATION_SCHEMA, "source_sha": SOURCE,
            "prior_event_head_sha256": self.db.meta()["head_hash"],
            "owner_run_id": FRESH_RUN, "original_source_sha": OLD_SOURCE,
            "original_head_seq": HEAD_SEQ, "original_head_sha256": HEAD_SHA256,
            **{k: "1" * 64 for k in (
                "stage_manifest_sha256", "consumed_exclusions_sha256",
                "yggdrasil_research_boundary_sha256", "remote_cutover_receipt_sha256",
                "original_task_release_receipt_sha256")},
            "remote_issue_number_floor": 1830, "accepted_yggdrasil_main_sha": TARGET,
            "development_only": True, "scientific_first_use": False, "paid_model_calls": 0,
            "new_controller": False, "new_scheduler": False, "new_queue": False,
            "worker_dispatch_authorized": False, "model_continuation_authorized": False,
        }
        native = self.fixture.issue
        with self.db.transaction():
            self.db.event(ACTIVATION_KIND, act)
            intake = dict(self.fixture.fixture.intake)
            intake.update(schema=INTAKE_SCHEMA,
                          activation_sha256=self.db.meta()["head_hash"],
                          native_intent_base64=base64.b64encode(native.intent_raw).decode("ascii"))
            intake["manifest_sha256"] = digest(canonical(intake))
            self.db.event(KIND, intake)
            self.db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) VALUES(?,?,?,'READY',?)",
                (native.ticket, "Yggdrasil", SOURCE, intake["manifest_sha256"]))
            self.db.event("TASK_INTAKE", {"ticket": native.ticket, "lane": "Yggdrasil",
                                          "manifest_sha": intake["manifest_sha256"]})
            self.db.verify()
        self.prefix = [(r["seq"], r["sha"]) for r in self.db.conn.execute(
            "SELECT seq,sha FROM events ORDER BY seq")]
        self.key = self.fixture.key
        self.now = "2026-11-21T08:00:00Z"
        self.finished = "2026-11-21T08:05:00Z"
        self.rid = 123456
        self.release = {
            "schema": RELEASE_SCHEMA, "admission_source_sha": SOURCE,
            "activation_run_id": FRESH_RUN, "initial_ready_sha256": self.prefix[-1][1],
            "worker_release_sha": self.fixture.release, "worker_release_tree": self.fixture.tree,
            "owner_run_id": 900, "owner_comment_id": 901, "original_rebind_run_id": 44852932511,
            "task_name": "FORGE-F139-UnifiedController", "development_only": True,
            "scientific_first_use": False, "model_continuation_authorized": False,
            "paid_model_calls": 0,
        }
        self.release["owner_signature"] = hmac.new(
            self.key.encode(), RELEASE_DOMAIN + canonical(self.release), hashlib.sha256).hexdigest()
        self.routes = deepcopy(self.fixture.routes)
        self.artifacts = {}
        self.api_calls = []

    def get(self, route):
        self.api_calls.append(route)
        return deepcopy(self.routes[route])

    def candidates_for_source(self, ticket, started_at, source):
        self.assertEqual(ticket, self.fixture.issue.ticket)
        self.assertEqual(started_at, self.now)
        self.assertEqual(source, self.fixture.release)
        return self.get("repos/" + REPO + "/actions/runs/" + str(self.rid))

    def artifact(self, ident):
        return self.artifacts[ident]

    def install_synthetic_release(self):
        # Test-only local writer; no production release authority is granted.
        with self.db.transaction():
            self.db.event(RELEASE_KIND, self.release)
            self.db.verify()

    def reopen(self):
        self.db.close()
        self.db = Database(self.path)
        self.db.verify()

    def prepare_provider(self, claim, raw):
        source = claim["worker_release_sha"]
        root = "repos/" + REPO + "/actions/runs/" + str(self.rid)
        title = "F139 " + claim["ticket"]
        self.routes[root] = {
            "id": self.rid, "display_title": title, "name": title,
            "event": "workflow_dispatch", "workflow_id": 388797257,
            "path": ".github/workflows/" + WORKFLOW,
            "head_sha": source, "head_branch": PREFIX + source,
            "run_attempt": 1, "status": "completed", "conclusion": "success",
            "repository": {"full_name": REPO}, "created_at": self.now,
        }
        jobs = [{"id": 10, "name": "native-authorize-fresh",
                 "status": "completed", "conclusion": "success"}]
        artifacts = []
        fixture = terminal_fixture.OriginalV3CustodyTests(
            "test_positive_development_only_signed_report_and_two_exact_zip_members")
        fixture.setUp()
        for i, label in enumerate(OS):
            a = admission_for_run(claim, raw, commitment=digest(canonical(claim)),
                                  run_id=self.rid, oslabel=label)
            c = a.intent
            report = dict(fixture.report, os=label, ticket_source_commit=c.target_commit,
                          target_tree_sha=c.target_tree_sha, path=c.path,
                          candidate_sha256=c.after_sha256, intent_sha256=c.intent_sha256,
                          qualification_key=c.qualification_key)
            receipt = receipt_v3(a, report)
            blob = fixture.zipbytes(report, receipt)
            aid = 20 + i
            self.artifacts[aid] = blob
            artifacts.append({"id": aid, "name": "forge-f139-fresh-native-receipt-" + label,
                              "workflow_run": {"id": self.rid, "head_sha": source},
                              "size_in_bytes": len(blob), "digest": "sha256:" + digest(blob),
                              "expired": False})
            jobs.append({"id": 30 + i, "name": "native-execute-fresh (" + label + ")",
                         "status": "completed", "conclusion": "success"})
        self.routes[root + "/jobs?per_page=100"] = {"jobs": jobs, "total_count": len(jobs)}
        self.routes[root + "/artifacts?per_page=100"] = {
            "artifacts": artifacts, "total_count": len(artifacts)}

    def test_original_inert_prefix_stays_valid_but_cannot_claim_without_release(self):
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaises(FreshLifecycleDenied):
                reserve_claim(self.db, self, self.key, now=self.now)
        self.assertEqual(self.db.meta()["head_seq"], 4)
        self.assertFalse(self.api_calls)

    def test_requires_existing_kernel_lock_and_correct_release_signature(self):
        self.install_synthetic_release()
        with self.assertRaises(FreshLifecycleDenied):
            reserve_claim(self.db, self, self.key, now=self.now)
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaises(FreshLifecycleDenied):
                reserve_claim(self.db, self, "wrong-synthetic-key" * 3, now=self.now)
        self.assertFalse(self.api_calls)
        self.assertEqual(self.db.meta()["head_seq"], 5)

    def test_lost_ack_cold_reopen_no_second_claim_and_positive_terminal(self):
        self.install_synthetic_release()
        with SingleOwner(self.path.with_suffix(".lock")):
            claim, raw = reserve_claim(self.db, self, self.key, now=self.now)
        self.assertEqual(claim["admission_seq"], 3)
        self.assertEqual(claim["claim_seq"], 6)
        self.reopen()
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaises(FreshLifecycleDenied):
                reserve_claim(self.db, self, self.key, now=self.now)
            self.prepare_provider(claim, raw)
            custody = settle_provider(self.db, self, self.key, run_id=self.rid, now=self.finished)
        self.reopen()
        self.assertEqual(self.db.meta()["head_seq"], 8)
        self.assertEqual(self.db.conn.execute("SELECT stage FROM tasks").fetchone()[0], "VERIFIED")
        self.assertEqual(custody["run_id"], self.rid)
        self.assertEqual([(r["seq"], r["sha"]) for r in self.db.conn.execute(
            "SELECT seq,sha FROM events WHERE seq<=4 ORDER BY seq")], self.prefix)
        file = Path(custody["evidence_dir"]) / "windows-latest.zip"
        file.write_bytes(b"tampered")
        with self.assertRaises(FreshLifecycleDenied):
            self.db.verify()

    def test_ack_once_and_failed_provider_cannot_create_successor(self):
        self.install_synthetic_release()
        with SingleOwner(self.path.with_suffix(".lock")):
            claim, raw = reserve_claim(self.db, self, self.key, now=self.now)
            acknowledge_post(self.db, self.key, ticket=claim["ticket"])
            with self.assertRaises(FreshLifecycleDenied):
                acknowledge_post(self.db, self.key, ticket=claim["ticket"])
            self.prepare_provider(claim, raw)
            route = "repos/" + REPO + "/actions/runs/" + str(self.rid)
            self.routes[route]["conclusion"] = "failure"
            with self.assertRaises(ValueError):
                settle_provider(self.db, self, self.key, run_id=self.rid, now=self.finished)
            with self.assertRaises(FreshLifecycleDenied):
                reserve_claim(self.db, self, self.key, now=self.now)
        self.reopen()
        self.assertEqual(self.db.meta()["head_seq"], 7)
        self.assertEqual(self.db.conn.execute("SELECT stage FROM tasks").fetchone()[0], "WAIT_PROVIDER")


if __name__ == "__main__":
    unittest.main()

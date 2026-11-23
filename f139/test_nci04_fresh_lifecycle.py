"""Real temporary SQLite, synthetic provider and synthetic owner key only."""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import hmac
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner, F139Error, run_once
from f139.nci04_native_contract import canonical, digest
from f139.nci04_fresh_native_activation import ACTIVATION_KIND, ACTIVATION_SCHEMA
from f139.nci04_fresh_native_intake import KIND, SCHEMA as INTAKE_SCHEMA
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE as OLD_SOURCE, HEAD_SEQ, HEAD_SHA256,
)
from f139.nci04_fresh_lifecycle import (
    RELEASE_KIND, RELEASE_SCHEMA, RELEASE_DOMAIN, FreshLifecycleDenied,
    reserve_claim, acknowledge_post, read_lifecycle, settle_provider, admit_next_successor,
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
        from f139.test_nci04_fresh_native_provider_issue import FreshProviderPreflightTests
        provenance = FreshProviderPreflightTests("test_provider_candidate_preflight_is_inert_and_rechecks_all")
        provenance.setUp()
        self.consumed = deepcopy(provenance.consumed)
        self.boundary = deepcopy(provenance.boundary)
        self.floor = deepcopy(provenance.floor)
        self.floor.update(target_forge_source_sha=SOURCE, remote_cutover_issue_number_floor=1830,
                          consumed_exclusions_sha256=digest(canonical(self.consumed)))
        for filename, doc in (("consumed-development-identities.json", self.consumed),
                              ("yggdrasil-research-lineage.json", self.boundary),
                              ("remote-issue-cutover-floor.json", self.floor)):
            (root / filename).write_bytes(canonical(doc))
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
        act.update(consumed_exclusions_sha256=digest(canonical(self.consumed)),
                   yggdrasil_research_boundary_sha256=digest(canonical(self.boundary)),
                   remote_cutover_receipt_sha256=digest(canonical(self.floor)))
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

    native_repo_get = get

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
            "actor": {"login": "spoonman136668-ai"},
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
            with self.assertRaises(FreshLifecycleDenied):
                admit_next_successor(self.db, self, self.key)
        self.reopen()
        self.assertEqual(self.db.meta()["head_seq"], 7)
        self.assertEqual(self.db.conn.execute("SELECT stage FROM tasks").fetchone()[0], "WAIT_PROVIDER")


    def test_successor_admission_uses_distinct_original_issue_and_no_replay(self):
        from f139.nci04_owner_issue import LABEL
        self.install_synthetic_release()
        with SingleOwner(self.path.with_suffix(".lock")):
            claim, raw = reserve_claim(self.db, self, self.key, now=self.now)
            self.prepare_provider(claim, raw)
            settle_provider(self.db, self, self.key, run_id=self.rid, now=self.finished)
            original = deepcopy(self.fixture.raw_issue)
            # An owner-authored new issue with identical candidate bytes is
            # consumed semantically even if it has a fresh issue number.
            duplicate = dict(original, number=1850, id=91850,
                             url="https://api.github.com/repos/" + REPO + "/issues/1850")
            candidate = json.loads(raw)
            data = b"# synthetic distinct successor candidate\n"
            candidate["after_sha256"] = digest(data)
            candidate["after_base64"] = base64.b64encode(data).decode("ascii")
            body = json.loads(original["body"])
            body["intent_base64"] = base64.b64encode(canonical(candidate)).decode("ascii")
            successor = dict(original, number=1851, id=91851,
                             url="https://api.github.com/repos/" + REPO + "/issues/1851",
                             body=json.dumps(body, sort_keys=True))
            prefix = "repos/" + REPO
            self.routes[prefix + "/issues/1850"] = duplicate
            self.routes[prefix + "/issues/1851"] = successor
            self.routes[prefix + "/issues?state=open&labels=" + LABEL +
                        "&per_page=100&page=1"] = [successor, original, duplicate]
            record = admit_next_successor(self.db, self, self.key)
            self.assertEqual(record["issue_number"], 1851)
            self.assertEqual(self.db.ready()["ticket"], record["ticket"])
            with self.assertRaises(FreshLifecycleDenied):
                admit_next_successor(self.db, self, self.key)
        self.reopen()
        self.assertEqual(self.db.meta()["head_seq"], 10)
        self.assertEqual([r["stage"] for r in self.db.conn.execute(
            "SELECT stage FROM tasks ORDER BY ticket")], ["VERIFIED", "READY"])
        self.assertEqual([(r["seq"], r["sha"]) for r in self.db.conn.execute(
            "SELECT seq,sha FROM events WHERE seq<=4 ORDER BY seq")], self.prefix)



    def test_original_run_once_recovers_lost_post_without_second_submission(self):
        self.install_synthetic_release()
        posts = []

        def lost_ack(args):
            posts.append(args)
            raise F139Error("SYNTHETIC_POST_TIMEOUT")

        self.runner = lost_ack
        classify = {"disposition": "FRESH_EXECUTION_HISTORY_RECORDED_DISPATCH_BLOCKED"}
        with patch("f139.nci04_fresh_native_owner_route.inspect_staged_fresh_native_mode",
                   return_value=classify), patch(
                       "f139.nci04_fresh_lifecycle.authenticate_runtime_owner") as host:
            with SingleOwner(self.path.with_suffix(".lock")):
                out = run_once(self.db, self, self.path, self.key, now=self.now)
                self.assertEqual(out["disposition"], "FRESH_START_RISK_NO_REPLAY")
                self.assertEqual(len(posts), 1)
                from f139.nci04_fresh_lifecycle import committed_claim
                release, entries = read_lifecycle(self.db, self.key)
                claim, raw = committed_claim(entries[-1], release)
            self.reopen()
            self.prepare_provider(claim, raw)
            with SingleOwner(self.path.with_suffix(".lock")):
                out = run_once(self.db, self, self.path, self.key, now=self.finished)
                self.assertEqual(out["disposition"], "FRESH_VERIFIED_TERMINAL")
                self.assertEqual(len(posts), 1)
                self.assertTrue(out["development_qualified"])
            self.assertEqual(host.call_count, 2)
        self.reopen()
        self.assertEqual(self.db.meta()["head_seq"], 8)

    def test_original_run_once_does_not_spend_claim_if_live_owner_denied(self):
        self.install_synthetic_release()
        classify = {"disposition": "FRESH_EXECUTION_HISTORY_RECORDED_DISPATCH_BLOCKED"}
        with patch("f139.nci04_fresh_native_owner_route.inspect_staged_fresh_native_mode",
                   return_value=classify), patch(
                       "f139.nci04_fresh_lifecycle.authenticate_runtime_owner",
                       side_effect=FreshLifecycleDenied("SYNTHETIC_HOST_DENIAL")):
            with SingleOwner(self.path.with_suffix(".lock")):
                with self.assertRaises(F139Error):
                    run_once(self.db, self, self.path, self.key, now=self.now)
        self.assertEqual(self.db.meta()["head_seq"], 5)
        self.assertFalse(self.api_calls)



    def test_run_once_retains_one_negative_and_never_reposts_after_restart(self):
        self.install_synthetic_release()
        posts = []
        self.runner = lambda args: posts.append(args)
        classify = {"disposition": "FRESH_EXECUTION_HISTORY_RECORDED_DISPATCH_BLOCKED"}
        with patch("f139.nci04_fresh_native_owner_route.inspect_staged_fresh_native_mode",
                   return_value=classify), patch("f139.nci04_fresh_lifecycle.authenticate_runtime_owner"):
            with SingleOwner(self.path.with_suffix(".lock")):
                first = run_once(self.db, self, self.path, self.key, now=self.now)
                self.assertEqual(first["dispatches"], 1)
                from f139.nci04_fresh_lifecycle import committed_claim
                release, entries = read_lifecycle(self.db, self.key)
                claim, raw = committed_claim(entries[-1], release)
            self.prepare_provider(claim, raw)
            route = "repos/" + REPO + "/actions/runs/" + str(self.rid)
            self.routes[route]["conclusion"] = "failure"
            self.routes[route+"/jobs?per_page=100"]["jobs"][1]["conclusion"] = "failure"
            with SingleOwner(self.path.with_suffix(".lock")):
                result = run_once(self.db, self, self.path, self.key, now=self.finished)
                self.assertEqual(result["disposition"], "FRESH_FAILED_PROVIDER_RETAINED_NO_REPLAY")
            self.reopen()
            with SingleOwner(self.path.with_suffix(".lock")):
                again = run_once(self.db, self, self.path, self.key, now=self.finished)
                self.assertEqual(again, result)
                self.assertEqual(len(posts), 1)
            self.assertEqual(self.db.conn.execute(
                "SELECT count(*) FROM events WHERE kind='FRESH_WORKER_PROVIDER_NEGATIVE'").fetchone()[0], 1)



if __name__ == "__main__":
    unittest.main()

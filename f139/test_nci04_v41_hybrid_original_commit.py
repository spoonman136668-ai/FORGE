"""Source-only original commit authority and postcommit hold negative controls.

All provider/owner comments below are synthetic. The SQLite tests exercise
real transactions on a disposable fixture with historical replay mocked;
they do NOT certify the genuine original 1829-event owner history.
"""
from contextlib import closing
import copy
import json
from pathlib import Path
import unittest
from unittest import mock

from f139 import nci04_v41_hybrid_original_commit as gate
from f139 import nci04_v41_hybrid_successor_release as release
from f139 import nci04_v41_hybrid_source_transition as source
from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical
from f139.test_nci04_v41_hybrid_successor_release import (
    Provider, env as release_env, event as release_event,
    TARGET, BACKUP_SHA, PREFIX as REMOTE_PREFIX)
from f139.test_nci04_v41_hybrid_source_transition import (
    HybridSyntheticSqlTransactionTests)


def request():
    return {
        "schema": gate.SCHEMA,
        "target_source_sha": TARGET,
        "backup_run_id": 987654,
        "backup_manifest_sha256": BACKUP_SHA,
        "paired_approval_id": 112,
        "readiness_comment_id": 113,
        "original_head_seq": source.ACTIVATED_SEQ,
        "original_head_sha256": source.ACTIVATED_HASH,
        "expected_proof_sha256": "c" * 64,
        "source_transition_requested": True,
        "task_resume_authorized": False,
        "policy_update_authorized": False,
        "hybrid_admission": False,
        "scientific_first_use": False,
        "new_dispatches": 0,
    }


def event():
    old = release_event()
    return {**old,
            "comment": {
                "id": 114, "body": gate.PREFIX +
                    canonical(request()).decode("ascii"),
                "created_at": "2026-11-14T16:00:00Z",
                "user": {"login": release.OWNER},
                "author_association": "OWNER",
            }}


class OriginalCommitAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.remote = Provider()
        value = event()["comment"]
        self.remote.entries[REMOTE_PREFIX + "issues/comments/114"] = {
            **value,
            "issue_url": "https://api.github.com/repos/" +
                         release.REPO + "/issues/807",
            "updated_at": value["created_at"],
        }

    def inspect(self, *, environment=None, issued=None):
        return gate.authenticate_commit_request(
            release_env() if environment is None else environment,
            event() if issued is None else issued, self.remote)

    def test_distinct_readiness_and_commit_events_required(self):
        doc = self.inspect()
        self.assertEqual(doc["readiness_comment_id"], 113)
        self.assertEqual(doc["source_commit_comment_id"], 114)
        self.assertEqual(doc["backup_run_id"], 987654)
        self.assertTrue(doc["source_transition_requested"])
        for key in ("hybrid_admission", "scientific_first_use",
                    "task_resume_authorized", "policy_update_authorized"):
            self.assertFalse(doc[key])
        self.assertEqual(
            self.remote.calls.count(REMOTE_PREFIX + "issues/comments/114"), 2)

    def test_readiness_comment_alone_not_commit_authority(self):
        with self.assertRaisesRegex(gate.OriginalCommitDenied,
                                    "EXPLICIT_SEPARATE_SOURCE_COMMIT_EVENT"):
            self.inspect(issued=release_event())

    def test_wrong_sha_runner_attempt_actor_and_paid_api_denied(self):
        for field, bad in (
            ("GITHUB_SHA", "f"*40),
            ("GITHUB_ACTOR", "other"),
            ("RUNNER_NAME", "github-hosted"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("OPENAI_API_KEY", "paid"),
        ):
            with self.subTest(field=field), self.assertRaises(
                    gate.OriginalCommitDenied):
                self.inspect(environment={**release_env(), field: bad})

    def test_forbidden_science_policy_or_implicit_approval_denied(self):
        for key, bad in (
            ("scientific_first_use", True),
            ("hybrid_admission", True),
            ("task_resume_authorized", True),
            ("policy_update_authorized", True),
            ("new_dispatches", 1),
            ("source_transition_requested", False),
            ("readiness_comment_id", 112),
        ):
            with self.subTest(key=key):
                doc = {**request(), key: bad}
                changed = event()
                changed["comment"]["body"] = (
                    gate.PREFIX + canonical(doc).decode("ascii"))
                with self.assertRaises(gate.OriginalCommitDenied):
                    self.inspect(issued=changed)

    def test_uncanonical_json_or_different_readiness_is_denied(self):
        changed = event()
        changed["comment"]["body"] += " "
        with self.assertRaises(gate.OriginalCommitDenied):
            self.inspect(issued=changed)
        changed = event()
        changed["comment"]["body"] = (
            gate.PREFIX + canonical({
                **request(), "backup_manifest_sha256": "0"*64
            }).decode("ascii"))
        self.remote.entries[
            REMOTE_PREFIX+"issues/comments/114"]["body"] = changed["comment"]["body"]
        with self.assertRaises(gate.HybridSuccessorDenied):
            self.inspect(issued=changed)

    def test_comment_order_edited_or_foreign_owner_denied(self):
        key = REMOTE_PREFIX + "issues/comments/114"
        for property, bad in (
            ("created_at", "2026-11-14T11:00:00Z"),
            ("updated_at", "2026-11-14T17:00:00Z"),
            ("author_association", "CONTRIBUTOR"),
        ):
            original = copy.deepcopy(self.remote.entries[key])
            self.remote.entries[key][property] = bad
            try:
                with self.subTest(property=property), self.assertRaises(
                        (gate.HybridSuccessorDenied, gate.OriginalCommitDenied)):
                    self.inspect()
            finally:
                self.remote.entries[key] = original

    def test_writer_not_called_on_non_windows_host(self):
        with self.assertRaisesRegex(
                gate.OriginalCommitDenied,
                "WINDOWS_ORIGINAL_HOST_AND_NATIVE_PROVIDER_REQUIRED"):
            gate.original_commit(Path("/tmp/unsafe.sqlite"), release_env(),
                                 event(), object())

    def test_unregistered_windows_wrapper_does_not_mutate_task(self):
        body = Path(gate.__file__).read_text(encoding="utf-8")
        wrapper = Path(gate.__file__).with_name(
            "v41_hybrid_original_source_commit.ps1").read_text("utf-8")
        for bad in (
            "Disable-ScheduledTask", "Enable-ScheduledTask",
            "Start-ScheduledTask", "Stop-ScheduledTask",
            "Set-ScheduledTask", "UPDATE meta SET",
            "gh api --method PATCH", "workflow_dispatch(",
        ):
            self.assertNotIn(bad, wrapper)
        self.assertIn("commit_transition(", body)
        self.assertIn("verify_postcommit_readonly(", body)
        self.assertIn("SOURCE-COMMIT ", body)


class OriginalPostcommitSqliteFixtureTests(unittest.TestCase):
    def setUp(self):
        self.fixture = HybridSyntheticSqlTransactionTests(
            "test_atomic_source_commit_keeps_history_and_new_dispatches_zero")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_held_committed_event_and_negatives_readback(self):
        self.fixture.simulated_external_qualification()
        f = self.fixture
        with SingleOwner(f.file.with_suffix(".lock")):
            proof = source.build_proof(f.db, f.target, 31, 800001, "5"*64)
            commit = source.commit_transition(
                f.db, proof,
                disabled_owner_witness=lambda: True,
                verified_release_witness=lambda: True)
            with closing(Database.open_readonly(f.file)) as db:
                held = gate.verify_postcommit_readonly(db, proof, commit)
                self.assertEqual(held["event_seq"], source.ACTIVATED_SEQ+1)
                self.assertEqual(held["verified_historical_tasks"], 153)
                self.assertEqual(held["custodied_negative_tasks"], 56)
                self.assertFalse(held["task_resume_authorized"])
                self.assertFalse(held["hybrid_admission"])
                self.assertEqual(db.conn.total_changes, 0)

    def test_tampered_receipt_fails_readonly_witness(self):
        f = self.fixture
        f.simulated_external_qualification()
        with SingleOwner(f.file.with_suffix(".lock")):
            proof = source.build_proof(f.db, f.target, 31, 800001, "5"*64)
            commit = source.commit_transition(
                f.db, proof,
                disabled_owner_witness=lambda: True,
                verified_release_witness=lambda: True)
            with closing(Database.open_readonly(f.file)) as db:
                for key, bad in (
                    ("event_head_sha256", "f"*64),
                    ("task_resume_authorized", True),
                    ("event_seq", source.ACTIVATED_SEQ + 2),
                    ("hybrid_admission", True),
                ):
                    with self.subTest(key=key), self.assertRaises(
                            gate.OriginalCommitDenied):
                        gate.verify_postcommit_readonly(
                            db, proof, {**commit, key: bad})


if __name__ == "__main__":
    unittest.main()

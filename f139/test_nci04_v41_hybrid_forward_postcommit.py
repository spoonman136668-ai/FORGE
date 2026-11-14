"""Synthetic fail-closed owner readback after the exact V38 source event.

These tests never write to live SQLite, register owner jobs or authorize a
second source transition. All provider/ledger test doubles are explicit.
"""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from f139.local_controller import Database
from f139 import nci04_v41_hybrid_forward_postcommit as post
from f139 import nci04_v41_hybrid_forward_repair as v38
from f139.test_nci04_v41_hybrid_forward_original_commit import CommitProvider


class PostcommitAuthTests(unittest.TestCase):
    def setUp(self):
        self.provider = CommitProvider()
        self.comment_id = 6893333333
        body = (post.PREFIX + self.provider.target + " " +
                str(self.provider.commit_id))
        self.provider.comments[self.comment_id] = (
            self.provider.comment(
                self.comment_id, body, "2026-11-14T23:00:00Z"))

    def event(self):
        event = self.provider.event()
        event["comment"] = self.provider.comments[self.comment_id]
        return event

    def test_separate_postcommit_owner_approval_authenticates_source(self):
        request = post.authenticate(
            self.provider.get, self.provider.env(), self.event())
        self.assertEqual(request["target_source_sha"], self.provider.target)
        self.assertEqual(request["source_commit_comment_id"],
                         self.provider.commit_id)
        self.assertEqual(request["backup_run_id"], self.provider.run_id)

    def test_replayed_or_wrong_prior_source_is_rejected(self):
        self.provider.comments[self.comment_id]["body"] = (
            post.PREFIX + self.provider.target + " " +
            str(self.provider.ready_id))
        with self.assertRaisesRegex(
                post.PostcommitDenied, "ORIGINAL_SOURCE_COMMIT_INTENT_UNAVAILABLE"):
            post.authenticate(
                self.provider.get, self.provider.env(), self.event())
        self.provider.comments[self.comment_id]["body"] = (
            post.PREFIX + self.provider.target + " " +
            str(self.comment_id))
        with self.assertRaisesRegex(
                post.PostcommitDenied, "NEW_POSTCOMMIT_AFTER_SOURCE_COMMIT_REQUIRED"):
            post.authenticate(
                self.provider.get, self.provider.env(), self.event())

    def test_wrong_runner_or_wrong_comment_identity_denied(self):
        env = self.provider.env()
        env["GITHUB_RUN_ATTEMPT"] = "2"
        with self.assertRaisesRegex(
                post.PostcommitDenied, "ORIGINAL_OWNER_FIRST_ATTEMPT_REQUIRED"):
            post.authenticate(self.provider.get, env, self.event())
        self.provider.comments[self.comment_id]["body"] = (
            post.PREFIX + "0" * 40 + " " + str(self.provider.commit_id))
        with self.assertRaisesRegex(
                post.PostcommitDenied, "EXACT_POSTCOMMIT_COMMENT_REQUIRED"):
            post.authenticate(
                self.provider.get, self.provider.env(), self.event())

    def test_no_live_activation_route_or_original_task_mutations(self):
        with self.assertRaisesRegex(
                post.PostcommitDenied, "ORIGINAL_WINDOWS_OWNER_REQUIRED"):
            post.original_postcommit(None, {}, {}, None)
        source = Path(post.__file__).read_text("utf-8")
        for forbidden in ("Start-ScheduledTask", "Enable-ScheduledTask",
                          "Set-ScheduledTask", "Disable-ScheduledTask",
                          "workflow_dispatch", "gh workflow run",
                          "gh api --method PATCH"):
            self.assertNotIn(forbidden, source)
        workflow = (Path(__file__).resolve().parent.parent / ".github" /
                    "workflows" /
                    "f139-v41-original-owner-live-install.yml").read_text(
                        "utf-8")
        self.assertNotIn("forward-postcommit", workflow)


class PostcommitLedgerTests(unittest.TestCase):
    def setUp(self):
        self.path = Path("synthetic-not-live-owner-state.sqlite")
        self.target = "b" * 40
        self.request = {
            "target_source_sha": self.target,
            "readiness_comment_id": 6889999999,
            "backup_run_id": 43649999999,
            "backup_manifest_sha256": "a" * 64,
            "backup_logical_all_tables_sha256": "c" * 64,
        }
        self.meta = {
            "source_sha": self.target,
            "head_seq": v38.V37_SEQ + 1,
            "head_hash": "e" * 64,
            "enabled": 1, "legacy_suspended": 1
        }
        self.proof = {
            "schema": v38.SCHEMA,
            "owner_event_id": self.request["readiness_comment_id"],
            "backup_run_id": self.request["backup_run_id"],
            "backup_manifest_sha256":
                self.request["backup_manifest_sha256"],
            "backup_logical_all_tables_sha256":
                self.request["backup_logical_all_tables_sha256"],
        }
        self.proof.update({k: False for k in (
            "task_resume_authorized", "owner_policy_update_authorized",
            "hybrid_admission", "scientific_first_use")})
        self.proof.update({
            k: "placeholder" for k in v38.FIELDS if k not in self.proof
        })
        self.row = {
            "seq": v38.V37_SEQ + 1,
            "kind": "SOURCE_TRANSITION_ADMITTED",
            "sha": self.meta["head_hash"],
            "prior_sha": v38.V37_HEAD,
            "payload": json.dumps(self.proof, sort_keys=True,
                                  separators=(",", ":")),
        }
        self.db = object.__new__(Database)
        self.db.filename = self.path
        self.db._readonly_opened = True

    def _run(self, *, meta=None, row=None, cold=None):
        ledger = self
        class Result:
            def fetchone(self):
                return row if row is not None else ledger.row
        class Connection:
            total_changes = 0
            def execute(self, sql, params=()):
                if "PRAGMA query_only" in sql:
                    return SimpleNamespace(fetchone=lambda: (1,))
                if "FROM events" in sql:
                    return Result()
                raise AssertionError("unexpected original ledger SQL " + sql)
        self.db.conn = Connection()
        actual_meta = dict(self.meta if meta is None else meta)
        with patch.object(Database, "meta", return_value=actual_meta), (
             patch.object(Database, "verify", return_value=None)), (
             patch.object(Database, "dual_native_schema",
                          return_value=True)), (
             patch.object(Database, "ready", return_value=None)), (
             patch.object(Database, "actives", return_value=[])), (
             patch.object(post.SingleOwner, "held",
                          return_value=True)), (
             patch.object(post, "is_migrated", return_value=False)), (
             patch.object(post.committed, "_fresh_bundle", return_value={
                 "original_head_seq": v38.V37_SEQ,
                 "original_head_sha256": v38.V37_HEAD,
             } if cold is None else cold)), (
             patch.object(post.committed, "_postcommit", return_value={
                 "event_seq": v38.V37_SEQ + 1,
                 "source_sha": self.target,
                 "verified_historical_tasks": 153,
                 "custodied_negative_tasks": 56,
                 "hybrid_admission": False,
                 "task_resume_authorized": False,
                 "scientific_first_use": False,
             })):
            # This test double never makes any real SQLite call.
            return post.inspect(self.db, self.request)

    def test_readonly_postcommit_accepts_only_exact_1831_event(self):
        result = self._run()
        self.assertEqual(result["event_seq"], v38.V37_SEQ + 1)
        self.assertEqual(result["predecessor_event_head_sha256"], v38.V37_HEAD)
        self.assertEqual(result["verified_historical_tasks"], 153)
        self.assertEqual(result["custodied_negative_tasks"], 56)
        self.assertFalse(result["native_activation_performed"])
        self.assertFalse(result["hybrid_schema_migrated"])
        self.assertFalse(result["task_resume_authorized"])

    def test_rejects_wrong_source_event_or_backup_receipt(self):
        for field, bad in (
            ("head_seq", v38.V37_SEQ),
            ("source_sha", v38.FROM),
            ("enabled", 0),
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                        post.PostcommitDenied,
                        "EXACT_INACTIVE_POSTCOMMIT_HOLD_REQUIRED"):
                    self._run(meta={**self.meta, field: bad})
        with self.assertRaisesRegex(
                post.PostcommitDenied,
                "EXACT_V38_SOURCE_EVENT_REQUIRED"):
            self._run(row={**self.row, "prior_sha": "0" * 64})
        bad_proof = {**self.proof, "backup_run_id": 44}
        with self.assertRaisesRegex(
                post.PostcommitDenied,
                "SOURCE_EVENT_NOT_BOUND_TO_APPROVED_BACKUP"):
            self._run(row={**self.row, "payload": json.dumps(
                bad_proof, sort_keys=True, separators=(",", ":"))})
        with self.assertRaisesRegex(
                post.PostcommitDenied,
                "PRECOMMIT_COLD_PREIMAGE_CHANGED"):
            self._run(cold={
                "original_head_seq": v38.V37_SEQ-1,
                "original_head_sha256": v38.V37_HEAD})


if __name__ == "__main__":
    unittest.main()

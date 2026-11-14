"""Paired original-owner maintenance negatives; no original task control."""
from contextlib import closing
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database
from f139 import nci04_v41_hybrid_cold_pair as pair
from f139 import nci04_v41_hybrid_pair_owner as gate
from f139 import nci04_v41_hybrid_owner_maintenance as original

TARGET = "491c6c0089d5a6a7f494243a5a0e86fc131a5a2e"


class PairedOwnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root/"FORGE-F139"/"state.sqlite"
        self.db.parent.mkdir()
        with closing(Database.initialize(self.db, pair.V41_SOURCE)) as d:
            d.enable(legacy_suspended=True)
            d.enable_native_two_slots()
        self.env = {
            "LOCALAPPDATA": str(self.root),
            "GITHUB_REPOSITORY": gate.REPO,
            "GITHUB_ACTOR": gate.OWNER,
            "GITHUB_EVENT_NAME": "issue_comment",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": TARGET,
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "99113",
            "RUNNER_NAME": "FORGE-CODEX-REMOTE",
        }
        self.before = {
            "id": 88,
            "body": original.PREFIX + TARGET,
            "created_at": "2026-11-14T08:11:00Z",
            "author_association": "OWNER", "user": {"login": gate.OWNER},
        }
        self.approval = {
            "id": 89, "body": gate.PREFIX + TARGET + " 88",
            "created_at": "2026-11-14T08:12:00Z",
            "author_association": "OWNER", "user": {"login": gate.OWNER},
        }
        self.event = {
            "action": "created",
            "issue": {"number":807,"user":{"login":gate.OWNER}},
            "sender": {"login":gate.OWNER},
            "comment": dict(self.approval),
        }
        self.calls = []
        self.policy = {
            "schema": "forge.f139.native-autonomy-feed-owner-policy.v1",
            "enabled": True, "source_sha": pair.V41_SOURCE,
            "title_prefix": "F139 autonomy DEV:",
            "lanes": ["Wingless", "Yggdrasil"],
            "max_issue_creations_per_cycle": 2,
            "require_owner_authored_pr": True,
            "require_single_head_commit_delta": True,
            "require_single_allowed_source_file": True,
            "scientific_first_use": False, "paid_model_calls": 0,
            "accepted_ref_mutations": 0,
            "new_controller": False, "new_scheduler": False,
            "new_queue": False,
        }

    def get(self, route):
        self.calls.append(route)
        prefix = "repos/"+gate.REPO+"/"
        if route == prefix+"issues/comments/88":
            value = self.before
        elif route == prefix+"issues/comments/89":
            value = self.approval
        elif route == prefix+"issues/807":
            return {"state":"open","user":{"login":gate.OWNER},
                    "body":json.dumps(self.policy)}
        elif route == prefix+"branches/main":
            return {"name":"main","protected":True,
                    "commit":{"sha":pair.V41_SOURCE}}
        elif route == prefix+"pulls/1660":
            return {"number":1660,"state":"open","merged":False,
                    "head":{"sha":TARGET},
                    "base":{"ref":"main","sha":pair.V41_SOURCE}}
        else:
            raise AssertionError("unexpected GET route")
        return {**value, "issue_url":"https://api.github.com/repos/" +
                gate.REPO + "/issues/807"}

    def auth(self, *, env=None, event=None, provider=None):
        return gate.authenticate_pair(
            self.env if env is None else env,
            self.event if event is None else event,
            self.get if provider is None else provider,
            target_sha=TARGET)

    def test_two_distinct_owner_comments_and_order(self):
        result = self.auth()
        self.assertEqual(result["run_id"], 99113)
        self.assertEqual(result["backup_comment_id"], 88)
        self.assertEqual(result["approval_comment_id"], 89)
        self.assertEqual(self.calls.count(
            "repos/"+gate.REPO+"/issues/comments/88"),2)
        self.assertEqual(self.calls.count(
            "repos/"+gate.REPO+"/issues/comments/89"),2)

    def test_single_backup_comment_not_pause_authority(self):
        e = {**self.event, "comment": self.before}
        with self.assertRaisesRegex(gate.PairOwnerDenied, "PAIRED_APPROVAL"):
            self.auth(event=e)

    def test_wrong_identity_attempt_first_use_or_old_main_denied(self):
        for key,bad in (
                ("GITHUB_ACTOR","other"),
                ("GITHUB_SHA","0"*40),
                ("GITHUB_RUN_ATTEMPT","2"),
                ("RUNNER_NAME","hosted"),
                ("GITHUB_EVENT_NAME","workflow_dispatch"),
                ("OPENAI_API_KEY","nonempty")):
            with self.subTest(key=key), self.assertRaisesRegex(
                    gate.PairOwnerDenied,"EVENT_RUNNER"):
                self.auth(env={**self.env,key:bad})

    def test_old_approval_new_request_or_wrong_issue_denied(self):
        for field,bad in (
                ("created_at","2026-11-14T08:10:00Z"),
                ("body",gate.PREFIX+TARGET+" INVALID"),
                ("author_association","CONTRIBUTOR")):
            with self.subTest(field=field):
                e={**self.event,"comment":{**self.approval,field:bad}}
                with self.assertRaises(gate.PairOwnerDenied):
                    self.auth(event=e)
        e={**self.event,"issue":{**self.event["issue"],"number":2222}}
        with self.assertRaisesRegex(gate.PairOwnerDenied,"OWNER_EVENT"):
            self.auth(event=e)

    def test_remote_backup_or_approval_mutation_denied(self):
        def changed(route):
            value=self.get(route)
            if route.endswith("/issues/comments/88"):
                return {**value,"body":"tampered"}
            return value
        with self.assertRaisesRegex(gate.PairOwnerDenied,"COMMENT_CUSTODY"):
            self.auth(provider=changed)

    def test_synthetic_readonly_preflight_not_original_acceptance(self):
        with patch.object(gate.bridge,"require_protected_main_release",
                          return_value={"source_sha":TARGET}), \
             patch.object(original,"_task_readback",return_value=True), \
             patch.object(original,"_candidate_clean_checkout",
                          return_value=True), \
             patch.object(pair,"MIN_V41_HEAD",0), \
             patch.object(pair,"verify_native_activation",return_value=True):
            result=gate.preflight_only(self.db,self.env,self.event,self.get,
                                       target_sha=TARGET)
        self.assertFalse(result["pause_performed"])
        self.assertFalse(result["source_transition_authorized"])
        self.assertFalse(result["task_resumed"])
        with closing(Database.open_readonly(self.db)) as db:
            self.assertEqual(db.meta()["source_sha"],pair.V41_SOURCE)

    def test_authentic_1829_floor_blocks_synthetic_backup(self):
        with patch.object(gate.bridge,"require_protected_main_release",
                          return_value={"source_sha":TARGET}), \
             patch.object(original,"_task_readback",return_value=True), \
             patch.object(original,"_candidate_clean_checkout",
                          return_value=True), \
             patch.object(pair,"verify_native_activation",return_value=True):
            with self.assertRaisesRegex(gate.PairOwnerDenied,
                                        "LEDGER_UNQUALIFIED"):
                gate.preflight_only(self.db,self.env,self.event,self.get,
                                    target_sha=TARGET)
        self.assertFalse(list(self.db.parent.glob("f139-hybrid-before-*")))

    def test_wrong_policy_or_provider_head_denied(self):
        self.policy["lanes"].append("TTT-Hybrid")
        with patch.object(gate.bridge,"require_protected_main_release",
                          return_value={"source_sha":TARGET}), \
             patch.object(original,"_task_readback",return_value=True), \
             patch.object(original,"_candidate_clean_checkout",return_value=True):
            with self.assertRaises(original.HybridOwnerBackupDenied):
                gate.preflight_only(self.db,self.env,self.event,self.get,
                                    target_sha=TARGET)

    def test_disabled_owner_is_required_before_backup(self):
        with patch.object(gate.bridge,"require_protected_main_release",
                          return_value={"source_sha":TARGET}), \
             patch.object(original,"_candidate_clean_checkout",return_value=True), \
             patch.object(original,"_task_readback",
                          side_effect=original.HybridOwnerBackupDenied(
                              "F139_HYBRID_V41_OWNER_BACKUP_ORIGINAL_TASK_NOT_DISABLED")):
            with self.assertRaisesRegex(original.HybridOwnerBackupDenied,
                                        "NOT_DISABLED"):
                gate.backup_only(self.db,self.env,self.event,self.get,
                                 target_sha=TARGET)
        self.assertFalse(list(self.db.parent.glob("f139-hybrid-before-*")))

    def test_open_pr_can_never_start_original_task_or_backup(self):
        with self.assertRaisesRegex(
                gate.bridge.ProtectedHybridSourceDenied,
                "PROTECTED_MAIN"):
            gate.preflight_only(self.db,self.env,self.event,self.get,
                                target_sha=TARGET)
        self.assertFalse(list(self.db.parent.glob("f139-hybrid-before-*")))

    def test_no_mutation_or_controller_surface(self):
        import inspect
        source=inspect.getsource(gate)
        for forbidden in ("Disable-ScheduledTask","Start-ScheduledTask",
                          "Stop-ScheduledTask","workflow_dispatch(",
                          "owner_policy_patch(","UPDATE meta SET",
                          "create_ref(","db.event("):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()

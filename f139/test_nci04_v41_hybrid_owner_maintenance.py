"""Fail-closed first-attempt original-owner V41 Hybrid backup admission."""
from contextlib import closing
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database
from f139 import nci04_v41_hybrid_cold_pair as pair
from f139 import nci04_v41_hybrid_owner_maintenance as route

TARGET = "d6b9bbf25c53e8ee4df509222c96c72e9e75c143"


class HybridOwnerMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / "FORGE-F139"
        self.folder.mkdir()
        self.db = self.folder / "state.sqlite"
        with closing(Database.initialize(self.db, pair.V41_SOURCE)) as original:
            original.enable(legacy_suspended=True)
            original.enable_native_two_slots()
        self.env = {
            "LOCALAPPDATA": str(self.root),
            "GITHUB_REPOSITORY": route.REPO,
            "GITHUB_ACTOR": route.OWNER,
            "GITHUB_EVENT_NAME": "issue_comment",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": TARGET,
            "GITHUB_RUN_ID": "70203",
            "GITHUB_RUN_ATTEMPT": "1",
            "RUNNER_NAME": "FORGE-CODEX-REMOTE",
        }
        self.comment = {
            "id": 501, "body": route.PREFIX + TARGET,
            "author_association": "OWNER",
            "created_at": "2026-11-14T08:00:00Z",
            "user": {"login": route.OWNER},
        }
        self.event = {
            "action": "created",
            "issue": {"number": 807, "user": {"login": route.OWNER}},
            "sender": {"login": route.OWNER},
            "comment": dict(self.comment),
        }
        self.policy = {
            "schema":"forge.f139.native-autonomy-feed-owner-policy.v1",
            "enabled":True, "source_sha":pair.V41_SOURCE,
            "title_prefix":"F139 autonomy DEV:",
            "lanes":["Wingless","Yggdrasil"],
            "max_issue_creations_per_cycle":2,
            "require_owner_authored_pr":True,
            "require_single_head_commit_delta":True,
            "require_single_allowed_source_file":True,
            "scientific_first_use":False, "paid_model_calls":0,
            "accepted_ref_mutations":0, "new_controller":False,
            "new_scheduler":False, "new_queue":False,
        }
        self.queries = []

    def get(self, url):
        self.queries.append(url)
        if url == "repos/" + route.REPO + "/issues/comments/501":
            return dict(self.comment,
                        issue_url="https://api.github.com/repos/" +
                                  route.REPO + "/issues/807")
        if url == "repos/" + route.REPO + "/issues/807":
            return {"state":"open", "user":{"login":route.OWNER},
                    "body":json.dumps(self.policy)}
        if url == "repos/" + route.REPO + "/branches/main":
            return {"name":"main","protected":True,
                    "commit":{"sha":pair.V41_SOURCE}}
        if url == "repos/" + route.REPO + "/pulls/1660":
            return {"number":1660,"state":"open","merged":False,
                    "head":{"sha":TARGET},
                    "base":{"ref":"main","sha":pair.V41_SOURCE}}
        raise AssertionError("Unexpected native route: "+url)

    def preflight(self, *, env=None, event=None, provider=None):
        with patch.object(route, "_task_readback", return_value=True), \
             patch.object(route, "_candidate_clean_checkout", return_value=True), \
             patch.object(pair, "MIN_V41_HEAD", 0), \
             patch.object(pair, "verify_native_activation",
                          return_value=True):
            return route.preflight_only(self.db, self.env if env is None else env,
                                        self.event if event is None else event,
                                        self.get if provider is None else provider,
                                        target_sha=TARGET)

    def test_first_attempt_custodied_readonly_preflight(self):
        result = self.preflight()
        self.assertEqual(result["run_id"],70203)
        self.assertEqual(result["original_source_sha"],pair.V41_SOURCE)
        self.assertFalse(result["task_pause_authorized_by_this_receipt"])
        self.assertFalse(result["source_transition_authorized"])
        self.assertFalse(result["scientific_first_use"])
        self.assertEqual(self.queries.count(
            "repos/" + route.REPO + "/issues/comments/501"),4)
        with closing(Database.open_readonly(self.db)) as original:
            self.assertEqual(original.meta()["source_sha"],pair.V41_SOURCE)

    def test_wrong_actor_runner_attempt_and_source_denied(self):
        for key,bad in (("GITHUB_ACTOR","other"),
                        ("GITHUB_RUN_ATTEMPT","2"),
                        ("RUNNER_NAME","actions-hosted"),
                        ("GITHUB_SHA","0"*40),
                        ("GITHUB_EVENT_NAME","workflow_dispatch"),
                        ("GITHUB_RUN_ID","0")):
            with self.subTest(key=key):
                altered={**self.env,key:bad}
                with self.assertRaisesRegex(route.HybridOwnerBackupDenied,
                                            "RUNNER_OR_EVENT"):
                    self.preflight(env=altered)

    def test_absent_owner_comment_or_wrong_scope_denied(self):
        cases=[
            {**self.event,"action":"edited"},
            {**self.event,"sender":{"login":"other"}},
            {**self.event,"comment":{**self.comment,
                "body":"F139-V41-PAUSE-BACKUP-RESUME "+TARGET}},
            {**self.event,"comment":{**self.comment,
                "author_association":"CONTRIBUTOR"}},
            {**self.event,"issue":{**self.event["issue"],
                "pull_request":{"url":"untrusted"}}},
        ]
        for value in cases:
            with self.subTest(value=value),self.assertRaisesRegex(
                    route.HybridOwnerBackupDenied,"EXACT_OWNER"):
                self.preflight(event=value)

    def test_remote_comment_tamper_denied_before_task(self):
        def tampered(url):
            result=self.get(url)
            if url.endswith("/issues/comments/501"):
                return {**result,"body":"edited"}
            return result
        with self.assertRaisesRegex(route.HybridOwnerBackupDenied,
                                    "COMMENT_READBACK"):
            self.preflight(provider=tampered)

    def test_policy_drifts_and_hybrid_early_activation_denied(self):
        for patch_values in (
            {"lanes":["Wingless","Yggdrasil","TTT-Hybrid"]},
            {"source_sha":TARGET},
            {"new_scheduler":True},
            {"paid_model_calls":1},
            {"scientific_first_use":True},
            {"accepted_ref_mutations":1},
        ):
            with self.subTest(change=patch_values):
                old=self.policy
                self.policy={**self.policy,**patch_values}
                try:
                    with self.assertRaisesRegex(route.HybridOwnerBackupDenied,
                                                "POLICY_DRIFT"):
                        self.preflight()
                finally:
                    self.policy=old

    def test_candidate_checkout_wrong_source_or_dirty_is_denied(self):
        def bad_git(args, **kwargs):
            if "rev-parse" in args:
                return subprocess.CompletedProcess(args,0,b"f"*40+b"\n",b"")
            return subprocess.CompletedProcess(args,0,b"",b"")
        with self.assertRaisesRegex(route.HybridOwnerBackupDenied,
                                    "WRONG_HEAD"):
            route._candidate_clean_checkout(TARGET,runner=bad_git)
        def dirty_git(args, **kwargs):
            if "rev-parse" in args:
                return subprocess.CompletedProcess(args,0,TARGET.encode()+b"\n",b"")
            return subprocess.CompletedProcess(args,0,b" M dirty.py\n",b"")
        with self.assertRaisesRegex(route.HybridOwnerBackupDenied,
                                    "DIRTY_OR_WRONG_HEAD"):
            route._candidate_clean_checkout(TARGET,runner=dirty_git)

    def test_source_pr_move_denied(self):
        def wrong(url):
            if url.endswith("/pulls/1660"):
                return {"number":1660,"state":"open","merged":False,
                        "head":{"sha":"f"*40},
                        "base":{"ref":"main","sha":pair.V41_SOURCE}}
            return self.get(url)
        with self.assertRaisesRegex(pair.HybridColdPairDenied,
                                    "SOURCE_DRIFT"):
            self.preflight(provider=wrong)

    def test_v41_event_floor_is_genuine_only(self):
        with patch.object(route,"_task_readback",return_value=True), \
             patch.object(route,"_candidate_clean_checkout",return_value=True), \
             patch.object(pair,"verify_native_activation",return_value=True):
            with self.assertRaisesRegex(route.HybridOwnerBackupDenied,
                                        "LEDGER_UNQUALIFIED"):
                route.preflight_only(self.db,self.env,self.event,self.get,
                                     target_sha=TARGET)

    def test_backup_without_original_paused_task_fails_before_stage(self):
        with patch.object(route, "_candidate_clean_checkout", return_value=True), \
             patch.object(route, "_task_readback",
                          side_effect=route.HybridOwnerBackupDenied(
                              "F139_HYBRID_V41_OWNER_BACKUP_TASK_NOT_DISABLED")):
            with self.assertRaisesRegex(route.HybridOwnerBackupDenied,
                                        "NOT_DISABLED"):
                route.backup_only(self.db,self.env,self.event,self.get,
                                  target_sha=TARGET)
        self.assertFalse((self.folder/"f139-hybrid-before-70203").exists())

    def test_original_path_cannot_be_external_or_symlink(self):
        outside=self.root/"other.sqlite"
        outside.write_bytes(self.db.read_bytes())
        with patch.object(route,"_task_readback",return_value=True):
            with self.assertRaisesRegex(route.HybridOwnerBackupDenied,
                                        "ORIGINAL_DATABASE_PATH"):
                route.preflight_only(outside,self.env,self.event,self.get,
                                     target_sha=TARGET)

    def test_no_live_task_or_controller_authority_surface(self):
        import inspect
        body=inspect.getsource(route)
        for forbidden in ("Disable-ScheduledTask","Stop-ScheduledTask",
                          "Start-ScheduledTask","workflow_dispatch(",
                          "create_ref(", "db.event(", "UPDATE meta SET",
                          "owner_policy_patch("):
            self.assertNotIn(forbidden,body)

    def test_original_task_check_is_windows_only(self):
        if route.os.name != "nt":
            with self.assertRaisesRegex(route.HybridOwnerBackupDenied,
                                        "WINDOWS_HOST"):
                route._task_readback(self.db,disabled=False)


if __name__=="__main__":
    unittest.main()

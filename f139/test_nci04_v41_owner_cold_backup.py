"""V41 cold backup authorization negatives: no original host mutation."""
from pathlib import Path
import unittest

from f139 import nci04_v41_owner_cold_backup as gate

SHA = "2ee1d2e3894558a92231e5922980f8c96e731b36"
ENV = dict(GITHUB_REPOSITORY=gate.REPO, GITHUB_ACTOR=gate.OWNER,
           GITHUB_EVENT_NAME="issue_comment", GITHUB_REF="refs/heads/main",
           RUNNER_NAME="FORGE-CODEX-REMOTE", GITHUB_RUN_ATTEMPT="1",
           GITHUB_SHA=SHA, GITHUB_RUN_ID="12345")


def event():
    return {
        "action": "created", "sender": {"login": gate.OWNER},
        "issue": {"number": 807, "user": {"login": gate.OWNER}},
        "comment": {"id": 77, "body": gate.PREFIX + SHA,
                    "user": {"login": gate.OWNER},
                    "author_association": "OWNER",
                    "created_at": "2026-11-12T21:00:00Z"},
    }


def get(route):
    assert route == "repos/" + gate.REPO + "/issues/comments/77"
    return {**event()["comment"],
            "issue_url": "https://api.github.com/repos/" +
                         gate.REPO + "/issues/807"}


class OwnerBackupGateTests(unittest.TestCase):
    def attempt(self, env=None, ev=None, reader=get):
        return gate.verify_owner_event(ENV if env is None else env,
                                       event() if ev is None else ev,
                                       reader, target=SHA)

    def test_owner_comment_double_read_exact(self):
        calls = []
        def read(route):
            calls.append(route)
            return get(route)
        self.assertEqual(self.attempt(reader=read), 12345)
        self.assertEqual(len(calls), 2)

    def test_wrong_actor_runner_source_and_replay_denied(self):
        for key, value in (
            ("GITHUB_ACTOR", "other"), ("GITHUB_REPOSITORY", "other/repo"),
            ("GITHUB_REF", "refs/heads/test"), ("GITHUB_SHA", "a" * 40),
            ("RUNNER_NAME", "unknown"), ("GITHUB_EVENT_NAME", "push"),
            ("GITHUB_RUN_ATTEMPT", "2"), ("GITHUB_RUN_ID", "0")):
            with self.subTest(key=key), self.assertRaises(gate.OwnerBackupDenied):
                self.attempt(env={**ENV, key: value})

    def test_bad_owner_comment_and_807_custody_denied(self):
        for name in ("wrong_prefix", "wrong_owner", "wrong_issue",
                     "is_pr", "wrong_sender", "wrong_assoc", "replayed"):
            request = event()
            if name == "wrong_prefix":
                request["comment"]["body"] = "F139-V41-CUTOVER " + SHA
            elif name == "wrong_owner":
                request["comment"]["user"]["login"] = "other"
            elif name == "wrong_issue":
                request["issue"]["number"] = 1715
            elif name == "is_pr":
                request["issue"]["pull_request"] = {}
            elif name == "wrong_sender":
                request["sender"]["login"] = "other"
            elif name == "wrong_assoc":
                request["comment"]["author_association"] = "CONTRIBUTOR"
            else:
                request["action"] = "edited"
            with self.subTest(name=name), self.assertRaises(gate.OwnerBackupDenied):
                self.attempt(ev=request)

    def test_second_github_readback_drift_denied(self):
        calls = []
        def drift(route):
            calls.append(route)
            result = get(route)
            if len(calls) == 2:
                result["body"] = "tampered"
            return result
        with self.assertRaisesRegex(gate.OwnerBackupDenied,
                                    "OWNER_COMMENT_READBACK_DRIFT"):
            self.attempt(reader=drift)


    def test_unmerged_or_incomplete_postmerge_ci_denied(self):
        def remote(route):
            if route.endswith("/pulls/1736"):
                return {"number": 1736, "merged": True, "merge_commit_sha": SHA,
                        "user": {"login": gate.OWNER},
                        "base": {"ref": "main"}, "head": {"sha": "a" * 40}}
            if "/actions/runs?" in route:
                return {"workflow_runs": [
                    {"name": name, "head_sha": SHA, "event": "push",
                     "head_branch": "main", "status": "completed",
                     "conclusion": "success", "run_attempt": 1,
                     "actor": {"login": gate.OWNER}}
                    for name in (
                        "FORGE public Linux and Windows qualification",
                        "FORGE F73 protected-main cryptographic origin (no science permission)")
                ]}
            raise AssertionError("unexpected read")
        self.assertTrue(gate.verify_qualified_main(remote, SHA))

        def wrong(route):
            obj = remote(route)
            if "/pulls/" in route:
                obj["merged"] = False
            return obj
        with self.assertRaisesRegex(gate.OwnerBackupDenied,
                                    "EXACT_PROTECTED_MERGED_PR_REQUIRED"):
            gate.verify_qualified_main(wrong, SHA)

        def failed(route):
            obj = remote(route)
            if "/actions/runs?" in route:
                obj["workflow_runs"][0]["conclusion"] = "failure"
            return obj
        with self.assertRaisesRegex(gate.OwnerBackupDenied,
                                    "QUALIFIED_POSTMERGE_RUN_REQUIRED"):
            gate.verify_qualified_main(failed, SHA)

        def duplicate(route):
            obj = remote(route)
            if "/actions/runs?" in route:
                obj["workflow_runs"].append(dict(obj["workflow_runs"][0]))
            return obj
        with self.assertRaisesRegex(gate.OwnerBackupDenied,
                                    "QUALIFIED_POSTMERGE_RUN_REQUIRED"):
            gate.verify_qualified_main(duplicate, SHA)

    def test_windows_concrete_path_subtype_not_rejected_before_authority(self):
        import json
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import inspect
        from pathlib import Path

        self.assertIn("isinstance(path, Path)", inspect.getsource(gate.preflight_only))
        self.assertIn("isinstance(path, Path)", inspect.getsource(gate.backup_only))
        self.assertNotIn("type(path) is Path", inspect.getsource(gate.preflight_only))
        self.assertNotIn("type(path) is Path", inspect.getsource(gate.backup_only))
        with TemporaryDirectory() as temp:
            file = Path(temp) / "FORGE-F139" / "state.sqlite"
            file.parent.mkdir()
            file.write_bytes(b"synthetic preflight only; never opened")
            routes = []
            def get_route(route):
                routes.append(route)
                if route.endswith("/issues/comments/77"):
                    return get(route)
                if route.endswith("/pulls/1736"):
                    return {
                        "number": 1736, "merged": True,
                        "merge_commit_sha": SHA,
                        "user": {"login": gate.OWNER},
                        "base": {"ref": "main"},
                        "head": {"sha": "a" * 40},
                    }
                if "/actions/runs?" in route:
                    return {"workflow_runs": [
                        {"name": name, "head_sha": SHA, "event": "push",
                         "head_branch": "main", "status": "completed",
                         "conclusion": "success", "run_attempt": 1,
                         "actor": {"login": gate.OWNER}}
                        for name in (
                            "FORGE public Linux and Windows qualification",
                            "FORGE F73 protected-main cryptographic origin (no science permission)")
                    ]}
                if route.endswith("/issues/807"):
                    return {"body": json.dumps({
                        "schema": "forge.f139.native-autonomy-feed-owner-policy.v1",
                        "enabled": True, "source_sha": gate.preflight.OWNER_SOURCE,
                        "lanes": ["Wingless", "Yggdrasil"], "scientific_first_use": False,
                        "paid_model_calls": 0, "new_controller": False,
                        "new_scheduler": False, "new_queue": False,
                    })}
                raise AssertionError("noncanonical read")
            api = object.__new__(gate.GitHub)
            with patch.object(gate.GitHub, "native_repo_get",
                              lambda self, path: get_route(path)):
                with patch.object(gate.GitHub, "protected_main", return_value=SHA):
                    result = gate.preflight_only(
                        file, {**ENV, "LOCALAPPDATA": temp}, event(), api, target=SHA)
            self.assertTrue(result["same_task_pause_resume_only"])
            self.assertFalse(result["source_transition_authorized"])
            self.assertFalse(result["scientific_first_use"])
            self.assertEqual(routes.count("repos/" + gate.REPO + "/issues/comments/77"), 2)
            self.assertEqual(file.read_bytes(), b"synthetic preflight only; never opened")

    def test_exact_existing_job_and_bounded_same_task_maintenance(self):
        import os
        import subprocess
        root = Path(__file__).resolve().parents[1]
        wf = (root / ".github/workflows/f139-g54-v9-owner-cutover.yml").read_text()
        path = root / "f139/v41_owner_pause_backup_resume.ps1"
        source = path.read_text()
        marker = "\n  v41-owner-cold-backup-only:\n"
        self.assertEqual(wf.count(marker), 1)
        job = wf.split(marker, 1)[1]
        self.assertIn("F139-V41-PAUSE-BACKUP-RESUME ", job)
        self.assertIn("forge-codex-isolated", job)
        self.assertIn("f139/v41_owner_pause_backup_resume.ps1", job)
        self.assertIn("persist-credentials: false", job)
        self.assertIn("forge-f139-g54-v9-owner-cutover", wf)
        for required in (
            "F139OriginalOwnerMutex", "Disable-ScheduledTask",
            "Stop-ScheduledTask", "Enable-ScheduledTask", "Start-ScheduledTask",
            "--preflight-only", "F139_V41_EXISTING_V40_OWNER_RESUMED=PASS",
            "F139_V41_OWNER_RECOVERY_HOLD_OR_UNVERIFIED_MANUAL_ATTENTION",
            "Unchanged", "Installed", "Policy", "F139_V41_BACKUP_ONLY",
            "WaitForExit(600000)", "Kill($true)", "backupChildCleared",
        ):
            self.assertIn(required, source)
        for forbidden in (
            "Register-ScheduledTask", "New-ScheduledTask", "Unregister-ScheduledTask",
            "New-ScheduledJob", "Invoke-Expression", "Set-ScheduledTask",
            "git checkout", "git fetch", "workflow_dispatch",
        ):
            self.assertNotIn(forbidden, source)
        if os.name == "nt":
            literal = str(path).replace("'", "''")
            command = ("$t=$null;$e=$null;[void][Management.Automation.Language.Parser]"
                       "::ParseFile('" + literal + "',[ref]$t,[ref]$e);"
                       "if($e.Count -ne 0){$e | ForEach-Object {Write-Error $_.Message};exit 1}")
            parsed = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive",
                                     "-Command", command], text=True,
                                    capture_output=True, timeout=20)
            self.assertEqual(parsed.returncode, 0, parsed.stderr)

    def test_preflight_remains_read_only_no_original_ledger_writer(self):
        import inspect
        source = inspect.getsource(gate.preflight_only)
        self.assertIn("verify_owner_event", source)
        self.assertIn("verify_qualified_main", source)
        for forbidden in ("Database.open_readonly", "db.event(", "UPDATE meta SET",
                          "Disable-ScheduledTask", "create_native_feed_issue"):
            self.assertNotIn(forbidden, source)

    def test_no_owner_writer_in_backup_module(self):
        text = (Path(__file__).with_name("nci04_v41_owner_cold_backup.py")
                .read_text(encoding="utf-8"))
        for forbidden in ("db.event(", "UPDATE meta SET",
                          "Disable-ScheduledTask", "create_ref(",
                          "create_native_feed_issue"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()

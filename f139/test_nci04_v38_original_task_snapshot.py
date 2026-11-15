"""Cross-platform original-owner task snapshot negative/protocol controls."""
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
from types import SimpleNamespace
import unittest

from f139 import nci04_v38_original_task_snapshot as snap
from scripts import check_rar_g145_pr_scope as g145

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/f139-v38-original-task-snapshot-once.yml"


class ReadOnlySnapshotTests(unittest.TestCase):
    def test_bounded_output_masks_and_no_overlap(self):
        for value in (b"F0000-U0000\r\n", b"F0001-U0002\n",
                      b"F07FF-U0000\n", b"F0000-U07FF\n",
                      b"TASK_LOOKUP_FAILED\n"):
            with self.subTest(value=value):
                self.assertEqual(snap.parse_receipt(value, 0),
                                 value.decode("ascii").strip())
        for value in (b"F0800-U0000", b"F0000-U0800",
                      b"F0001-U0001", b"F0000-U0000\nraw-host-command",
                      b"FAAAA-U0000", b"F0000-U0000\x00",
                      b"F0000-U0000\xff", b"",
                      b"scheduled task principal details"):
            self.assertEqual(snap.parse_receipt(value, 0),
                             "POWERSHELL_OUTPUT_INVALID")
        self.assertEqual(snap.parse_receipt(b"F0000-U0000", 1),
                         "POWERSHELL_EXIT_FAILED")
        self.assertEqual(snap.parse_receipt(b"F0000-U0000", -1),
                         "POWERSHELL_EXIT_FAILED")
        self.assertEqual(snap.parse_receipt(b"a" * 101, 0),
                         "POWERSHELL_OUTPUT_INVALID")
        self.assertEqual(snap.parse_receipt(b"POWERSHELL_PROTOCOL_FAILED", 0),
                         "POWERSHELL_PROTOCOL_FAILED")

    def test_subprocess_failure_classes_and_no_raw_host_leak(self):
        def fake(stdout=b"F0000-U0000\n", code=0):
            def runner(args, **kw):
                self.assertIn("-NonInteractive", args)
                self.assertEqual(kw["timeout"], 30)
                self.assertEqual(kw["stdin"], subprocess.DEVNULL)
                self.assertFalse(kw["check"])
                return SimpleNamespace(returncode=code, stdout=stdout,
                                       stderr=b"private host details")
            return runner
        self.assertEqual(snap.powershell_once("powershell.exe", {}, runner=fake()),
                         "F0000-U0000")
        self.assertEqual(snap.powershell_once("powershell.exe", {},
                              runner=fake(b"secret command", 0)),
                         "POWERSHELL_OUTPUT_INVALID")
        self.assertEqual(snap.powershell_once("powershell.exe", {},
                              runner=fake(b"private traceback", 5)),
                         "POWERSHELL_EXIT_FAILED")
        def timed_out(*args, **kwargs):
            raise subprocess.TimeoutExpired("private command", 30, output=b"secret")
        def denied(*args, **kwargs):
            raise OSError("private host path")
        def malformed(*args, **kwargs):
            raise RuntimeError("private diagnostic information")
        self.assertEqual(snap.powershell_once("powershell.exe", {}, runner=timed_out),
                         "POWERSHELL_TIMEOUT")
        self.assertEqual(snap.powershell_once("powershell.exe", {}, runner=denied),
                         "POWERSHELL_SPAWN_FAILED")
        self.assertEqual(snap.powershell_once("powershell.exe", {}, runner=malformed),
                         "POWERSHELL_INTERNAL_ERROR")

    @unittest.skipUnless(sys.platform == "win32", "Windows PowerShell 5.1 only")
    def test_windows_powershell_native_parse_and_synthetic_task(self):
        """Parse and execute actual source with test-only task stubs, never real task."""
        powershell = shutil.which("powershell.exe")
        self.assertIsNotNone(powershell, "WINDOWS_POWERSHELL_UNAVAILABLE")
        env = dict(os.environ)
        env["FORGE_V38_SCRIPT_FOR_PARSE"] = snap.SCRIPT
        parser = (
            "$tokens=$null; $errors=$null; "
            "[void][System.Management.Automation.Language.Parser]::ParseInput("
            "$env:FORGE_V38_SCRIPT_FOR_PARSE,[ref]$tokens,[ref]$errors); "
            "if($errors.Count -gt 0){"
            "Write-Output ('PARSE_ERROR_LINE='+$errors[0].Extent.StartLineNumber); exit 41}; "
            "Write-Output 'PARSE_OK'"
        )
        parsed = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", parser],
            capture_output=True, env=env, timeout=20, text=True, check=False)
        self.assertEqual(parsed.returncode, 0,
                         "V38_PS_PARSE_FAILED " + parsed.stdout.strip()[:60])
        self.assertEqual(parsed.stdout.strip(), "PARSE_OK")

        # The function names mask actual OS cmdlets inside a fresh PowerShell
        # process. Synthetic action count 0 must produce bounded mask output.
        fake_host = r"""
function Get-ScheduledTask {
  [CmdletBinding()]
  param([string]$TaskName)
  [pscustomobject]@{
    Principal=[pscustomobject]@{ UserId='SYNTHETIC-OWNER' }
    Actions=@()
    Triggers=@()
    State='Disabled'
    Settings=[pscustomobject]@{ Enabled=$false }
  }
}
function Get-CimInstance {
  [CmdletBinding()]
  param([Parameter(Position=0)][string]$ClassName, [string]$Filter)
  @()
}
"""
        simulated = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command",
             fake_host + snap.SCRIPT],
            capture_output=True, env=env, timeout=20, text=True, check=False)
        self.assertEqual(simulated.returncode, 0, "V38_PS_SYNTHETIC_EXIT_FAILED")
        receipt = simulated.stdout.encode("ascii", errors="replace")
        self.assertRegex(snap.parse_receipt(receipt, simulated.returncode),
                         r"^F[0-9A-F]{4}-U[0-9A-F]{4}$")

    def test_all_original_task_predicates_bounded_and_readonly(self):
        src = snap.SCRIPT
        self.assertIn("Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController'", src)
        self.assertIn("Get-CimInstance Win32_Process", src)
        self.assertIn("Translate([Security.Principal.SecurityIdentifier])", src)
        self.assertIn("git -C $root rev-parse HEAD", src)
        self.assertIn("git -C $root status --porcelain --untracked-files=all", src)
        self.assertIn("if($procs.Count -ne 0) {Bad 10}", src)
        self.assertIn("task", snap.__doc__.lower())
        for bit in range(11):
            self.assertTrue(("Bad " + str(bit)) in src or
                            ("Unk " + str(bit)) in src)
        for forbidden in ("Set-ScheduledTask", "Start-ScheduledTask",
                          "Stop-ScheduledTask", "Enable-ScheduledTask",
                          "Disable-ScheduledTask", "Register-ScheduledTask",
                          "New-ScheduledTask", "Start-Process", "Invoke-Expression",
                          "gh api --method POST", "CREATE TABLE", "UPDATE tasks"):
            self.assertNotIn(forbidden, src)
        self.assertNotIn("$pid=", src.lower())
        self.assertEqual(snap.MAX_MASK, 2047)
        self.assertIn("not isinstance(db_path, Path)",
                      Path(snap.__file__).read_text("utf-8"))
        self.assertIsInstance(Path("state.sqlite"), Path)

    def test_fresh_v5_owner_comment_after_v39_actions_read(self):
        target = "a" * 40
        new_id = snap.PREV_COMMENT + 1
        body = snap.PREFIX + target + " " + str(snap.PREV_COMMENT)
        event = {"action": "created",
                 "issue": {"number": 807,
                           "user": {"login": snap.OWNER}},
                 "sender": {"login": snap.OWNER},
                 "comment": {"id": new_id, "body": body,
                             "author_association": "OWNER",
                             "user": {"login": snap.OWNER}}}
        env = {
            "GITHUB_SHA": target,
            "GITHUB_REPOSITORY": snap.REPO,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_ACTOR": snap.OWNER,
            "GITHUB_EVENT_NAME": "issue_comment",
            "GITHUB_RUN_ATTEMPT": "1",
            "RUNNER_NAME": "FORGE-CODEX-REMOTE",
            "GITHUB_RUN_ID": "43663000001",
        }
        def get(route):
            prefix = "repos/" + snap.REPO + "/"
            if route == prefix + "issues/comments/" + str(new_id):
                return {"id": new_id, "body": body,
                        "author_association": "OWNER",
                        "user": {"login": snap.OWNER},
                        "issue_url": "https://api.github.com/repos/" +
                                     snap.REPO + "/issues/807",
                        "created_at": "2026-11-15T10:15:00Z"}
            if route == prefix + "issues/comments/" + str(snap.PREV_COMMENT):
                return {"id": snap.PREV_COMMENT, "body": snap.PREV_BODY,
                        "author_association": "OWNER",
                        "user": {"login": snap.OWNER},
                        "created_at": "2026-11-15T09:59:49Z"}
            if route == prefix + "actions/runs/" + str(snap.PREV_RUN):
                return {"id": snap.PREV_RUN, "head_sha": snap.PREV_SHA,
                        "run_attempt": 1, "event": "issue_comment",
                        "status": "completed", "conclusion": "success",
                        "actor": {"login": snap.OWNER}}
            if route == prefix + "actions/runs/" + str(snap.PREV_RUN) + "/jobs?per_page=100":
                return {"total_count": 1, "jobs": [
                    {"name": "original-owner-actions-provider-readonly",
                     "status": "completed", "conclusion": "success"}]}
            if route == prefix + "branches/main":
                return {"name": "main", "protected": True,
                        "commit": {"sha": target}}
            if route == prefix + "issues/807":
                return {"state": "open", "body": json.dumps({
                    "lanes": ["Wingless", "Yggdrasil"],
                    "scientific_first_use": False, "new_controller": False,
                    "new_scheduler": False, "new_queue": False,
                    "paid_model_calls": 0})}
            raise AssertionError("unrecognized task probe owner GET")
        self.assertEqual(snap.authenticate(get, env, event), target)
        for mod in ({"GITHUB_RUN_ATTEMPT": "2"},
                    {"RUNNER_NAME": "OTHER"},
                    {"GITHUB_ACTOR": "OTHER"},
                    {"OPENAI_API_KEY": "x"},
                    {"GITHUB_SHA": snap.PREV_SHA}):
            with self.assertRaises(snap.SnapshotDenied):
                snap.authenticate(get, {**env, **mod}, event)
        with self.assertRaises(snap.SnapshotDenied):
            snap.authenticate(get, env, {
                **event, "comment": {**event["comment"], "id":
                                     snap.PREV_COMMENT}})

    def test_workflow_scope_frozen_owner_only_and_no_scheduler(self):
        text = WORKFLOW.read_text("utf-8")
        self.assertIn("on:\n  issue_comment:\n    types: [created]", text)
        self.assertIn("group: forge-f139-v38-original-task-snapshot-v5", text)
        self.assertNotIn("group: forge-f139-v41-original-owner-live-install", text)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]", text)
        self.assertIn("GITHUB_RUN_ATTEMPT -cne '1'", text)
        self.assertIn("F139-V38-ORIGINAL-TASK-SNAPSHOT-V5 ", text)
        self.assertIn("6892675791", text)
        self.assertIn("f139.nci04_v38_original_task_snapshot", text)
        self.assertIn("9bda78341bc3651e8b7b0a24ea6c7858dbff05c6", text)
        for forbidden in ("\n  schedule:", "\n  push:",
                          "\n  workflow_dispatch:", "\n  workflow_call:",
                          "Set-ScheduledTask", "Start-ScheduledTask",
                          "Stop-ScheduledTask", "Register-ScheduledTask",
                          "gh workflow run", "actions: write",
                          "issues: write", "contents: write"):
            self.assertNotIn(forbidden, text)
        self.assertFalse(g145.generic_paths_safe([
            ".github/workflows/f139-v38-original-task-snapshot-once.yml"]))
        self.assertEqual(g145.V38_SNAPSHOT_BRANCH,
                         "engineering/f139-v38-original-task-snapshot-once-20261114")
        self.assertEqual(len(g145.V38_SNAPSHOT_FILES), 7)
        g145.v38_snapshot_negative_controls()
        self.assertEqual(g145.V38_SNAPSHOT_V2_BRANCH,
                         "engineering/f139-v38-snapshot-concurrency-isolation-20261114")
        self.assertEqual(len(g145.V38_SNAPSHOT_V2_FILES), 7)
        g145.v38_snapshot_v2_negative_controls()
        self.assertEqual(g145.V38_SNAPSHOT_V3_BRANCH,
                         "engineering/f139-v38-protocol-cause-categories-20261115")
        self.assertEqual(len(g145.V38_SNAPSHOT_V3_FILES), 7)
        g145.v38_snapshot_v3_negative_controls()
        self.assertEqual(g145.V38_SNAPSHOT_V4_BRANCH,
                         "engineering/f139-v38-native-parsefix-owner-snapshot-v4-20261115")
        self.assertEqual(len(g145.V38_SNAPSHOT_V4_FILES), 7)
        g145.v38_snapshot_v4_negative_controls()
        self.assertEqual(g145.V38_SNAPSHOT_V5_BRANCH,
                         "engineering/f139-v38-original-task-snapshot-v5-after-get-proof-20261115")
        self.assertEqual(len(g145.V38_SNAPSHOT_V5_FILES), 7)
        g145.v38_snapshot_v5_negative_controls()


if __name__ == "__main__":
    unittest.main()

"""Distinct V41 PAUSE-HOLD authority; synthetic provider / no original task.

The release handoff is NOT registered with an issue-comment workflow.  No
test below pauses a real task, stages an original bundle, or grants source
commit/scientific admission.
"""
import os
from pathlib import Path
import shutil
import subprocess
import unittest

from f139 import nci04_v41_hybrid_pair_owner as pair
from f139 import nci04_v41_hybrid_successor_release as successor
from f139 import test_nci04_v41_hybrid_pair_owner as original_fixtures
from f139 import test_nci04_v41_hybrid_successor_release as release_fixtures


ROOT = Path(__file__).resolve().parents[1]
HOLD_PS = ROOT / "f139" / "v41_hybrid_original_pause_hold_backup.ps1"
RESUME_PS = ROOT / "f139" / "v41_hybrid_owner_pause_backup_resume.ps1"


class DistinctOwnerHoldIntentTests(unittest.TestCase):
    def setUp(self):
        p = original_fixtures.PairedOwnerTests(
            "test_two_distinct_owner_comments_and_order")
        p.setUp()
        self.addCleanup(p.doCleanups)
        self.p = p
        self.p.before["updated_at"] = self.p.before["created_at"]
        self.p.approval["updated_at"] = self.p.approval["created_at"]
        self.p.approval["body"] = (
            pair.HOLD_PREFIX + original_fixtures.TARGET + " 88")
        self.p.event["comment"] = dict(self.p.approval)

    def authenticate(self, *, hold=True, event=None):
        return pair.authenticate_pair(
            self.p.env, self.p.event if event is None else event,
            self.p.get, target_sha=original_fixtures.TARGET, hold=hold)

    def test_hold_is_distinct_from_successful_resume_approval(self):
        held = self.authenticate(hold=True)
        self.assertEqual(held["backup_comment_id"], 88)
        self.assertEqual(held["approval_comment_id"], 89)
        self.assertTrue(held["source_hold_requested"])
        self.assertEqual(held["run_id"], 99113)
        with self.assertRaisesRegex(
                pair.PairOwnerDenied, "INDEPENDENT_PAIRED_APPROVAL"):
            self.authenticate(hold=False)
        self.p.approval["body"] = (
            pair.PREFIX + original_fixtures.TARGET + " 88")
        self.p.event["comment"] = dict(self.p.approval)
        with self.assertRaisesRegex(
                pair.PairOwnerDenied, "INDEPENDENT_PAIRED_APPROVAL"):
            self.authenticate(hold=True)
        self.assertNotIn("source_hold_requested",
                         self.authenticate(hold=False))

    def test_edited_hold_request_or_approval_fails_closed(self):
        for comment in (self.p.before, self.p.approval):
            with self.subTest(id=comment["id"]):
                created = comment["updated_at"]
                comment["updated_at"] = "2026-11-14T08:20:00Z"
                try:
                    with self.assertRaisesRegex(
                            pair.PairOwnerDenied,
                            "HOLD_REQUIRES_UNEDITED_BOTH_OWNER_COMMENTS"):
                        self.authenticate()
                finally:
                    comment["updated_at"] = created

    def test_single_backup_comment_not_held_owner_authority(self):
        with self.assertRaises(pair.PairOwnerDenied):
            self.authenticate(event={**self.p.event,
                                     "comment": dict(self.p.before)})

    def test_hold_preflight_keeps_authentic_original_floor(self):
        # The original actual 1829 event chain is NOT present here.
        from unittest.mock import patch
        with patch.object(pair.bridge, "require_protected_main_release",
                          return_value={"source_sha": original_fixtures.TARGET}), \
             patch.object(pair.pair, "_authenticate_candidate",
                          return_value=original_fixtures.TARGET), \
             patch.object(pair.pair, "verify_native_activation",
                          return_value=True), \
             patch.object(original_fixtures.original, "_task_readback",
                          return_value=True), \
             patch.object(original_fixtures.original,
                          "_candidate_clean_checkout", return_value=True):
            with self.assertRaises(pair.PairOwnerDenied):
                pair.preflight_only(
                    self.p.db, self.p.env, self.p.event, self.p.get,
                    target_sha=original_fixtures.TARGET, hold=True)
        self.assertFalse(list(self.p.db.parent.glob("f139-hybrid-before-*")))


class HoldReleaseChainTests(unittest.TestCase):
    def test_readiness_requires_hold_approval_not_resume_approval(self):
        self.assertEqual(successor.PAIR, pair.HOLD_PREFIX)
        remote = release_fixtures.Provider()
        expected = remote.entries[
            release_fixtures.PREFIX+"issues/comments/112"]
        self.assertEqual(expected["body"].split(" ")[0],
                         "F139-HYBRID-V41-PAUSE-HOLD")
        result = successor.authenticate_owner_intent(
            remote, release_fixtures.env(), release_fixtures.event(),
            target=release_fixtures.TARGET, run_id=987654,
            manifest_sha=release_fixtures.BACKUP_SHA, approval_id=112)
        self.assertFalse(result["source_transition_authorized"])
        self.assertEqual(result["paired_approval_id"], 112)
        expected["body"] = (pair.PREFIX + release_fixtures.TARGET + " 111")
        with self.assertRaisesRegex(
                successor.HybridSuccessorDenied, "PAIRED_APPROVAL_TARGET_DRIFT"):
            successor.authenticate_owner_intent(
                remote, release_fixtures.env(), release_fixtures.event(),
                target=release_fixtures.TARGET, run_id=987654,
                manifest_sha=release_fixtures.BACKUP_SHA, approval_id=112)

    def test_unregistered_hold_wrapper_keeps_resume_wrapper_unchanged(self):
        script = HOLD_PS.read_text("utf-8")
        prior = RESUME_PS.read_text("utf-8")
        self.assertIn("F139-HYBRID-V41-PAUSE-HOLD ", script)
        self.assertNotIn("F139-HYBRID-V41-PAUSE-HOLD ", prior)
        self.assertIn("F139-HYBRID-V41-PAUSE-RESUME ", prior)
        self.assertIn("'--hold'", script)
        self.assertIn("source-hold-preflight.v1", script)
        self.assertIn("source-hold-backup-only.v1", script)
        self.assertIn("F139_HYBRID_V41_SAME_ORIGINAL_TASK_DISABLED=PASS",
                      script)
        self.assertIn("F139_HYBRID_V41_SAME_ORIGINAL_OWNER_RESUMED=PASS",
                      prior)
        # Intentionally held in success path; verified old-owner resume only
        # after a safe-to-resume failure. Never a new controller/scheduler.
        success = script.split(
            "# The separately approved HOLD prevents an intervening owner tick.",
            1)[1].split("\n} catch {", 1)[0]
        self.assertNotIn("Enable-ScheduledTask", success)
        self.assertNotIn("Start-ScheduledTask", success)
        self.assertNotIn("$resumed=$true", success)
        self.assertIn("BACKUP_FAILED_SAME_ORIGINAL_OWNER_RESUMED", script)
        for forbidden in (
                "Register-ScheduledTask", "New-ScheduledTask",
                "Set-ScheduledTask", "workflow_dispatch",
                "gh api --method POST", "gh api --method PATCH"):
            self.assertNotIn(forbidden, script)
        workflows = ROOT / ".github" / "workflows"
        for path in workflows.glob("*.yml"):
            self.assertNotIn(HOLD_PS.name, path.read_text("utf-8"))

    @unittest.skipUnless(os.name == "nt", "Native Windows PowerShell parser")
    def test_native_windows_hold_wrapper_parses(self):
        exe = shutil.which("powershell.exe")
        self.assertIsNotNone(exe)
        program = (
            "$t=$null;$errors=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "$env:F139_HOLD_PS,[ref]$t,[ref]$errors)|Out-Null;"
            "if(@($errors).Count -ne 0){"
            "$errors|ForEach-Object{Write-Output $_.Message};exit 1}")
        result = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", program],
            env={**os.environ, "F139_HOLD_PS": str(HOLD_PS)},
            capture_output=True, text=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0,
                         result.stdout+"\n"+result.stderr)


if __name__ == "__main__":
    unittest.main()

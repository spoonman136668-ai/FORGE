"""V55 owner-source release tests: synthetic detached-only, never live."""
import inspect
import os
import sqlite3
import unittest
from unittest.mock import patch

from f139.local_controller import Database, SingleOwner
from f139.nci04_v55_detached_activation import rehearse_v45_source_and_activation
from f139.nci04_v55_forward_transition import make_proof, SOURCE
from f139 import nci04_v55_owner_release as release
from f139 import nci04_v55_owner_release_cli as cli
from f139.test_nci04_v55_detached_activation import V55DetachedActivation


class OriginalV55SourceReleaseTests(unittest.TestCase):
    def setUp(self):
        fixture = V55DetachedActivation(
            "test_detached_transition_and_activation_are_atomic_and_once_only"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.path = fixture.path
        for x in (
            patch.object(release, "verified_historical_foundation",
                         return_value=None),
            patch.object(release, "verify_native_activation",
                         return_value=True),
        ):
            x.start()
            self.addCleanup(x.stop)

    def proof(self):
        args = self.fixture.args()
        with SingleOwner(self.path.with_suffix(".lock")):
            return make_proof(self.db, **args)

    def test_original_readonly_snapshot_custody_has_no_writes(self):
        before = self.db.conn.total_changes
        first = release.original_snapshot(self.db)
        self.assertEqual(first, release.original_snapshot(self.db))
        self.assertEqual(first["source_sha"], SOURCE)
        self.assertEqual(first["head_seq"], 1849)
        self.assertEqual(first["verified_historical_tasks"], 154)
        self.assertEqual(first["custodied_negative_tasks"], 56)
        self.assertEqual(len(first["custodied_negative_tickets"]), 56)
        self.assertEqual(before, self.db.conn.total_changes)

    def test_same_owner_mutex_required_before_any_mutation(self):
        proof = self.proof()
        before = self.db.conn.total_changes
        with self.assertRaisesRegex(ValueError, "EXCLUSIVE_WRITER_REQUIRED"):
            release.apply_copy_or_original(self.db, proof)
        self.assertEqual(before, self.db.conn.total_changes)
        self.assertEqual(self.db.meta()["source_sha"], SOURCE)

    def test_real_two_event_source_and_activation_calls_existing_native_approval(self):
        from f139.nci04_owner_ledger import (
            ACTIVATION_KIND, ACTIVATION_SCHEMA, SEALED_OWNER_PREFIX_HEAD
        )
        proof = self.proof()
        approvals = []
        def existing_native(db, approval):
            approvals.append(approval)
            with db.transaction():
                db.event(ACTIVATION_KIND, {
                    "schema": ACTIVATION_SCHEMA,
                    "source_sha": approval["source_sha"],
                    "prior_event_head_sha256": db.meta()["head_hash"],
                    "sealed_original_prefix_sha256": SEALED_OWNER_PREFIX_HEAD,
                    "verified_original_tasks": 4,
                    "verified_d2k_tasks": 2,
                    "new_dispatches": 0,
                    "scientific_first_use": False,
                    "development_only": True,
                })
            return True
        with patch.object(release, "activate_native", side_effect=existing_native):
            with SingleOwner(self.path.with_suffix(".lock")):
                result = release.apply_copy_or_original(self.db, proof)
        self.assertEqual(len(approvals), 1)
        self.assertTrue(approvals[0]["native_development_approved"])
        self.assertFalse(approvals[0]["scientific_first_use"])
        self.assertFalse(approvals[0]["create_controller"])
        self.assertEqual(approvals[0]["paid_api_calls"], 0)
        self.assertEqual(result["head_seq"], 1851)
        self.assertTrue(result["original_ledger_verified"])
        self.assertEqual(self.db.meta()["source_sha"], self.fixture.args()["target"])
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE seq>=1850").fetchone()[0], 2)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE stage='QUARANTINED'").fetchone()[0], 56)

    def test_failure_after_transition_is_hold_never_replay(self):
        proof = self.proof()
        with patch.object(release, "activate_native", return_value=False):
            with SingleOwner(self.path.with_suffix(".lock")):
                with self.assertRaisesRegex(ValueError, "ACTIVATION_FAILED_HOLD"):
                    release.apply_copy_or_original(self.db, proof)
        self.assertEqual(self.db.meta()["head_seq"], 1850)
        self.assertNotEqual(self.db.meta()["source_sha"], SOURCE)
        with SingleOwner(self.path.with_suffix(".lock")):
            with self.assertRaises(ValueError):
                release.apply_copy_or_original(self.db, proof)

    def test_cli_requires_first_attempt_authenticated_original_windows_owner(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp)/"state.sqlite"
            db.write_bytes(b"synthetic-not-a-usable-ledger")
            with patch.dict(os.environ, {
                "GITHUB_REPOSITORY":"attacker/repo",
                "GITHUB_EVENT_NAME":"issue_comment",
                "GITHUB_ACTOR":"attacker",
            }):
                with self.assertRaises(ValueError):
                    cli.main(["--mode","preflight","--db",str(db)])

    def test_preflight_reports_cold_verified_terminal_counts_to_shell(self):
        from unittest.mock import MagicMock
        snapshot = {
            "verified_historical_tasks": 154,
            "custodied_negative_tasks": 56,
            "terminal_tasks_sha256": "f"*64,
        }
        fake = MagicMock()
        fake.meta.return_value = {
            "source_sha": SOURCE,
            "head_seq": 1849,
            "head_hash": "e"*64,
        }
        with patch.object(cli.Database, "open_readonly", return_value=fake), \
             patch.object(cli, "original_snapshot", return_value=snapshot):
            got = cli.read_frozen(self.path)
        self.assertEqual(got["verified_historical_tasks"], 154)
        self.assertEqual(got["custodied_negative_tasks"], 56)
        self.assertEqual(got["head_seq"], 1849)
        self.assertEqual(got["terminal_tasks_sha256"], "f"*64)
        fake.close.assert_called_once()

    def test_original_workflow_only_admits_fresh_v55_suffix_through_guarded_bridge(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        launcher = (root/"f139/v54_original_owner_repair.ps1").read_text(encoding="utf-8")
        successor = (root/"f139/v55_original_owner_repair.ps1").read_text(encoding="utf-8")
        workflow = (root/".github/workflows/f139-v54-original-owner-release.yml").read_text(encoding="utf-8")
        self.assertIn("F139-V54-OWNER-RELEASE '+$Main+' V55", launcher)
        self.assertIn("F139_V55_BRIDGE_AUTHENTICATION_HOLD", launcher)
        self.assertIn("v55_original_owner_repair.ps1", launcher)
        self.assertIn("F139-V54-OWNER-RELEASE '+$Main+' V55", successor)
        self.assertIn("F139_V55_FORWARD_ONLY_HOLD_NO_REPLAY", successor)
        self.assertIn("f139-v54-original-owner-release.yml", successor)
        self.assertIn("startsWith(github.event.comment.body, 'F139-V54-OWNER-RELEASE ')", workflow)
        self.assertNotIn("Register-ScheduledTask", launcher)

    def test_release_shell_invokes_existing_cli_and_binds_backup_pins(self):
        from pathlib import Path
        script = (Path(__file__).with_name(
            "v55_original_owner_repair.ps1")).read_text(encoding="utf-8")
        self.assertEqual(script.count(
            "& $python -B -m f139.nci04_v55_owner_release_cli --mode @cliArgs"
        ), 1)
        self.assertNotIn("f139.nci04_v55_owner_forward_repair_cli", script)
        self.assertEqual(script.count("$b=InvokeNative @('backup'"), 1)
        backup = script.split("$b=InvokeNative @('backup'", 1)[1].split(
            "'F139_V55_COLD_BACKUP='", 1)[0]
        self.assertIn("'--binary-sha',$binarySha", backup)
        self.assertIn("'--mechanism-sha',$mechanismSha", backup)
        self.assertIn("'--rehearsal-run-id',([string]$priorRehearsal)", backup)
        self.assertIn("$pref.verified_historical_tasks -ge 154", script)
        self.assertIn("$pref.custodied_negative_tasks -ge 56", script)

    def test_original_owner_github_get_retry_is_bounded_and_read_only(self):
        """Execute real PowerShell GET helper with isolated, mocked transport."""
        from pathlib import Path
        import shutil
        import subprocess
        script = Path(__file__).with_name("v55_original_owner_repair.ps1").read_text(
            encoding="utf-8"
        )
        function_source = script.split("function Need(", 1)[1].split(
            "\nfunction Field(", 1
        )[0]
        function_source = "function Need(" + function_source
        self.assertEqual(function_source.count("gh api --method GET"), 1)
        self.assertNotIn("gh api --method POST", function_source)
        self.assertNotIn("gh api --method PATCH", function_source)
        self.assertIn("$attempt -le 3", function_source)
        self.assertIn("GITHUB_GET_FAILED", function_source)
        pwsh = shutil.which("pwsh")
        if not pwsh:
            self.skipTest("PowerShell integration runs on Windows qualification")
        body = r'''
$ErrorActionPreference='Stop'
$script:n=0
$script:delays=0
function Start-Sleep {param([int]$Seconds) $script:delays+=$Seconds}
function gh {
  param([Parameter(ValueFromRemainingArguments=$true)][string[]]$p)
  if($p.Count -ne 4 -or $p[0] -cne 'api' -or
     $p[1] -cne '--method' -or $p[2] -cne 'GET' -or
     $p[3] -cne 'repos/spoonman136668-ai/FORGE/issues/807') {
    throw 'TEST_UNEXPECTED_NON_GET_OR_ROUTE'
  }
  $script:n++
  if($script:n -lt 3) { $global:LASTEXITCODE=1; return }
  $global:LASTEXITCODE=0
  return '{"ok":true}'
}
$x=GetJson 'repos/spoonman136668-ai/FORGE/issues/807'
if(-not $x.ok -or $script:n -ne 3 -or $script:delays -ne 6){
  throw 'TEST_READ_RETRY_BEHAVIOR'
}
$script:n=0
$script:delays=0
function gh {
  param([Parameter(ValueFromRemainingArguments=$true)][string[]]$p)
  if($p[2] -cne 'GET') {throw 'TEST_NOT_GET'}
  $script:n++
  $global:LASTEXITCODE=1
}
try {
  $null=GetJson 'repos/spoonman136668-ai/FORGE/issues/807'
  throw 'TEST_UNEXPECTED_ACCEPT'
} catch {
  if($_.Exception.Message -notlike '*F139_V55_REPAIR_GITHUB_GET_FAILED*'){
    throw
  }
}
if($script:n -ne 3 -or $script:delays -ne 6){
  throw 'TEST_EXHAUSTION_NOT_BOUNDED'
}
$script:n=0
function gh {
  param([Parameter(ValueFromRemainingArguments=$true)][string[]]$p)
  $script:n++
  $global:LASTEXITCODE=0
  return '{invalid'
}
try {
  $null=GetJson 'repos/spoonman136668-ai/FORGE/issues/807'
  throw 'TEST_UNEXPECTED_JSON_ACCEPT'
} catch {
  if($_.Exception.Message -notlike '*F139_V55_REPAIR_GITHUB_GET_INVALID_JSON*'){
    throw
  }
}
if($script:n -ne 1){throw 'TEST_INVALID_JSON_RETRIED'}
Write-Output 'F139_V55_TRANSPORT_NEGATIVES_PASS'
'''
        result = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command", "-"],
            input=function_source + "\n" + body + "\n",
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0,
                         result.stdout[-1000:] + result.stderr[-2000:])
        self.assertIn("F139_V55_TRANSPORT_NEGATIVES_PASS", result.stdout)

    def test_no_new_scheduler_or_runner_interface_in_release_module(self):
        source = inspect.getsource(release)
        self.assertIn("activate_native(db, approval)", source)
        self.assertIn("db.transaction()", source)
        for forbidden in ("Register-ScheduledTask","New-ScheduledTask",
                          "gh api --method POST", "def run_controller",
                          "def publish_model_once", "scientific_first_use=True"):
            self.assertNotIn(forbidden,source)


if __name__ == "__main__":
    unittest.main()

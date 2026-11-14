"""Guard one exact original-owner workflow addition; no live owner operations."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import textwrap
import unittest

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/".github/workflows/f139-v41-original-owner-live-install.yml"
BEFORE="b7abc3a9118a5c69dd24b4f351bf5697bfdf52f3"
AFTER="ff11352d1d298361e97b1e7422338f608d4b2a70"
BRANCH="engineering/f139-hybrid-reader-route-20261110"

def digest(blob):
    return hashlib.sha1(b"blob "+str(len(blob)).encode()+b"\0"+blob).hexdigest()

class ExactOwnerWorkflowBridge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob=FILE.read_bytes().replace(b"\r\n",b"\n")
        cls.body=cls.blob.decode("utf-8")
        cls.before, marker, cls.new_job=cls.body.partition(
            "  hybrid-v41-paired-original-owner-backup:\n")
        cls.marker=marker

    def test_existing_job_source_is_exact_and_workflow_is_pinned(self):
        self.assertTrue(self.marker)
        self.assertTrue(self.before.endswith("\n\n"))  # one blank separator
        self.assertEqual(digest(self.before[:-1].encode()),BEFORE)
        self.assertEqual(digest(self.blob),AFTER)
        self.assertEqual(self.body.count(self.marker),1)
        for job in ("original-owner-v41-live-install",
                    "original-owner-v41-readiness","original-owner-v41-copy-rehearsal"):
            self.assertEqual(self.before.count("  "+job+":"),1)

    def test_new_job_is_existing_original_owner_only(self):
        for required in ("github.actor == 'spoonman136668-ai'",
                         "github.repository == 'spoonman136668-ai/FORGE'",
                         "github.event.issue.number == 807",
                         "!github.event.issue.pull_request",
                         "F139-HYBRID-V41-PAUSE-RESUME ",
                         "runs-on: [self-hosted, Windows, forge-codex-isolated]",
                         "RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'",
                         "GITHUB_REF -cne 'refs/heads/main'",
                         "GITHUB_RUN_ATTEMPT -cne '1'",
                         "persist-credentials: false", "fetch-depth: 0",
                         "contents: read", "issues: read","actions: read",
                         "v41_hybrid_owner_pause_backup_resume.ps1"):
            self.assertIn(required,self.new_job)
        for forbidden in ("Register-ScheduledTask","Disable-ScheduledTask",
                          "Start-ScheduledTask","Set-ScheduledTask",
                          "workflow_dispatch:","schedule:","repository_dispatch:",
                          "gh api --method PATCH","gh api --method POST"):
            self.assertNotIn(forbidden,self.new_job)

    def test_no_general_workflow_permission_or_new_trigger(self):
        from scripts import check_rar_g145_pr_scope as scope
        self.assertEqual(scope.HYBRID_OWNER_WORKFLOW_BRANCH,BRANCH)
        self.assertEqual(scope.HYBRID_OWNER_WORKFLOW_AFTER,AFTER)
        frozen,paths=scope.FROZEN_SCOPES[BRANCH]
        self.assertEqual(frozen,"1a40fe4e3ec6e93a1631d59863b95e90981d734e")
        self.assertIn(str(FILE.relative_to(ROOT)).replace("\\","/"),paths)
        self.assertFalse(scope.generic_paths_safe(
            [".github/workflows/f139-v41-original-owner-live-install.yml"]))
        self.assertEqual(self.before.count("  issue_comment:"),1)
        self.assertEqual(self.body.count("  issue_comment:"),1)
        for trigger in ("  schedule:","  workflow_dispatch:",
                        "  pull_request:","  repository_dispatch:"):
            self.assertNotIn(trigger,self.body)

    @unittest.skipUnless(os.name=="nt","Native Windows PowerShell parser")
    def test_original_windows_powershell_parser(self):
        script=textwrap.dedent(self.new_job.split("        run: |\n",1)[1])
        exe=shutil.which("powershell.exe")
        self.assertIsNotNone(exe)
        code=(
            "$ErrorActionPreference='Stop';$t=$null;$e=$null;"
            "[System.Management.Automation.Language.Parser]::ParseInput("
            "$env:F139_HYBRID_PS,[ref]$t,[ref]$e)|Out-Null;"
            "if($null -ne $e -and @($e).Count -gt 0){"
            "$e|ForEach-Object{Write-Output $_.Message};exit 1}")
        p=subprocess.run([exe,"-NoProfile","-NonInteractive","-Command",code],
            env={**os.environ,"F139_HYBRID_PS":script},capture_output=True,
            timeout=30,check=False,text=True)
        self.assertEqual(p.returncode,0,p.stdout+"\n"+p.stderr)

if __name__=="__main__":unittest.main()

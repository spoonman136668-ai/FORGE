"""Source-only original task lifecycle qualification; never invokes owner task."""
from pathlib import Path
import os
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
WRAPPER=ROOT/"f139/v41_hybrid_owner_pause_backup_resume.ps1"


class HybridOriginalTaskWrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=WRAPPER.read_text(encoding="utf-8")

    def test_single_original_task_not_new_scheduler(self):
        src=self.source
        self.assertIn("$name='FORGE-F139-UnifiedController'",src)
        self.assertIn("F139OriginalOwnerMutex",src)
        self.assertIn("Disable-ScheduledTask -TaskName $name",src)
        self.assertIn("Stop-ScheduledTask -TaskName $name",src)
        self.assertIn("Enable-ScheduledTask -TaskName $name",src)
        self.assertIn("Start-ScheduledTask -TaskName $name",src)
        for forbidden in ("Register-ScheduledTask","Unregister-ScheduledTask",
                          "Set-ScheduledTask -TaskName", "New-ScheduledTaskTrigger",
                          "New-ScheduledTaskAction","workflow_dispatch",
                          "repository_dispatch", "Set-ItemProperty",
                          "gh api --method PATCH","gh api --method POST",
                          "Start-Job ", "Start-ThreadJob "):
            self.assertNotIn(forbidden,src)

    def test_paired_request_and_exact_github_source_before_pause(self):
        src=self.source
        self.assertIn("$approvalMode=if($Hold){'PAUSE-HOLD'}else{'PAUSE-RESUME'}",src)
        self.assertIn("'^F139-HYBRID-V41-'+$approvalMode",src)
        self.assertIn("if($Hold){$args+=('--hold')}",src)
        self.assertIn("F139_HYBRID_V41_PAIRED_PREFLIGHT=",src)
        self.assertIn("GITHUB_RUN_ATTEMPT -ceq '1'",src)
        self.assertIn("GITHUB_SHA -ceq $Target",src)
        self.assertIn("$pre=Invoke-Pair $true 120000",src)
        self.assertLess(src.index("$pre=Invoke-Pair"),
                        src.index("Disable-ScheduledTask -TaskName $name"))
        self.assertLess(src.index("Main\n$policyBefore=Policy"),
                        src.index("Disable-ScheduledTask -TaskName $name"))
        self.assertIn("TaskArg $t 'RepositoryRoot'",src)
        self.assertIn("TaskArg $t 'Database'",src)
        self.assertIn("TaskArg $t 'PythonExe'",src)
        self.assertIn("ORIGINAL_TASK_SID_OR_TOPOLOGY_DRIFT",src)

    def test_bounded_child_and_forward_only_uncertain_effects(self):
        src=self.source
        self.assertIn("$proc.WaitForExit($limitMs)",src)
        self.assertIn("$proc.WaitForExit(30000)",src)
        self.assertIn("CANDIDATE_CHILD_UNCERTAIN_EFFECT",src)
        self.assertIn("$script:backupChildCleared=$false",src)
        self.assertIn("if($paused -and -not $startAttempted -and $backupChildCleared)",src)
        self.assertIn("ORIGINAL_OWNER_RECOVERY_HOLD",src)
        self.assertIn("SAME_ORIGINAL_OWNER_RESUMED=PASS",src)
        self.assertNotIn("Copy-Item",src)
        self.assertNotIn("Restore-ScheduledTask",src)
        self.assertNotIn("UPDATE meta SET",src)

    def test_receipt_proves_backup_not_hybrid_source_release(self):
        src=self.source
        for val in ("independent_detached_restore_verified",
                    "provider_archives_bytes_verified",
                    "generation_binary_bytes_verified",
                    "original_owner_mutations -eq 0",
                    "source_transition_authorized -eq $false",
                    "hybrid_admission -eq $false",
                    "scientific_first_use -eq $false"):
            self.assertIn(val,src)
        self.assertIn("F139_HYBRID_V41_SOURCE_TRANSITION=FALSE",src)
        self.assertIn("F139_HYBRID_V41_SCIENTIFIC_FIRST_USE=FALSE",src)

    @unittest.skipUnless(os.name=="nt","Windows PowerShell parser only")
    def test_native_windows_powershell_parser(self):
        exe=shutil.which("powershell.exe")
        self.assertIsNotNone(exe)
        code=(
            "$ErrorActionPreference='Stop';$tok=$null;$err=$null;"
            "[System.Management.Automation.Language.Parser]::ParseFile("
            "$env:F139_HYBRID_WRAPPER_FILE,[ref]$tok,[ref]$err)|Out-Null;"
            "if($null -ne $err -and @($err).Count -gt 0){"
            "$err|ForEach-Object{Write-Output $_.Message};exit 1}"
        )
        p=subprocess.run([exe,"-NoProfile","-NonInteractive","-Command",code],
                         env={**os.environ,"F139_HYBRID_WRAPPER_FILE":str(WRAPPER)},
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         timeout=30,check=False,text=True)
        self.assertEqual(p.returncode,0,(p.stdout+"\n"+p.stderr)[:2000])

    def test_wrapper_not_executed_by_tests(self):
        self.assertTrue(WRAPPER.is_file())
        self.assertNotIn("New-ScheduledTask",self.source)


if __name__=="__main__":
    unittest.main()

"""Exact original-owner Hybrid cutover wiring; never touches a real task.

Final source qualification includes real original SQL fixtures in the existing
V41 successor tests. These checks prove the new entrypoint's safe boundaries,
not live task/SID/Windows original acceptance.
"""
from pathlib import Path
import os
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"f139/v41_hybrid_original_activate.ps1"
WF=ROOT/".github/workflows/f139-v41-original-owner-live-install.yml"
BACKUP=ROOT/"f139/v41_hybrid_owner_pause_backup_resume.ps1"
COMMIT=ROOT/"f139/v41_hybrid_original_source_commit.ps1"


class V41HybridCutoverTests(unittest.TestCase):
    def test_reuses_original_workflow_not_second_controller_or_scheduler(self):
        workflow=WF.read_text("utf-8")
        self.assertEqual(workflow.count("  hybrid-v41-original-pause-hold:"),1)
        self.assertEqual(workflow.count("  hybrid-v41-original-readiness:"),1)
        self.assertEqual(workflow.count("  hybrid-v41-original-source-commit:"),1)
        self.assertEqual(workflow.count("  hybrid-v41-original-source-activate:"),1)
        self.assertEqual(workflow.count("  hybrid-v41-original-precommit-abort:"),1)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]",workflow)
        self.assertIn("group: forge-f139-v41-original-owner-live-install",workflow)
        self.assertIn("cancel-in-progress: false",workflow)
        for text in (
            "'F139-HYBRID-V41-PAUSE-HOLD '",
            "'F139-HYBRID-V41-SOURCE-READINESS '",
            "'F139-HYBRID-V41-SOURCE-COMMIT '",
            "'F139-HYBRID-V41-SOURCE-ACTIVATE '",
            "'F139-HYBRID-V41-SAFE-ABORT '",
            "github.event.issue.number == 807",
            "github.actor == 'spoonman136668-ai'",
            "RUNNER_NAME -cne 'FORGE-CODEX-REMOTE'",
            "GITHUB_RUN_ATTEMPT -cne '1'",
        ):
            self.assertIn(text,workflow)
        self.assertNotIn("workflow_dispatch:",workflow)
        self.assertNotIn("schedule:",workflow)
        self.assertNotIn("Register-ScheduledTask",workflow)
        self.assertNotIn("New-ScheduledTask ",workflow)

    def test_old_pause_resume_still_distinct_and_stages_target_before_hold(self):
        workflow=WF.read_text("utf-8")
        self.assertIn("startsWith(github.event.comment.body, 'F139-HYBRID-V41-PAUSE-RESUME ')",workflow)
        self.assertIn('& $wrapper -Target $env:GITHUB_SHA',workflow)
        hold=workflow.split("  hybrid-v41-original-pause-hold:",1)[1].split(
            "  hybrid-v41-original-readiness:",1)[0]
        self.assertIn("git clone --quiet --no-hardlinks --no-checkout",hold)
        self.assertIn("checkout --quiet --detach $env:GITHUB_SHA",hold)
        self.assertIn("status --porcelain --untracked-files=all",hold)
        self.assertIn("74dd90e6d71da6b53898c7a80d5362f1b0e6af27",hold)
        self.assertLess(hold.index("git clone --quiet"),hold.index(" -Hold"))
        self.assertIn('& "$env:GITHUB_WORKSPACE/f139/v41_hybrid_owner_pause_backup_resume.ps1" -Target $env:GITHUB_SHA -Hold',hold)
        self.assertIn("[switch]$Hold",BACKUP.read_text("utf-8"))
        self.assertIn("F139_HYBRID_V41_ORIGINAL_SOURCE_COMMIT_HOLD=PASS",COMMIT.read_text("utf-8"))

    def test_activation_is_real_same_task_not_new_task_or_replayed_commit(self):
        s=SCRIPT.read_text("utf-8")
        for required in (
            "F139-HYBRID-V41-SOURCE-ACTIVATE ",
            "SOURCE-ACTIVATE '+$Target+' [1-9][0-9]*$",
            "nci04_v41_hybrid_forward_postcommit as postcommit",
            "postcommit.original_postcommit(db,dict(os.environ),previous,api)",
            'receipt["event_seq"]==1831',
            "source_event_seq -eq 1831",
            "F139_HYBRID_V38_EVENT1831_ACTIVATION_PREFLIGHT=",
            "Get-ScheduledTask -TaskName $name",
            "Set-ScheduledTask -TaskName $name -Action $newAction",
            "upgrade-hybrid-lane",
            "F139_HYBRID_V41_LANE_SCHEMA_MIGRATION=PASS",
            "$p.lanes=@('Wingless','Yggdrasil','TTT-Hybrid')",
            "New-ScheduledTaskAction",
            "Enable-ScheduledTask -TaskName $name",
            "Start-ScheduledTask -TaskName $name",
            "F139_HYBRID_V41_ORIGINAL_CONTROLLER_PROCESS=PASS",
            "Database.open_readonly(Path(sys.argv[1]))",
            "F139_HYBRID_V41_THREE_LANE_COLD_READBACK=PASS",
            "F139_HYBRID_V41_FORWARD_REPAIR_HOLD_NO_REPLAY",
            "F139_HYBRID_V41_SCIENTIFIC_FIRST_USE=FALSE",
        ):
            self.assertIn(required,s)
        for forbidden in (
            "Register-ScheduledTask", "New-ScheduledTask -",
            "workflow_dispatch", "Restore-Sqlite", "Restore-Database",
            "sqlite3.connect(p)","UPDATE meta SET", "DELETE FROM events",
            "SOURCE_TRANSITION_ADMITTED", "FORGE-F139-NewController",
        ):
            self.assertNotIn(forbidden,s)
        self.assertEqual(s.count("Set-ScheduledTask -TaskName $name"),1)
        self.assertEqual(s.count("Start-ScheduledTask -TaskName $name"),1)
        self.assertEqual(s.count("Enable-ScheduledTask -TaskName $name"),1)
        self.assertIn('receipt["original_owner_mutations"]==0',s)
        self.assertIn("postcommit.original_postcommit(",s)
        self.assertIn("SELECT COUNT(*) FROM tasks WHERE stage='QUARANTINED'",s)

    def test_activate_requires_distinct_comment_before_any_task_mutation(self):
        script=SCRIPT.read_text("utf-8")
        self.assertLess(script.index("EVENT1831_ACTIVATION_PREFLIGHT="),
                        script.index("Set-ScheduledTask -TaskName"))
        self.assertLess(script.index("Get-ScheduledTask -TaskName"),
                        script.index("Set-ScheduledTask -TaskName"))
        self.assertLess(script.index("upgrade-hybrid-lane"),
                        script.index("gh api --method PATCH"))
        self.assertLess(script.index("gh api --method PATCH"),
                        script.index("Enable-ScheduledTask -TaskName"))
        self.assertLess(script.index("Enable-ScheduledTask -TaskName"),
                        script.index("Start-ScheduledTask -TaskName"))


    def test_event1831_bridge_preserves_original_hold_and_rejects_old_preimage(self):
        s=SCRIPT.read_text("utf-8")
        self.assertIn("Source $root $heldSource",s)
        self.assertIn("'2c7caad5a4502d4b874a11d57207a35cf033eb08'",s)
        self.assertIn("'c611c4362e3cc867984448a03ecdf3be923d2ef1'",s)
        self.assertNotIn("Source $root $old",s)
        self.assertNotIn("nci04_v41_hybrid_original_commit as commit",s)
        self.assertNotIn("nci04_v41_hybrid_held_recovery as held",s)
        self.assertNotIn("held.inspect_held_ledger(original,req)",s)
        self.assertIn("postcommit_id<current_id",s)
        self.assertIn("prior[\"body\"].startswith(postcommit.PREFIX+target+",s)
        self.assertIn("original_owner_mutations=0",s)
        self.assertIn("custodied_negative_tasks=56",s)
        self.assertLess(s.index("postcommit.original_postcommit("),
                        s.index("Set-ScheduledTask -TaskName"))
        self.assertLess(s.index("source_event_seq -eq 1831"),
                        s.index("Set-ScheduledTask -TaskName"))
        self.assertLess(s.index("upgrade-hybrid-lane"),
                        s.index("gh api --method PATCH"))

    def test_embedded_v38_preflight_is_syntactically_valid_python(self):
        script=SCRIPT.read_text("utf-8")
        self.assertEqual(script.count("$program=@'\n"),1)
        embedded=script.split("$program=@'\n",1)[1].split(
            "\n'@\n$env:PYTHONPATH",1)[0]
        compile(embedded,"<f139-v38-activation-preflight>","exec")
        for marker in (
            'postcommit_id<current_id',
            'readiness._owner_comment(get,current_id,body)',
            'postcommit.original_postcommit(db,dict(os.environ),previous,api)',
            'receipt["event_seq"]==1831',
            'receipt["custodied_negative_tasks"]==56',
            'receipt["original_owner_mutations"]==0',
            'receipt["scientific_first_use"] is False',
        ):
            self.assertIn(marker,embedded)

    @unittest.skipUnless(os.name=="nt","native Windows PowerShell parser")
    def test_native_windows_ps51_parser(self):
        exe=shutil.which("powershell.exe")
        self.assertIsNotNone(exe)
        ps=(
          "$t=$null;$err=$null;"
          "[System.Management.Automation.Language.Parser]::ParseFile("
          "$env:F139_HYBRID_ACTIVATION_SCRIPT,[ref]$t,[ref]$err)|Out-Null;"
          "if(@($err).Count -ne 0){$err|ForEach-Object{$_|Out-String};exit 1}")
        check=subprocess.run(
          [exe,"-NoProfile","-NonInteractive","-Command",ps],
          env={**os.environ,"F139_HYBRID_ACTIVATION_SCRIPT":str(SCRIPT)},
          text=True,capture_output=True,timeout=30,check=False)
        self.assertEqual(check.returncode,0,check.stdout+"\n"+check.stderr)


if __name__=="__main__":
    unittest.main()

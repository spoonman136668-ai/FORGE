"""V46 guarded original event1836 source release negative and source controls."""
from __future__ import annotations

import copy
import inspect
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

from f139 import nci04_v46_live_source_commit as live
from f139 import nci04_v42_owner_source_readiness as v42
from f139 import nci04_v44_event1836_copy_rehearsal as v44
from f139 import nci04_v45_original_rehearsal_gate as v45


class LiveV46Tests(unittest.TestCase):
    def fake(self):
        sha = "f" * 40
        rid = 43999999999
        cid = v45.V44_COMMENT + 123
        now = "2026-11-16T18:30:00Z"
        body = live.PREFIX+sha+" "+live.TARGET+" "+str(v45.V44_COMMENT)
        env = dict(GITHUB_SHA=sha,GITHUB_RUN_ID=str(rid),
                   GITHUB_REPOSITORY=v42.REPO,
                   GITHUB_ACTOR=v42.OWNER,
                   GITHUB_EVENT_NAME="issue_comment",
                   GITHUB_REF="refs/heads/main",
                   GITHUB_RUN_ATTEMPT="1",
                   RUNNER_NAME="FORGE-CODEX-REMOTE")
        event = dict(action="created",
                     issue=dict(number=807,user=dict(login=v42.OWNER)),
                     sender=dict(login=v42.OWNER),
                     comment=dict(id=cid,body=body,
                                  created_at=now,updated_at=now,
                                  user=dict(login=v42.OWNER),
                                  author_association="OWNER"))
        p = "repos/"+v42.REPO+"/"
        record = dict(**event["comment"],
                      issue_url="https://api.github.com/repos/"+
                          v42.REPO+"/issues/807")
        old = dict(id=v45.V44_COMMENT,
                   body="F139-V44-COPY-REHEARSAL "+
                        v45.V44_MAIN+" "+live.TARGET+" 6916414055",
                   created_at="2026-11-16T12:55:16Z")
        data = {
            p+"issues/comments/"+str(cid):record,
            p+"issues/comments/"+str(v45.V44_COMMENT):old,
            p+"compare/"+live.TARGET+"..."+sha+
               "?per_page=1&page=2":dict(
                   status="ahead",behind_by=0,
                   merge_base_commit=dict(sha=live.TARGET)),
        }
        def get(route):
            if route not in data:raise AssertionError("unexpected GET: "+route)
            return copy.deepcopy(data[route])
        return env,event,data,get

    def invoke(self,env,event,get):
        # Pure remote authentication exercised with native-platform predicates
        # simulated; no real process or native task is ever contacted.
        with patch.object(live.sys,"platform","win32"), \
             patch.object(live.os,"name","nt"), \
             patch.object(v45,"qualify",return_value={"v44_original_job_status":"success"}), \
             patch.object(v42,"release_source",return_value={"main_qualification_job_count":8,
                                                             "main_qualification_run_id":43900000000}):
            return live.request(get,env,event)

    def test_owner_authenticated_v44_and_main_custody(self):
        env,event,data,get=self.fake()
        out=self.invoke(env,event,get)
        self.assertEqual(out["comment_id"],event["comment"]["id"])
        self.assertEqual(out["v44_run_id"],v45.V44_RUN)
        self.assertEqual(live.TARGET,v44.RELEASE_SOURCE)
        self.assertEqual(live.EXPECTED_V44_PROOF,
                         "70474d338d4c379b42362ca3cd24d7d02a0e9ac82b4fb8b018454e7c1822112c")

    def test_forged_owner_and_unsafe_replay_rejected(self):
        variants=[
            ("env","GITHUB_ACTOR","other"),
            ("env","GITHUB_REF","refs/heads/old"),
            ("env","GITHUB_RUN_ATTEMPT","2"),
            ("env","RUNNER_NAME","other"),
            ("env","OPENAI_API_KEY","paid"),
            ("event","action","edited"),
            ("issue","number",1715),
            ("comment","id",v45.V44_COMMENT),
            ("comment","body","F139-V44-COPY-REHEARSAL forged"),
            ("comment","author_association","CONTRIBUTOR"),
            ("sender","login","other"),
        ]
        for kind,key,value in variants:
            with self.subTest(kind=kind,key=key):
                env,event,data,get=self.fake()
                if kind=="env":env[key]=value
                elif kind=="event":event[key]=value
                else:event[kind][key]=value
                with self.assertRaises(live.OriginalV46Denied):
                    self.invoke(env,event,get)

    def test_remote_replay_and_release_ancestry_fail_closed(self):
        for mode in ("owner_body","owner_timestamp","v44_body","source_ancestry","main_ci"):
            with self.subTest(mode=mode):
                env,event,data,get=self.fake()
                p="repos/"+v42.REPO+"/"
                if mode=="owner_body":
                    data[p+"issues/comments/"+str(event["comment"]["id"])]["body"]="forged"
                elif mode=="owner_timestamp":
                    data[p+"issues/comments/"+str(event["comment"]["id"])]["created_at"]="yesterday"
                elif mode=="v44_body":
                    data[p+"issues/comments/"+str(v45.V44_COMMENT)]["body"]="forged"
                elif mode=="source_ancestry":
                    data[p+"compare/"+live.TARGET+"..."+env["GITHUB_SHA"]+
                         "?per_page=1&page=2"]["behind_by"]=1
                if mode=="main_ci":
                    with patch.object(live.sys,"platform","win32"), \
                         patch.object(live.os,"name","nt"), \
                         patch.object(v45,"qualify",return_value={"v44_original_job_status":"success"}), \
                         patch.object(v42,"release_source",return_value={"main_qualification_job_count":7}):
                        with self.assertRaises(live.OriginalV46Denied):
                            live.request(get,env,event)
                else:
                    with self.assertRaises(live.OriginalV46Denied):
                        self.invoke(env,event,get)

    def test_disabled_task_readback_fail_closed(self):
        db_path=Path("/not-a-real-db")
        for code,output in ((1,b""),(0,b"unexpected"),(0,live.ORIGINAL_TASK_MARKER)):
            with self.subTest(code=code):
                run=lambda *a,**kw: subprocess.CompletedProcess(a,code,output,b"")
                with patch.object(live.sys,"platform","win32"), \
                     patch.object(live.os,"name","nt"), \
                     patch.object(live.shutil,"which",return_value="powershell.exe"):
                    if code == 0 and output==live.ORIGINAL_TASK_MARKER:
                        self.assertTrue(live.disabled_original_task(db_path,runner=run))
                    else:
                        with self.assertRaises(live.OriginalV46Denied):
                            live.disabled_original_task(db_path,runner=run)

    def test_original_task_script_is_guarded_and_single_owner(self):
        script=(Path(__file__).resolve().parents[1]/
                "f139/v46_original_owner_live_install.ps1").read_text(encoding="utf-8")
        self.assertIn("F139-V46-LIVE-INSTALL ",script)
        self.assertIn("af204acc983719b382bc8daf2216ec6733ca3ee7",script)
        self.assertIn("4ccbb84785a43e038453d6f2bda5415ecb364084",script)
        self.assertIn("Set-ScheduledTask -TaskName $name",script)
        self.assertIn("Disable-ScheduledTask -TaskName $name",script)
        self.assertIn("F139_V46_POSTCOMMIT_FORWARD_REPAIR_ONLY_HOLD",script)
        self.assertIn("F139_V46_SCIENTIFIC_FIRST_USE=FALSE",script)
        self.assertIn("F139_V46_SAME_ORIGINAL_TASK_ACTIVATED=PASS",script)
        self.assertNotIn("Register-ScheduledTask",script)
        self.assertNotIn("New-ScheduledTaskTrigger",script)
        self.assertNotIn("Start-Job",script)
        self.assertNotIn("Invoke-Expression",script)
        self.assertIn("$originalArgs.Split(@($originalRoot)",script)
        self.assertIn("source_sha -ceq $old",script)

    def test_windows_powershell_51_ast_parse_only(self):
        if os.name!="nt":
            self.skipTest("Original Windows PowerShell AST check")
        exe=shutil.which("powershell.exe")
        if not exe:
            self.fail("Original Windows PowerShell 5.1 not available")
        path=(Path(__file__).resolve().parents[1]/
              "f139/v46_original_owner_live_install.ps1")
        ps=r'''
$ErrorActionPreference='Stop'
$tokens=$null
$errors=$null
[System.Management.Automation.Language.Parser]::ParseFile(
  $env:F139_V46_PARSE_ONLY,[ref]$tokens,[ref]$errors)|Out-Null
if(@($errors).Count -ne 0){exit 31}
Write-Output 'F139_V46_AST_ONLY=PASS'
'''
        result=subprocess.run(
            [exe,"-NoProfile","-NonInteractive","-Command",ps],
            env={**os.environ,"F139_V46_PARSE_ONLY":str(path)},
            capture_output=True,timeout=30,check=False)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors="replace"))
        self.assertEqual(result.stdout.strip(),b"F139_V46_AST_ONLY=PASS")

    def test_no_dangerous_python_controller_writes(self):
        source=inspect.getsource(live)
        self.assertNotIn("gh api --method PATCH",source)
        self.assertNotIn("Stop-ScheduledTask",source)
        self.assertNotIn("Start-ScheduledTask",source)
        self.assertNotIn("Register-ScheduledTask",source)
        self.assertIn('with writer.transaction():',source)
        self.assertIn('writer.event("SOURCE_TRANSITION_ADMITTED", proof)',source)
        self.assertIn("v44_proof",source)
        self.assertIn("sealed_original(path)",source)
        self.assertNotIn("restore",inspect.getsource(live.commit_original).lower().replace("sealed_original",""))


    def test_existing_g54_one_shot_job_and_no_new_scheduler(self):
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/f139-g54-v9-owner-cutover.yml").read_text(
                      encoding="utf-8")
        marker="\n  v46-original-owner-live-install:\n"
        self.assertEqual(workflow.count(marker),1)
        job=workflow.split(marker,1)[1]
        self.assertIn("F139-V46-LIVE-INSTALL ",job)
        self.assertIn("github.actor == 'spoonman136668-ai'",job)
        self.assertIn("github.event.issue.number == 807",job)
        self.assertIn("runs-on: [self-hosted, Windows, forge-codex-isolated]",job)
        self.assertIn("f139/v46_original_owner_live_install.ps1",job)
        self.assertNotIn("schedule:",job)
        self.assertNotIn("Register-ScheduledTask",job)
        self.assertNotIn("workflow_dispatch:",job)


if __name__ == "__main__":
    unittest.main()

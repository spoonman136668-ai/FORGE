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
from unittest.mock import patch, MagicMock

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
            p+"branches/"+live.pin.release_worker_branch(live.TARGET):
                dict(name=live.pin.release_worker_branch(live.TARGET),
                     protected=True,commit={"sha":live.TARGET}),
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

    def fake_recovery(self):
        env,event,data,get=self.fake()
        base="repos/"+v42.REPO+"/"
        prior_own=event["comment"]
        data.pop(base+"issues/comments/"+str(prior_own["id"]))
        timestamp="2026-11-16T21:50:00Z"
        new_id=live.FAILED_RELEASE_COMMENT+5000
        event["comment"]=dict(
            id=new_id,
            body=live.RECOVERY_PREFIX+env["GITHUB_SHA"]+" "+
                 live.TARGET+" "+str(live.FAILED_RELEASE_COMMENT)+
                 " "+str(live.FAILED_RELEASE_RUN),
            created_at=timestamp, updated_at=timestamp,
            user={"login":v42.OWNER},author_association="OWNER")
        data[base+"issues/comments/"+str(new_id)]=dict(
            **event["comment"],
            issue_url="https://api.github.com/repos/"+v42.REPO+"/issues/807")
        data[base+"issues/comments/"+str(live.FAILED_RELEASE_COMMENT)] = dict(
            id=live.FAILED_RELEASE_COMMENT,
            body=live.PREFIX+live.FAILED_RELEASE_MAIN+" "+
                 live.TARGET+" "+str(v45.V44_COMMENT),
            created_at="2026-11-16T21:21:31Z",
            user={"login":v42.OWNER},author_association="OWNER",
            issue_url="https://api.github.com/repos/"+v42.REPO+"/issues/807")
        data[base+"actions/runs/"+str(live.FAILED_RELEASE_RUN)]=dict(
            id=live.FAILED_RELEASE_RUN,
            event="issue_comment",name=live.RECOVERY_WORKFLOW,
            head_sha=live.FAILED_RELEASE_MAIN,
            run_attempt=1,status="completed",conclusion="failure",
            actor={"login":v42.OWNER})
        data[base+"actions/runs/"+str(live.FAILED_RELEASE_RUN)+
             "/jobs?per_page=100"]=dict(
                 total_count=2,
                 jobs=[dict(id=live.FAILED_RELEASE_JOB,
                            name=live.RECOVERY_JOB,
                            status="completed",conclusion="failure"),
                       dict(id=9,name="other-job",
                            status="completed",conclusion="skipped")])
        return env,event,data,get

    def invoke_recovery(self,env,event,get):
        with patch.object(live.sys,"platform","win32"), \
             patch.object(live.os,"name","nt"), \
             patch.object(v45,"qualify",return_value={
                 "v44_original_job_status":"success"}), \
             patch.object(v42,"release_source",return_value={
                 "main_qualification_job_count":8,
                 "main_qualification_run_id":43958718732}):
            return live.request(get,env,event,recovery_mode=True)

    def test_distinct_recovery_accepts_only_authenticated_prior_failure(self):
        env,event,data,get=self.fake_recovery()
        proof=self.invoke_recovery(env,event,get)
        self.assertEqual(proof["comment_id"],event["comment"]["id"])
        self.assertEqual(proof["workflow_sha"],env["GITHUB_SHA"])
        # A recovery comment cannot be interpreted as a new ref-create event.
        with self.assertRaises(live.OriginalV46Denied):
            self.invoke(env,event,get)
        with patch.object(live.sys,"platform","win32"), \
             patch.object(live.os,"name","nt"):
            with self.assertRaises(live.OriginalV46Denied):
                live.request(get,env,event,require_worker_ref=False,
                             recovery_mode=True)

    def test_recovery_fails_closed_on_prior_run_and_ref_anomalies(self):
        base="repos/"+v42.REPO+"/"
        variants=[
            ("run","conclusion","success"),
            ("run","run_attempt",2),
            ("run","head_sha","0"*40),
            ("run","actor",{"login":"unrelated"}),
            ("jobs","total_count",30),
            ("job","conclusion","success"),
            ("job","id",-1),
            ("prior","author_association","CONTRIBUTOR"),
            ("prior","body","tampered"),
            ("worker","protected",False),
            ("worker","commit",{"sha":"0"*40}),
        ]
        for table,key,value in variants:
            with self.subTest(table=table,key=key):
                env,event,data,get=self.fake_recovery()
                selected={
                    "run":data[base+"actions/runs/"+
                               str(live.FAILED_RELEASE_RUN)],
                    "jobs":data[base+"actions/runs/"+
                                str(live.FAILED_RELEASE_RUN)+
                                "/jobs?per_page=100"],
                    "job":data[base+"actions/runs/"+
                               str(live.FAILED_RELEASE_RUN)+
                               "/jobs?per_page=100"]["jobs"][0],
                    "prior":data[base+"issues/comments/"+
                                 str(live.FAILED_RELEASE_COMMENT)],
                    "worker":data[base+"branches/"+
                                  live.pin.release_worker_branch(live.TARGET)],
                }[table]
                selected[key]=value
                with self.assertRaises(live.OriginalV46Denied):
                    self.invoke_recovery(env,event,get)

    def test_recovery_does_not_post_or_gain_content_write_token(self):
        script=(Path(__file__).resolve().parents[1]/
                "f139/v46_original_owner_live_install.ps1").read_text(
                    encoding="utf-8")
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/f139-g54-v9-owner-cutover.yml").read_text(
                      encoding="utf-8")
        self.assertEqual(script.count("Invoke-WebRequest -Method Post"),1)
        self.assertIn("if($ExistingRefRecovery)",script)
        self.assertIn("PREEXISTING_WORKER_REF_NOT_FOUND_HOLD",script)
        self.assertIn("F139_V47_EXISTING_IMMUTABLE_WORKER_REF=PASS",script)
        self.assertIn("NATIVE_ADMIN_OWNER_IDENTITY_REQUIRED",script)
        self.assertIn("ADMIN_BYPASS_ACTORS_FIELD_REQUIRED",script)
        self.assertIn("Remove-Item Env:GH_TOKEN",script)
        self.assertIn("$env:GH_TOKEN=$workflowToken",script)
        self.assertIn("F139_V47_EXISTING_REF_RECOVERY",script)
        self.assertEqual(workflow.count(
            "  v47-original-owner-existing-ref-recovery:"),1)
        recovery=workflow.split(
            "  v47-original-owner-existing-ref-recovery:",1)[1]
        self.assertIn("contents: read",recovery)
        self.assertNotIn("contents: write",recovery)
        self.assertIn("F139-V47-OWNER-RESUME ",recovery)
        self.assertIn("-ExistingRefRecovery",recovery)
        self.assertNotIn("workflow_dispatch:",recovery)
        self.assertNotIn("schedule:",recovery)

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

    def test_ref_provision_readonly_exemption_is_never_commit_authority(self):
        env,event,data,get=self.fake()
        route=("repos/"+v42.REPO+"/branches/"+
               live.pin.release_worker_branch(live.TARGET))
        del data[route]
        with patch.object(live.sys,"platform","win32"), \
             patch.object(live.os,"name","nt"), \
             patch.object(v45,"qualify",return_value={
                 "v44_original_job_status":"success"}), \
             patch.object(v42,"release_source",return_value={
                 "main_qualification_job_count":8,
                 "main_qualification_run_id":43931735723}):
            with self.assertRaises(AssertionError):
                live.request(get,env,event)
            p=live.request(get,env,event,require_worker_ref=False)
            self.assertEqual(p["workflow_sha"],env["GITHUB_SHA"])
            self.assertEqual(p["comment_id"],event["comment"]["id"])
            with self.assertRaises(live.OriginalV46Denied):
                live.request(get,env,event,require_worker_ref=None)
        # The only exemption is the explicit provision-preflight CLI path.
        source=inspect.getsource(live)
        self.assertIn("if args.ref_provision_preflight:",source)
        self.assertIn("require_worker_ref=False",source)
        self.assertIn("if require_worker_ref:",source)
        self.assertNotIn("require_worker_ref=False",inspect.getsource(live.commit_original))

    def test_scoped_one_shot_ref_post_is_pre_task_and_not_a_new_controller(self):
        script=(Path(__file__).resolve().parents[1]/
                "f139/v46_original_owner_live_install.ps1").read_text(
                    encoding="utf-8")
        self.assertEqual(script.count("Invoke-WebRequest -Method Post"),1)
        self.assertIn("ref-provision-preflight",script)
        self.assertIn("F139_V46_SCOPED_TOKEN_IMMUTABLE_WORKER_REF=PASS",script)
        self.assertIn("EXACT_WORKER_REF_ALREADY_PRESENT_OR_PROBE_FAILED",script)
        self.assertIn("WORKER_REF_RULESET_NOT_IMMUTABLE_HOLD",script)
        self.assertIn("STRICT_POST_REF_PREFLIGHT_UNQUALIFIED",script)
        self.assertLess(script.index("Invoke-WebRequest -Method Post"),
                        script.index("Disable-ScheduledTask -TaskName $name"))
        self.assertLess(script.index("STRICT_POST_REF_PREFLIGHT_UNQUALIFIED"),
                        script.index("Disable-ScheduledTask -TaskName $name"))
        self.assertNotIn("Register-ScheduledTask",script)
        self.assertNotIn("Set-GitHub",script)
        self.assertNotIn("workflow_dispatch",script)

    def test_v46_only_g54_workflow_gets_ref_write_permission(self):
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/f139-g54-v9-owner-cutover.yml").read_text(
                      encoding="utf-8")
        head, release=workflow.split("  v46-original-owner-live-install:",1)
        self.assertEqual(head.count("contents: write"),0)
        self.assertEqual(release.count("contents: write"),1)
        self.assertIn("contents: write # V46 only:",release)
        self.assertIn("GH_TOKEN: ${{ github.token }}",release)
        self.assertIn("github.event.issue.number == 807",release)
        self.assertIn("github.actor == 'spoonman136668-ai'",release)
        self.assertNotIn("schedule:",release)
        self.assertNotIn("workflow_dispatch:",release)

    def test_protected_exact_source_worker_ref_is_mandatory(self):
        route = "repos/"+v42.REPO+"/branches/"+live.pin.release_worker_branch(live.TARGET)
        for bad in (
                {"name":"unrelated","protected":True,"commit":{"sha":live.TARGET}},
                {"name":live.pin.release_worker_branch(live.TARGET),
                 "protected":False,"commit":{"sha":live.TARGET}},
                {"name":live.pin.release_worker_branch(live.TARGET),
                 "protected":True,"commit":{"sha":"b"*40}},
                {},
        ):
            with self.subTest(bad=bad):
                env,event,data,get=self.fake()
                data[route]=bad
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

    def test_poststart_live_event1836_anchor_accepts_natural_later_ticks(self):
        # Simulate a verified current head AFTER startup. No real owner touched.
        dbpath = Path("/fake-original.sqlite")
        expected = "a" * 64
        original = MagicMock()
        original.meta.return_value = {
            "source_sha": live.TARGET,
            "enabled": 1, "legacy_suspended": 1,
            "head_seq": 1837, "head_hash": "b"*64,
        }
        original.conn.total_changes = 0
        original.conn.execute.return_value.fetchone.return_value = {
            "kind": "SOURCE_TRANSITION_ADMITTED",
            "prior_sha": live.successor.PREDECESSOR_SHA,
            "sha": expected, "payload": "{}",
        }
        with patch.object(live.sys,"platform","win32"), \
             patch.object(live.os,"name","nt"), \
             patch.object(live,"canonical_db",return_value=dbpath), \
             patch.object(live.Database,"open_readonly",return_value=original):
            self.assertTrue(live.verify_poststart_event1836(
                dbpath, {"LOCALAPPDATA": "C:/irrelevant"}, expected))
            original.verify.assert_called_once()
            original.close.assert_called_once()

    def test_poststart_live_event1836_anchor_rejects_drift(self):
        dbpath = Path("/fake-original.sqlite")
        expected = "a" * 64
        cases = [
            ("wrong_source", {"source_sha": "f"*40}, {}),
            ("not_enabled", {"enabled": 0}, {}),
            ("head_rewound", {"head_seq":1835}, {}),
            ("wrong_kind", {}, {"kind":"NATIVE_TICK"}),
            ("wrong_predecessor", {}, {"prior_sha": "b"*64}),
            ("wrong_sha", {}, {"sha":"c"*64}),
            ("changes", {}, {"_total_changes":1}),
            ("missing", {}, {"_missing":True}),
        ]
        for name,meta_changes,row_changes in cases:
            with self.subTest(name=name):
                original=MagicMock()
                meta={"source_sha":live.TARGET,"enabled":1,
                      "legacy_suspended":1,"head_seq":1837,
                      "head_hash":"d"*64}
                meta.update(meta_changes)
                original.meta.return_value=meta
                row={"kind":"SOURCE_TRANSITION_ADMITTED",
                     "prior_sha":live.successor.PREDECESSOR_SHA,
                     "sha":expected,"payload":"{}"}
                row.update({k:v for k,v in row_changes.items()
                            if not k.startswith("_")})
                original.conn.total_changes=row_changes.get("_total_changes",0)
                original.conn.execute.return_value.fetchone.return_value=(
                    None if row_changes.get("_missing") else row)
                with patch.object(live.sys,"platform","win32"), \
                     patch.object(live.os,"name","nt"), \
                     patch.object(live,"canonical_db",return_value=dbpath), \
                     patch.object(live.Database,"open_readonly",return_value=original):
                    with self.assertRaises(live.OriginalV46Denied):
                        live.verify_poststart_event1836(
                            dbpath, {"LOCALAPPDATA": "C:/irrelevant"}, expected)

    def test_existing_binary_has_exact_source_rebuild_guard(self):
        script=(Path(__file__).resolve().parents[1]/
                "f139/v46_original_owner_live_install.ps1").read_text(
                    encoding="utf-8")
        self.assertIn("$existingBinNeedsSourceProof=", script)
        self.assertIn("go build -trimpath -o $proofBin",script)
        self.assertIn("EXISTING_BINARY_NOT_SOURCE_BOUND",script)
        self.assertIn("GOPROXY='off'",script)
        self.assertIn("GOTOOLCHAIN='local'",script)
        self.assertIn("F139_V46_LIVE_EVENT1836_ANCHOR=PASS",script)
        self.assertNotIn(
            "(Ledger $Target 1836) -ceq $posthead) 'LIVE_OWNER_PROCESS_OR_LEDGER_NOT_VERIFIED'",
            script)

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

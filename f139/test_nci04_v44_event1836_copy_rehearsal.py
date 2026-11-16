"""V44 original-owner copy-only event1836 qualification/negative controls."""
from __future__ import annotations
import copy
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from f139 import nci04_v44_event1836_copy_rehearsal as copy_only
from f139 import nci04_v44_owner_copy_cli as owner
from f139 import nci04_v42_owner_source_readiness as v42


class V44CopyTests(unittest.TestCase):
    def fake_event(self):
        target="f" * 40
        cid=owner.PREDECESSOR_COMMENT_ID+100
        env={
            "GITHUB_REPOSITORY":v42.REPO,
            "GITHUB_ACTOR":v42.OWNER,
            "GITHUB_EVENT_NAME":"issue_comment",
            "GITHUB_REF":"refs/heads/main",
            "RUNNER_NAME":"FORGE-CODEX-REMOTE",
            "GITHUB_RUN_ATTEMPT":"1",
            "GITHUB_RUN_ID":"43899999999",
            "GITHUB_SHA":target,
        }
        body=(owner.PREFIX+target+" "+copy_only.RELEASE_SOURCE+
              " "+str(owner.PREDECESSOR_COMMENT_ID))
        now="2026-11-16T13:00:00Z"
        event={
            "action":"created",
            "issue":{"number":807,"user":{"login":v42.OWNER}},
            "sender":{"login":v42.OWNER},
            "comment":{"id":cid,"user":{"login":v42.OWNER},
                       "author_association":"OWNER",
                       "body":body,"created_at":now,"updated_at":now},
        }
        remote={
            **event["comment"],
            "issue_url":"https://api.github.com/repos/"+
                v42.REPO+"/issues/807"}
        previous={
            "id":owner.PREDECESSOR_COMMENT_ID,
            "body":"F139-V43-COLD-BACKUP "+
                copy_only.RELEASE_SOURCE+" 6913813568",
            "user":{"login":v42.OWNER},
            "author_association":"OWNER",
            "created_at":"2026-11-16T12:28:02Z",
        }
        run={
            "id":copy_only.BACKUP_RUN,
            "head_sha":copy_only.RELEASE_SOURCE,
            "event":"issue_comment",
            "name":"FORGE G54 guarded V9 original-owner cutover",
            "run_attempt":1,
            "status":"completed","conclusion":"success",
            "actor":{"login":v42.OWNER},
        }
        job={
            "id":133297431631,"name":"v43-original-owner-cold-backup",
            "run_id":copy_only.BACKUP_RUN,
            "status":"completed","conclusion":"success",
        }
        jobs={"jobs":[job],"total_count":1}
        base="repos/"+v42.REPO+"/"
        def get(route):
            if route==base+"issues/comments/"+str(cid):
                return copy.deepcopy(remote)
            if route==base+"issues/comments/"+str(owner.PREDECESSOR_COMMENT_ID):
                return copy.deepcopy(previous)
            if route==base+"actions/runs/"+str(copy_only.BACKUP_RUN):
                return copy.deepcopy(run)
            if route==base+"actions/runs/"+str(copy_only.BACKUP_RUN)+"/jobs?per_page=100":
                return copy.deepcopy(jobs)
            raise AssertionError("unexpected GitHub route:"+route)
        return env,event,get,remote,previous,run,jobs

    def test_qualified_backup_provenance_binding(self):
        self.assertEqual(copy_only.BACKUP_RUN,43866834289)
        self.assertEqual(
            copy_only.BACKUP_MANIFEST,
            "d856b21d92772ab0bb9213988447517ac2463c5f6c25e2fdfd06c8e5dd7ed8b8")
        self.assertEqual(
            copy_only.BACKUP_TABLES,
            "5f14fb40039e660f10fe5f49fabcc2c5f4e2875bc1dc287edd415f51a9611812")
        env,event,get,_,_,_,_=self.fake_event()
        with patch.object(v42,"release_source",return_value={"source":"qualified"}):
            result=owner.intent(get,env,event)
        self.assertEqual(result[0],env["GITHUB_SHA"])
        self.assertEqual(result[1],int(env["GITHUB_RUN_ID"]))
        self.assertEqual(result[2],event["comment"]["id"])
        self.assertEqual(result[3],{"source":"qualified"})

    def test_issue_identity_and_prior_real_backup_reject_forgery(self):
        kinds=[
            ("env","GITHUB_ACTOR","other"),
            ("env","RUNNER_NAME","other"),
            ("env","GITHUB_REF","refs/heads/bad"),
            ("env","GITHUB_RUN_ATTEMPT","2"),
            ("env","OPENAI_API_KEY","paid"),
            ("event","action","edited"),
            ("issue","number",1715),
            ("issue","pull_request",{}),
            ("comment","author_association","CONTRIBUTOR"),
            ("comment","id",owner.PREDECESSOR_COMMENT_ID),
            ("comment","body","F139-V44-COPY-REHEARSAL bad"),
            ("comment","user",{"login":"other"}),
        ]
        for kind,key,val in kinds:
            with self.subTest(kind=kind,key=key):
                env,event,get,_,_,_,_=self.fake_event()
                if kind=="env":
                    env[key]=val
                elif kind=="event":
                    event[key]=val
                else:
                    event[kind][key]=val
                with patch.object(v42,"release_source",return_value={}):
                    with self.assertRaises(owner.OwnerCopyDenied):
                        owner.intent(get,env,event)
        env,event,get,remote,previous,run,jobs=self.fake_event()
        prior=previous.copy()
        prior["body"]="wrong"
        base="repos/"+v42.REPO+"/"
        def spoof(route):
            if route==base+"issues/comments/"+str(owner.PREDECESSOR_COMMENT_ID):
                return prior
            return get(route)
        with patch.object(v42,"release_source",return_value={}):
            with self.assertRaisesRegex(
                    owner.OwnerCopyDenied,"PRIOR_REAL_BACKUP"):
                owner.intent(spoof,env,event)

    def test_failed_backup_run_cannot_authorize_rehearsal(self):
        env,event,get,remote,previous,run,jobs=self.fake_event()
        run["conclusion"]="failure"
        base="repos/"+v42.REPO+"/"
        def failed(route):
            if route==base+"actions/runs/"+str(copy_only.BACKUP_RUN):
                return run
            return get(route)
        with patch.object(v42,"release_source",return_value={}):
            with self.assertRaisesRegex(
                    owner.OwnerCopyDenied,"BACKUP_RUN_REQUIRED"):
                owner.intent(failed,env,event)

    def test_no_unsafe_original_or_partial_retry(self):
        with self.assertRaises(copy_only.CopyOnlyDenied):
            copy_only.rehearse(
                object(),owner_comment_id=owner.PREDECESSOR_COMMENT_ID+1,
                run_id=43899999999,
                copy_path=Path("relative/rehearsal.sqlite"),
                original_witness=lambda:True,
                release_witness=lambda:True)
        self.assertFalse(hasattr(copy_only,"commit_original"))
        self.assertFalse(hasattr(copy_only,"activate"))
        self.assertFalse(hasattr(copy_only,"write_policy"))
        self.assertFalse(hasattr(owner,"install"))
        body=inspect.getsource(copy_only.rehearse)
        self.assertIn("with copied.transaction():",body)
        self.assertIn("if inject_failure == \"after_source_event\":",body)
        self.assertIn("db",body)
        self.assertNotIn("original.conn.execute(\"UPDATE",body)
        self.assertNotIn("original.event(",body)
        self.assertNotIn("original.transaction(",body)

    def test_existing_one_shot_job_no_task_mutation(self):
        root=Path(__file__).resolve().parents[1]
        workflow=(root/".github/workflows/f139-g54-v9-owner-cutover.yml").read_text()
        marker="\n  v44-original-owner-copy-rehearsal:\n"
        self.assertEqual(workflow.count(marker),1)
        source=workflow.split(marker,1)[1]
        self.assertIn("f139.nci04_v44_owner_copy_cli",source)
        self.assertIn("F139-V44-COPY-REHEARSAL ",source)
        self.assertIn("github.event_name == 'issue_comment'",source)
        self.assertIn("RUNNER_NAME -ceq 'FORGE-CODEX-REMOTE'",source)
        self.assertIn("GITHUB_RUN_ATTEMPT -ceq '1'",source)
        self.assertNotIn("schedule:",source)
        for bad in (
            "Stop-ScheduledTask","Start-ScheduledTask",
            "Register-ScheduledTask","Disable-ScheduledTask",
            "Set-ScheduledTask","Stop-Process",
            "gh api --method","Invoke-Expression"):
            self.assertNotIn(bad,source)


if __name__=="__main__":
    unittest.main()

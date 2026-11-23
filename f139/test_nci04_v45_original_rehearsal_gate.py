"""V45 GET-only prior-rehearsal provenance and fail-closed controls."""
from __future__ import annotations

import copy
import inspect
import unittest
from unittest.mock import patch

from f139 import nci04_v45_original_rehearsal_gate as gate
from f139 import nci04_v42_owner_source_readiness as readiness
from f139 import nci04_v44_event1836_copy_rehearsal as v44


class OriginalRehearsalGateTests(unittest.TestCase):
    def fixture(self):
        main = "f" * 40
        p = "repos/" + readiness.REPO + "/"
        comment_body = ("F139-V44-COPY-REHEARSAL " + gate.V44_MAIN + " " +
                        v44.RELEASE_SOURCE + " 6916414055")
        def run(run_id, sha):
            return dict(id=run_id, name=gate.V44_WORKFLOW,
                        head_sha=sha, event="issue_comment",
                        status="completed", conclusion="success",
                        run_attempt=1, actor={"login":readiness.OWNER})
        def job(run_id, job_id, name):
            return dict(id=job_id, name=name, run_id=run_id,
                        status="completed", conclusion="success",
                        runner_name="FORGE-CODEX-REMOTE")
        data = {
            p + "branches/main": dict(name="main", protected=True,
                                      commit={"sha":main}),
            p + "compare/" + gate.V44_MAIN + "..." + main +
                "?per_page=1&page=2": dict(status="ahead", behind_by=0,
                          merge_base_commit={"sha":gate.V44_MAIN}),
            p + "issues/comments/" + str(gate.V44_COMMENT): dict(
                id=gate.V44_COMMENT, body=comment_body,
                user={"login":readiness.OWNER},
                author_association="OWNER",
                issue_url="https://api.github.com/repos/" +
                    readiness.REPO + "/issues/807"),
            p + "actions/runs/" + str(gate.V44_RUN): run(
                gate.V44_RUN,gate.V44_MAIN),
            p + "actions/runs/" + str(gate.V44_RUN) +
                "/jobs?per_page=100": dict(total_count=1,jobs=[
                    job(gate.V44_RUN,gate.V44_JOB,gate.V44_JOB_NAME)]),
            p + "actions/runs/" + str(v44.BACKUP_RUN): run(
                v44.BACKUP_RUN,v44.RELEASE_SOURCE),
            p + "actions/runs/" + str(v44.BACKUP_RUN) +
                "/jobs?per_page=100": dict(total_count=1,jobs=[
                    job(v44.BACKUP_RUN,gate.V43_JOB,gate.V43_JOB_NAME)]),
        }
        return main, data

    def run_gate(self,data,main):
        def get(route):
            if route not in data:
                raise AssertionError("unexpected route: "+route)
            return copy.deepcopy(data[route])
        with patch.object(readiness,"_policy",return_value=True) as policy:
            result=gate.qualify(get,main_sha=main)
            self.assertEqual(policy.call_count,2)
        return result

    def test_success_is_remote_only_and_non_authorizing(self):
        main,data=self.fixture()
        result=self.run_gate(data,main)
        self.assertEqual(result["v44_original_job_status"],"success")
        self.assertEqual(result["v43_backup_job_status"],"success")
        self.assertEqual(result["target_source_sha"],v44.RELEASE_SOURCE)
        self.assertFalse(result["live_source_transition_authorized"])
        self.assertFalse(result["original_database_freshly_read"])
        self.assertFalse(result["v44_receipt_log_independently_parsed"])
        self.assertEqual(result["original_sqlite_mutations"],0)
        self.assertEqual(result["new_dispatches"],0)
        self.assertNotIn("Stop-ScheduledTask",inspect.getsource(gate))
        self.assertNotIn("Start-ScheduledTask",inspect.getsource(gate))
        self.assertFalse(hasattr(gate,"commit"))
        self.assertFalse(hasattr(gate,"install"))

    def test_forged_execution_metadata_fails_closed(self):
        mutations=[
            ("v44run","conclusion","failure"),
            ("v44run","run_attempt",2),
            ("v44run","head_sha","0"*40),
            ("v44run","event","workflow_dispatch"),
            ("v43run","head_sha","1"*40),
            ("v43run","conclusion","cancelled"),
            ("v44job","runner_name","other-runner"),
            ("v44job","conclusion","failure"),
            ("v43job","id",0),
            ("v43job","runner_name","other-runner"),
            ("comment","body","forged"),
            ("comment","author_association","CONTRIBUTOR"),
            ("main","protected",False),
            ("compare","behind_by",1),
        ]
        for which,key,value in mutations:
            with self.subTest(which=which,key=key):
                main,data=self.fixture()
                p="repos/"+readiness.REPO+"/"
                target={
                    "v44run":data[p+"actions/runs/"+str(gate.V44_RUN)],
                    "v43run":data[p+"actions/runs/"+str(v44.BACKUP_RUN)],
                    "v44job":data[p+"actions/runs/"+str(gate.V44_RUN)+
                                   "/jobs?per_page=100"]["jobs"][0],
                    "v43job":data[p+"actions/runs/"+str(v44.BACKUP_RUN)+
                                   "/jobs?per_page=100"]["jobs"][0],
                    "comment":data[p+"issues/comments/"+str(gate.V44_COMMENT)],
                    "main":data[p+"branches/main"],
                    "compare":data[p+"compare/"+gate.V44_MAIN+"..."+main+
                                   "?per_page=1&page=2"],
                }[which]
                target[key]=value
                with self.assertRaises(gate.V45ReadinessDenied):
                    self.run_gate(data,main)

    def test_incomplete_and_duplicate_jobs_fail_closed(self):
        main,data=self.fixture()
        p="repos/"+readiness.REPO+"/actions/runs/"+str(gate.V44_RUN)+"/jobs?per_page=100"
        data[p]["total_count"]=2
        with self.assertRaisesRegex(gate.V45ReadinessDenied,"COMPLETE_JOBS"):
            self.run_gate(data,main)
        main,data=self.fixture()
        job=copy.deepcopy(data[p]["jobs"][0])
        data[p]["jobs"].append(job)
        data[p]["total_count"]=2
        with self.assertRaisesRegex(gate.V45ReadinessDenied,"EXACT_SUCCESSFUL"):
            self.run_gate(data,main)

    def test_wrong_main_and_denied_policy_fail_closed(self):
        main,data=self.fixture()
        with self.assertRaises(gate.V45ReadinessDenied):
            self.run_gate(data,"x"*40)
        def get(route):
            return copy.deepcopy(data[route])
        with patch.object(readiness,"_policy",side_effect=readiness.SourceReadinessDenied("POLICY_DRIFT")):
            with self.assertRaises(readiness.SourceReadinessDenied):
                gate.qualify(get,main_sha=main)


if __name__ == "__main__":
    unittest.main()

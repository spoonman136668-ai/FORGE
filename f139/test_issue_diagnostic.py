"""D2K source-bound Go diagnostic qualification with synthetic process outputs."""
import hashlib
import os
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from f139.issue_diagnostic import diagnose, bounded_run, MAX_OUTPUT, TIMEOUT_SEC
from f139.verify_ticket import signature, Untrusted, REPO

SOURCE = "e1b16d0a4097e9fd3d61c9ee635486a72395cf4b"
KEY = "f139-test-hmac-secret-never-deploy-00000000000000000000"
BODY = "a" * 64


def authorized():
    ticket="f139-d2k-i1401-"+SOURCE[:12]+"-"+BODY[:8]
    data={
        "key":KEY,"ticket":ticket,"lane":"Qualification","source_sha":SOURCE,
        "epoch":"1","repository":REPO,"ref":"refs/heads/main",
        "event":"workflow_dispatch","head_sha":SOURCE,"run_attempt":"1",
        "run_id":"12345","os":"windows-latest","issue_number":"1401",
        "issue_id":"91401","body_sha256":BODY,"target_package":"./planner",
    }
    data["signature"]=signature(
        KEY,ticket,"Qualification",SOURCE,"1",issue_number="1401",
        issue_id="91401",body_sha256=BODY,target_package="./planner")
    return data


class D2KPackageDiagnosticTests(unittest.TestCase):
    def test_exact_go_command_and_clean_child_environment(self):
        calls=[]
        def runner(command, **kwargs):
            calls.append((command,kwargs))
            return SimpleNamespace(returncode=0,stdout=b"ok\n")
        with mock.patch.dict(os.environ, {
            "GH_TOKEN":"test-secret","GITHUB_TOKEN":"test-secret",
            "F139_WORKER_HMAC_KEY":"test-secret"}):
            result=diagnose(authorized(),command_runner=runner,clock=lambda:5)
        self.assertEqual(result["outcome"],"PASS")
        self.assertEqual(result["returncode"],0)
        self.assertEqual(result["issue_number"],1401)
        self.assertEqual(result["body_sha256"],BODY)
        self.assertEqual(result["output_sha256"],hashlib.sha256(b"ok\n").hexdigest())
        command,options=calls[0]
        self.assertEqual(command,["go","test","-count=1","-timeout=90s","./planner"])
        self.assertEqual(options["stdin"],subprocess.DEVNULL)
        self.assertEqual(options["timeout"],TIMEOUT_SEC)
        for key in ("GH_TOKEN","GITHUB_TOKEN","F139_WORKER_HMAC_KEY"):
            self.assertNotIn(key,options["env"])

    def test_test_failure_preserved_not_promoted(self):
        report=diagnose(authorized(),command_runner=lambda *a,**k:
                        SimpleNamespace(returncode=1,stdout=b"failed"))
        self.assertEqual(report["outcome"],"TEST_FAILURE")
        self.assertEqual(report["returncode"],1)
        self.assertFalse(report["scientific_first_use"])
        self.assertEqual(report["paid_model_calls"],0)

    def test_timeout_preserved_not_replayed(self):
        def runner(*args,**kwargs):
            raise subprocess.TimeoutExpired(args[0],TIMEOUT_SEC,output=b"timeout")
        report=diagnose(authorized(),command_runner=runner)
        self.assertEqual(report["outcome"],"TIMEOUT")
        self.assertEqual(report["returncode"],-1)

    def test_real_subprocess_output_limit_kills_and_retains_negative(self):
        outcome = bounded_run(
            [sys.executable, "-c", "import sys; sys.stdout.write('X' * 400000); sys.stdout.flush()"],
            env=os.environ.copy(),timeout=10)
        self.assertEqual(outcome.returncode,125)
        self.assertLessEqual(len(outcome.stdout),MAX_OUTPUT)
        self.assertIn(b"F139_D2K_OUTPUT_LIMIT_EXCEEDED",outcome.stdout[:100])

    def test_real_subprocess_timeout_retains_bounded_prefix(self):
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            bounded_run(
                [sys.executable,"-c", "import sys,time; print('begin',flush=True);time.sleep(20)"],
                env=os.environ.copy(),timeout=0.5)
        self.assertIn(b"begin",caught.exception.output)
        self.assertLessEqual(len(caught.exception.output),MAX_OUTPUT)

    def test_wrong_signature_invalid_package_and_oversize_fail_closed(self):
        item=authorized();item["target_package"]="../private"
        with self.assertRaises(Untrusted):
            diagnose(item,command_runner=lambda *a,**k:None)
        item=authorized();item["signature"]="0"*64
        with self.assertRaises(Untrusted):
            diagnose(item,command_runner=lambda *a,**k:None)
        with self.assertRaisesRegex(Untrusted,"D2K_OUTPUT_TOO_LARGE"):
            diagnose(authorized(),command_runner=lambda *a,**k:
                     SimpleNamespace(returncode=0,stdout=b"x"*(MAX_OUTPUT+1)))
        with self.assertRaisesRegex(Untrusted,"D2K_EXIT_CODE_INVALID"):
            diagnose(authorized(),command_runner=lambda *a,**k:
                     SimpleNamespace(returncode=-9,stdout=b"unexpected signal"))

if __name__=="__main__":
    unittest.main()

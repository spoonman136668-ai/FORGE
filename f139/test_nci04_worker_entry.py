"""A6 safe native workflow bridge qualification (no real ticket dispatch)."""
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from f139.nci04_native_contract import canonical, digest, parse_intent
from f139.nci04_owner_issue import inspect_owner_issue, make_signed_dispatch_inputs
from f139.nci04_worker_entry import authorize, execute, NativeWorkerBlocked
from f139.nci04_signed_native import NativeAdmission
from f139.nci04_native_worker import COMMANDS
from test_nci04_owner_issue import candidate as make_candidate, issue as make_issue, MAIN, HMAC


def git(root, *args):
    p=subprocess.run(["git","-C",str(root),*args],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     check=True,timeout=15)
    return p.stdout.decode().strip()


class NativeExecutionBoundaryTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory(prefix="f139-a6-worker-")
        self.addCleanup(folder.cleanup)
        self.parent=Path(folder.name)
        self.source=self.parent/"native"
        self.source.mkdir()
        git(self.source,"init","-q")
        git(self.source,"config","user.name","nci04-test")
        git(self.source,"config","user.email","nci04@example.invalid")
        (self.source/"cognition").mkdir()
        (self.source/"cognition"/"base.go").write_text("package cognition\n")
        git(self.source,"add",".")
        git(self.source,"commit","-qm","original native source")
        sha=git(self.source,"rev-parse","HEAD")
        tree=git(self.source,"rev-parse","HEAD^{tree}")
        raw=make_issue()
        issue_doc=json.loads(raw["body"])
        source_candidate=make_candidate()
        source_candidate["target_commit"]=sha
        source_candidate["target_tree_sha"]=tree
        issue_doc["intent_base64"]=base64.b64encode(canonical(source_candidate)).decode()
        raw["body"]=json.dumps(issue_doc)
        native=inspect_owner_issue(
            raw,protected_main=MAIN,authenticated_target_commit=sha,
            authenticated_target_tree=tree)
        self.issue=native
        fields=make_signed_dispatch_inputs(native,owner_hmac_key=HMAC,epoch=1)
        self.fields=fields
        self.env={
            "F139_WORKER_HMAC_KEY":HMAC,
            "F139_TICKET":native.ticket,
            "F139_LANE":native.lane,
            "F139_SOURCE_SHA":MAIN,
            "F139_EPOCH":"1",
            "F139_SIGNATURE":fields["signature"],
            "F139_NATIVE_SIGNATURE":fields["native_signature"],
            "F139_INTENT_BASE64":base64.b64encode(native.intent_raw).decode(),
            "F139_ISSUE_NUMBER":str(native.number),
            "F139_ISSUE_ID":str(native.issue_id),
            "F139_BODY_SHA256":native.issue_body_sha256,
            "F139_QUALIFICATION_KEY":native.qualification_key,
            "F139_TARGET_COMMIT":sha,
            "F139_TARGET_TREE_SHA":tree,
            "F139_AUTHENTICATED_TARGET_TREE":tree,
            "GITHUB_REPOSITORY":"spoonman136668-ai/FORGE",
            "GITHUB_REF":"refs/heads/main",
            "GITHUB_EVENT_NAME":"workflow_dispatch",
            "GITHUB_SHA":MAIN,
            "GITHUB_RUN_ID":"39510000000",
            "GITHUB_RUN_ATTEMPT":"1",
            "F139_RUNNER_OS":"ubuntu-latest",
        }

    def test_authorize_with_real_original_plus_native_HMAC(self):
        with mock.patch.dict(os.environ,self.env,clear=True):
            result=authorize()
        self.assertEqual(result["schema"],"forge.f139.nci04.native-authorized-job.v1")
        self.assertRegex(result["authorization_sha256"],r"^[a-f0-9]{64}$")
        self.assertFalse(result["scientific_first_use"])

    def test_authorize_exact_worker_release_ref_not_unrelated_commit(self):
        release={**self.env,
                 "GITHUB_REF":"refs/heads/f139-owner-release-"+MAIN}
        with mock.patch.dict(os.environ,release,clear=True):
            self.assertEqual(authorize()["schema"],
                             "forge.f139.nci04.native-authorized-job.v1")
        forged={**release,"GITHUB_REF":"refs/heads/f139-owner-release-"+"0"*40}
        with mock.patch.dict(os.environ,forged,clear=True):
            with self.assertRaises(ValueError):
                authorize()

    def test_wrong_signatures_issue_or_provider_tree_denied(self):
        for key,value in (
            ("F139_WORKER_HMAC_KEY","evil"*12),
            ("F139_NATIVE_SIGNATURE","0"*64),
            ("F139_ISSUE_NUMBER","703"),
            ("F139_AUTHENTICATED_TARGET_TREE","9"*40),
            ("GITHUB_RUN_ATTEMPT","2")):
            with self.subTest(field=key),mock.patch.dict(
                os.environ,{**self.env,key:value},clear=True):
                with self.assertRaises(ValueError):
                    authorize()

    def test_real_isolated_source_patch_and_credential_free_fixed_inventory(self):
        with mock.patch.dict(os.environ,self.env,clear=True):
            auth=authorize()
        env={k:v for k,v in self.env.items() if k!="F139_WORKER_HMAC_KEY"}
        # Preserve only OS process-location variables for real Windows git.
        for key in ("PATH","SystemRoot","WINDIR","ComSpec","PATHEXT",
                    "TEMP","TMP","USERPROFILE","HOME"):
            if key in os.environ:
                env[key]=os.environ[key]
        env.update({
            "F139_NATIVE_AUTHORIZATION_SHA256":auth["authorization_sha256"],
            "F139_NATIVE_AUTHENTICATION_PASSED":"true",
        })
        scratch=self.parent/"staging"
        output=self.parent/"receipts"
        scratch.mkdir()
        output.mkdir()
        seen=[]
        def fixed_run(candidate,stage):
            seen.append(stage)
            self.assertFalse((self.source/"cognition"/"native_state.go").exists())
            self.assertTrue((stage/"checkout"/"cognition"/"native_state.go").exists())
            self.assertTrue((stage/"checkout"/"cognition"/"base.go").exists())
            calls=[{
                "command":list(cmd),"outcome":"PASS","returncode":0,
                "elapsed_ms":12,"output_sha256":digest(b"test passed\n"),
                "output_bytes":12,"excerpt":"test passed\n",
            } for cmd in COMMANDS["Wingless"]]
            c=candidate
            return {
                "schema":"forge.f139.nci04.native-development-diagnostic.v1",
                "intent_sha256":c.intent_sha256,
                "qualification_key":c.qualification_key,
                "target_commit":c.target_commit,
                "target_tree_sha":c.target_tree_sha,
                "candidate_file":c.path,
                "candidate_sha256":c.after_sha256,
                "lane":c.lane,"qualification_complete":True,
                "real_code_changed_in_isolated_copy":True,
                "commands":calls,
                "child_peak_rss_bytes":None,
                "scientific_first_use":False,
                "protected_holdouts_accessed":0,
                "accepted_ref_mutations":0,
                "paid_model_calls":0,
                "durable_controller_custody_verified":False,
                "unattended_controller_dispatch_verified":False,
            }
        with mock.patch.dict(os.environ,env,clear=True), mock.patch(
             "f139.nci04_worker_entry.verify_fixed_commands",side_effect=fixed_run):
            result,ok=execute(self.source,scratch,output)
        self.assertTrue(ok)
        self.assertTrue(result["native_qualified"])
        self.assertEqual(len(seen),1)
        self.assertTrue((output/"f139-receipt.json").is_file())
        self.assertTrue((output/"f139-native-report.json").is_file())
        self.assertEqual(git(self.source,"status","--porcelain"),"")

    def test_native_code_job_refuses_signing_secret_and_missing_auth(self):
        scratch=self.parent/"staging"
        output=self.parent/"receipts"
        scratch.mkdir()
        output.mkdir()
        env={**self.env,
             "F139_NATIVE_AUTHENTICATION_PASSED":"true",
             "F139_NATIVE_AUTHORIZATION_SHA256":"e"*64}
        with mock.patch.dict(os.environ,env,clear=True):
            with self.assertRaisesRegex(NativeWorkerBlocked,"WORKER_CREDENTIAL_INHERITANCE"):
                execute(self.source,scratch,output)
        env.pop("F139_WORKER_HMAC_KEY")
        env["F139_NATIVE_AUTHENTICATION_PASSED"]="false"
        with mock.patch.dict(os.environ,env,clear=True):
            with self.assertRaisesRegex(NativeWorkerBlocked,"NATIVE_AUTH_JOB_NOT_SUCCESS"):
                execute(self.source,scratch,output)

if __name__=="__main__":
    unittest.main()

"""R12-J: actual Ed25519 fixture proof and strict inactive owner trust."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from f139.local_controller import canonical
from f139.rsi_r12g_pre_dispatch import (
    prepare, event_payload, sign,
)
from f139.rsi_r12j_owner_signature import (
    DOMAIN, SCHEMA, SIGNED_SCHEMA, ROOT, ROOT_SCHEMA,
    OriginalSignerDenied, statement, validate_statement,
    verify_ed25519, verify_enrolled,
)
from f139.test_rsi_r12b_signed_job import (
    synthetic_binding, KEY, MAIN, TREE,
)

def fixture():
    binding, _ = synthetic_binding()
    intent = prepare(
        binding=binding, source_sha=MAIN,
        source_tree_sha=TREE, runner_os="windows-latest")
    preissue = event_payload(
        bundle=intent, signature=sign(KEY, intent),
        binding=binding, prior_head="f" * 64)
    row = {"seq": binding["reservation_seq"] + 1,
           "sha": "a" * 64, "prior_sha": "f" * 64}
    run_id = max(intent["failed_run_id"]+1, 42599999999)
    run = {
        "id":run_id, "event":"workflow_dispatch",
        "run_attempt":1, "head_sha":MAIN,
        "head_branch":"main", "name":"F139 "+intent["ticket"],
        "path":".github/workflows/forge-f139-development-worker.yml",
        "status":"in_progress", "conclusion":None,
        "actor":{"login":"spoonman136668-ai"},
        "repository":{"full_name":"spoonman136668-ai/FORGE"},
        "head_repository":{"full_name":"spoonman136668-ai/FORGE"},
    }
    job = {"id":129999999999, "run_id":run_id, "head_sha":MAIN,
           "name":"rsi-self-qualification (windows-latest)",
           "labels":["windows-latest"], "status":"queued",
           "conclusion":None}
    doc = statement(
        preissue=preissue, preissue_row=row, binding=binding,
        run=run, job=job, ledger_head="e"*64)
    return doc, preissue, row, binding, run, job


class OriginalPublicSignatureTests(unittest.TestCase):
    def setUp(self):
        self.doc, self.preissue, self.row, self.binding, self.run, self.job = fixture()

    def test_preexecution_identity_not_terminal_evidence(self):
        self.assertEqual(self.doc["schema"], SCHEMA)
        self.assertEqual(self.doc["run_id"], self.run["id"])
        self.assertEqual(self.doc["job_id"], self.job["id"])
        self.assertEqual(self.doc["ticket"], self.preissue["intent"]["ticket"])
        self.assertEqual(self.doc["run_attempt"], 1)
        validate_statement(self.doc)
        for key in ("original_ledger_independently_verified",
                    "credential_free_worker_admitted",
                    "scientific_first_use", "source_promoted",
                    "autonomous_rsi_proven"):
            self.assertFalse(self.doc[key])
        self.assertEqual(self.doc["one_signed_job"], 1)
        self.assertFalse(self.doc["retry_allowed"])

    def test_forged_provider_and_original_identity_rejected(self):
        for key, value in (
            ("id", 1), ("run_attempt", 2), ("head_sha","f"*40),
            ("head_branch","elsewhere"), ("event","push"),
            ("status","completed"), ("name","F139 forged"),
            ("actor",{"login":"attacker"}),
        ):
            with self.subTest(key=key):
                with self.assertRaises(Exception):
                    statement(
                        preissue=self.preissue, preissue_row=self.row,
                        binding=self.binding,
                        run={**self.run,key:value}, job=self.job,
                        ledger_head="e"*64)
        for key, value in (
            ("id", 0), ("run_id", 1), ("labels", ["ubuntu-latest"]),
            ("status", "completed"),
        ):
            with self.subTest(key=key):
                with self.assertRaises(Exception):
                    statement(
                        preissue=self.preissue, preissue_row=self.row,
                        binding=self.binding, run=self.run,
                        job={**self.job,key:value}, ledger_head="e"*64)

    def test_tampered_frozen_statement_fields_fail_closed(self):
        for key, value in (
            ("source_sha", "bad"), ("owner_source_sha","f"*39),
            ("source_tree_sha", "bad"), ("run_attempt",2),
            ("ticket","forge-self-unsigned"), ("run_id",0),
            ("job_id",0), ("one_signed_job",2),
            ("preissue_seq", 0), ("candidate_sha256", "bad"),
            ("original_ledger_head_sha256", "bad"),
            ("credential_free_worker_admitted",True),
            ("source_promoted",True), ("retry_allowed",True),
            ("original_ledger_independently_verified",True),
        ):
            with self.subTest(key=key):
                with self.assertRaises(OriginalSignerDenied):
                    validate_statement({**self.doc,key:value})

    def test_original_owner_key_not_enrolled_and_worker_unchanged(self):
        root = json.loads(ROOT.read_text("ascii"))
        self.assertEqual(root["schema"],ROOT_SCHEMA)
        self.assertIs(root["enabled"],False)
        self.assertIs(root["allow_worker_admission"],False)
        self.assertEqual(root["keys"],[])
        with self.assertRaisesRegex(
                OriginalSignerDenied,"KEY_NOT_ENROLLED"):
            verify_enrolled(signed_receipt={
                "schema":SIGNED_SCHEMA, "statement":self.doc,
                "key_id":"0"*64,
                "signature_base64":base64.b64encode(bytes(64)).decode("ascii"),
            })
        from f139.verify_ticket import LANES as WORKER
        from f139.local_controller import LANES as OWNER
        self.assertNotIn("FORGE-self",WORKER)
        self.assertNotIn("FORGE-self",OWNER)
        wf=(Path(__file__).resolve().parents[1] /
            ".github/workflows/forge-f139-development-worker.yml").read_text()
        self.assertNotIn("rsi-authorize:",wf)
        self.assertNotIn("rsi-execute:",wf)
        self.assertNotIn("schedule:",wf)

    def test_real_go_ed25519_sign_and_verify_no_enrollment(self):
        go = shutil.which("go")
        self.assertIsNotNone(go, "Ed25519 qualification needs installed Go")
        f=Path(__file__).with_name("testdata") / "rsi_r12j_ephemeral_signer.go"
        self.assertTrue(f.is_file())
        environment=dict(os.environ)
        environment.update({
            "GO111MODULE":"off","GOTOOLCHAIN":"local",
            "GOPROXY":"off","GOSUMDB":"off","GOWORK":"off",
        })
        body=DOMAIN+canonical(self.doc)
        r=subprocess.run(
            [go,"run",str(f)],input=body,check=False,
            capture_output=True,timeout=90,env=environment,cwd=f.parent)
        self.assertEqual(r.returncode,0,r.stderr[-1200:])
        obj=json.loads(r.stdout)
        self.assertTrue(verify_ed25519(
            statement_data=self.doc,
            signature_b64=obj["signature_b64"],
            public_key_b64=obj["public_key_b64"]))
        changed={**self.doc,"job_id":self.doc["job_id"]+1}
        with self.assertRaisesRegex(
                OriginalSignerDenied,"ED25519_SIGNATURE_INVALID"):
            verify_ed25519(
                statement_data=changed,
                signature_b64=obj["signature_b64"],
                public_key_b64=obj["public_key_b64"])
        tampered=bytearray(base64.b64decode(obj["signature_b64"]))
        tampered[-1]^=0x01
        with self.assertRaises(OriginalSignerDenied):
            verify_ed25519(
                statement_data=self.doc,
                signature_b64=base64.b64encode(tampered).decode("ascii"),
                public_key_b64=obj["public_key_b64"])
        # A real ephemeral key is not a registered original-owner identity.
        with self.assertRaisesRegex(
                OriginalSignerDenied,"KEY_NOT_ENROLLED"):
            verify_enrolled(signed_receipt={
                "schema":SIGNED_SCHEMA,"statement":self.doc,
                "key_id":hashlib.sha256(
                    base64.b64decode(obj["public_key_b64"])).hexdigest(),
                "signature_base64":obj["signature_b64"],
            })


if __name__=="__main__":
    unittest.main()

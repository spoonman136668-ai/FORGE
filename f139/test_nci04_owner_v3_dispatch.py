"""Real production owner-source V3 domain; V1/V2 cannot be substituted."""
import unittest
from f139.nci04_native_contract import Candidate
from f139.nci04_owner_issue import NativeIssue
from f139 import nci04_owner_v3_dispatch as v3
from f139 import nci04_g36_v2_dispatch as old


class VersionDistinctNativeOwnerTests(unittest.TestCase):
    def setUp(self):
        c=Candidate(
            "a"*64, "b"*64,
            "fc5d28a836f33caad3a576e0a6d4a1bf211cd857",
            "4cab523b03f7316b2470eddb93c479ec9e8cbab4",
            "yggdrasil/public_causal_cells.py",
            "d"*64,"e"*64,b"trusted-test-only","Yggdrasil")
        self.issue=NativeIssue(
            1200,120012345,"f139-nci04-i1200-0743ca22b76e-aaaaaaaa",
            "Yggdrasil","0743ca22b76ebd943a66f05a36ea919301676be0",
            "f"*64,c.intent_sha256,c.qualification_key,b"unit-test-only",c)
        self.key="owner-fixture-only-not-production-0123456789"
        self.seq=323
        self.claim=324

    def sign(self):
        return v3.signature(self.key,self.issue,9,self.seq,"1"*64,
                            self.claim,"2"*64)

    def test_v3_domain_binds_original_ledger_and_source(self):
        signed=self.sign()
        self.assertEqual(len(signed),64)
        proof=v3.verify_claim(self.key,self.issue,9,self.seq,"1"*64,
                              self.claim,"2"*64,signed)
        self.assertEqual(len(proof),64)
        self.assertEqual(v3._bound(self.issue,9,self.seq,"1"*64,
                                   self.claim,"2"*64)["protocol"],"v3")

    def test_old_v2_signing_cannot_be_used_for_new_source(self):
        with self.assertRaises(Exception):
            old.signature(self.key,self.issue,9,self.seq,"1"*64,
                          self.claim,"2"*64)
        with self.assertRaises(v3.G36Denied):
            v3.verify_claim(self.key,self.issue,9,self.seq,"1"*64,
                            self.claim,"2"*64,"0"*64)

    def test_failed_original_event_seq_is_never_replayed(self):
        for original,claim in [(317,322),(322,323),(323,323),(321,350)]:
            with self.subTest(original=original,claim=claim):
                with self.assertRaises(v3.G36Denied):
                    v3.signature(self.key,self.issue,9,original,"1"*64,claim,"2"*64)

    def test_cross_issue_and_epoch_forgery_denied(self):
        signed=self.sign()
        for epoch,event,claimed_hash in [(10,323,"2"*64),(9,324,"2"*64),
                                         (9,323,"3"*64)]:
            with self.subTest(epoch=epoch,event=event):
                with self.assertRaises(v3.G36Denied):
                    v3.verify_claim(self.key,self.issue,epoch,event,"1"*64,
                                    325,claimed_hash,signed)

    def test_current_dev_only_bound_scope(self):
        signed=self.sign()
        other=self.issue.candidate
        from dataclasses import replace
        modified=replace(self.issue,candidate=replace(other,path="yggdrasil/other.py"))
        with self.assertRaises(v3.G36Denied):
            v3.signature(self.key,modified,9,323,"1"*64,324,"2"*64)


    def test_v1_v2_v3_original_workflow_routes_are_exclusive(self):
        from pathlib import Path
        workflow=(Path(__file__).resolve().parents[1]/
                  ".github/workflows/forge-f139-development-worker.yml").read_text("utf-8")
        self.assertEqual(workflow.count("inputs.target_package != 'f139-nci04-v2' && inputs.target_package != 'f139-nci04-v3'"),2)
        self.assertIn("native-authorize-v3:",workflow)
        self.assertIn("native-execute-v3:",workflow)
        self.assertIn("nci04_owner_v3_dispatch authorize-v3",workflow)
        self.assertIn("nci04_owner_v3_dispatch execute-v3",workflow)
        self.assertIn("F139_NATIVE_PROTOCOL: v3",workflow)
        self.assertIn("needs: native-authorize-v3",workflow)
        self.assertIn("F139_WORKER_HMAC_KEY: ${{ secrets.F139_WORKER_HMAC_KEY }}",workflow)
        self.assertEqual(workflow.count("name: forge-f139-v2-native-receipt-"),1)
        self.assertEqual(workflow.count("name: forge-f139-v3-native-receipt-"),1)


if __name__=="__main__":
    unittest.main()

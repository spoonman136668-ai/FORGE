"""Production worker V3 regression contract; historical V1/V2 untouched."""
import copy
import unittest
from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from f139 import nci04_worker_v3 as v3
from f139.nci04_native_contract import Candidate
from f139.nci04_signed_native import NativeAdmission


class V3WorkerContractTests(unittest.TestCase):
    def setUp(self):
        self.candidate=Candidate(
            intent_sha256="a"*64,qualification_key="b"*64,
            target_commit="c"*40,target_tree_sha="d"*40,
            path="yggdrasil/public_causal_cells.py",
            before_sha256="e"*64,after_sha256="f"*64,
            after_bytes=b"print(1)",lane="Yggdrasil")
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def runner(self, lines, exitcode=0):
        def run(*args,**kwargs):
            return SimpleNamespace(stdout=lines,returncode=exitcode)
        return run

    def test_fixed_non_atlas_module_executes_with_positive_count(self):
        r=v3.invoke(v3.unit("test_native_cells.py"),self.root,
                    module="test_native_cells.py",
                    runner=self.runner(b"Ran 8 tests in 0.1s\nOK\n"))
        self.assertEqual(r["status"],"PASS")
        self.assertEqual(r["discovered_tests"],8)
        self.assertIsNone(r["child_peak_rss_bytes"])
        self.assertIs(r["resource_budget_verified"],False)

    def test_original_full_suite_is_executed_not_skipped(self):
        argv=v3.COMMAND+("-p","test_*.py","-v")
        r=v3.invoke(argv,self.root,module="test_*.py",
                    runner=self.runner(b"Ran 54 tests in 0.1s\nOK"))
        self.assertEqual(r["discovered_tests"],54)
        self.assertEqual(r["status"],"PASS")

    def test_original_frozen_g29_expected_modified_source_rejection(self):
        output=(b"Ran 4 tests in 0.1s\nFAIL\n" +
                b"YGG_ATLAS_FAIL_CLOSED: working source mismatch: "+
                v3.TARGET.encode())
        r=v3.invoke(v3.unit(v3.ATLAS),self.root,module=v3.ATLAS,
                    expected_rejection=True,runner=self.runner(output,1))
        self.assertEqual(r["status"],v3.CLOSED)
        self.assertEqual(r["returncode"],1)
        with self.assertRaises(v3.V3Denied):
            v3.invoke(v3.unit(v3.ATLAS),self.root,module=v3.ATLAS,
                      runner=self.runner(output,1))

    def test_forged_positive_atlas_and_unrelated_failure_cannot_qualify(self):
        for output,exitcode in [
            (b"Ran 4 tests in 0.1s\nOK",0),
            (b"Ran 4 tests in 0.1s\nModuleNotFoundError",1),
            (b"Ran 4 tests in 0.1s\nYGG_ATLAS_FAIL_CLOSED: indexed file set changed",1),
            (b"Ran 4 tests in 0.1s\nworking source mismatch: other.py",1),
        ]:
            with self.subTest(exitcode=exitcode),self.assertRaises(v3.V3Denied):
                v3.invoke(v3.unit(v3.ATLAS),self.root,module=v3.ATLAS,
                          expected_rejection=True,runner=self.runner(output,exitcode))

    def test_zero_test_forgery_and_wrong_argv_rejected(self):
        for output in (b"Ran 0 tests in 0.2s\nOK",b"test succeeded"):
            with self.assertRaises(v3.V3Denied):
                v3.invoke(v3.unit(v3.ATLAS),self.root,module=v3.ATLAS,
                          runner=self.runner(output))
        for argv in (("bash","-c","echo success"),
                     v3.COMMAND+("-p","something_else.py","-v"),
                     v3.COMMAND+("-p","test_*.py","-k","skip-all","-v")):
            with self.assertRaises(v3.V3Denied):
                v3.invoke(argv,self.root,module="test_*.py",
                          runner=self.runner(b"Ran 54 tests in 0.1s\nOK"))

    def test_existing_source_lane_scope_unmodified(self):
        wrong=copy.copy(self.candidate)
        object.__setattr__(wrong,"lane","Wingless")
        with self.assertRaises(v3.V3Denied):
            v3.inventory(wrong,self.root)

    def test_v3_receipt_is_distinct_and_refuses_positive_authority(self):
        admission=NativeAdmission(ticket="f139-nci04-i1200-abcdefabcdef-aaaaaaaa",
                                  lane="Yggdrasil",source_sha="a"*40,
                                  run_id=999999999,runner_os="ubuntu-latest",
                                  issue_number=1200,issue_id=123321,
                                  intent=self.candidate,
                                  authorization_sha256="c"*64)
        report={"schema":v3.SCHEMA,"os":"ubuntu-latest",
                "ticket_source_commit":self.candidate.target_commit,
                "target_tree_sha":self.candidate.target_tree_sha,
                "path":self.candidate.path,
                "candidate_sha256":self.candidate.after_sha256,
                "scientific_first_use":False,
                "protected_holdouts_accessed":0,
                "accepted_ref_mutations":0,
                "paid_model_calls":0,
                "intent_sha256":self.candidate.intent_sha256,
                "qualification_key":self.candidate.qualification_key,
                "native_qualified":False,"child_cpu_rss_verified":False}
        receipt=v3.receipt_v3(admission,report)
        self.assertEqual(receipt["schema"],v3.RECEIPT)
        self.assertIs(receipt["native_qualified"],False)
        report["native_qualified"]=True
        with self.assertRaises(v3.V3Denied):
            v3.receipt_v3(admission,report)
        report["native_qualified"]=False
        report["child_cpu_rss_verified"]=True
        with self.assertRaises(v3.V3Denied):
            v3.receipt_v3(admission,report)


    def test_original_worker_produces_positive_development_job_outcome_only_with_positive_receipt(self):
        import os
        from f139.nci04_worker_entry import execute_v3_development
        from f139.nci04_native_contract import canonical
        admission=NativeAdmission(
            ticket="f139-nci04-i1201-abcdefabcdef-aaaaaaaa",
            lane="Yggdrasil",source_sha="a"*40,
            run_id=999999998,runner_os="windows-latest" if os.name=="nt" else "ubuntu-latest",
            issue_number=1201,issue_id=123322,intent=self.candidate,
            authorization_sha256="c"*64)
        report={"schema":v3.SCHEMA,"native_qualified":True,
                "scientific_first_use":False,
                "child_cpu_rss_verified":True}
        receipt={"native_qualified":True,"development_only":True,
                 "scientific_first_use_authorized":False,
                 "accepted_ref_mutations":0,"paid_model_calls":0}
        output=self.root/"out-positive"
        scratch=self.root/"scratch"
        native=self.root/"native"
        for folder in (output,scratch,native):folder.mkdir()
        env={"F139_NATIVE_PROTOCOL":"v3",
             "F139_NATIVE_V3_AUTHORIZATION_PASSED":"true"}
        with patch.dict(os.environ,env,clear=True),\
             patch("f139.nci04_worker_v3.run_v3",return_value=report) as run,\
             patch("f139.nci04_worker_v3.receipt_v3",return_value=receipt):
            actual,completed=execute_v3_development(admission,native,scratch,output)
        self.assertTrue(completed)
        self.assertEqual(actual,receipt)
        self.assertEqual((output/"f139-v3-native-receipt.json").read_bytes(),
                         canonical(receipt))
        self.assertEqual((output/"f139-v3-native-report.json").read_bytes(),
                         canonical(report))
        self.assertEqual(run.call_count,1)
        self.assertEqual({p.name for p in output.iterdir()},
                         {"f139-v3-native-report.json","f139-v3-native-receipt.json"})

    def test_negative_v3_receipt_does_not_complete_job_or_grant_science(self):
        import os
        from f139.nci04_worker_entry import execute_v3_development
        admission=NativeAdmission(
            ticket="f139-nci04-i1202-abcdefabcdef-aaaaaaaa",
            lane="Yggdrasil",source_sha="a"*40,
            run_id=999999997,runner_os="windows-latest" if os.name=="nt" else "ubuntu-latest",
            issue_number=1202,issue_id=123323,intent=self.candidate,
            authorization_sha256="c"*64)
        output=self.root/"out-negative"
        scratch=self.root/"scratch-neg"
        native=self.root/"native-neg"
        for folder in (output,scratch,native):folder.mkdir()
        report={"schema":v3.SCHEMA,"native_qualified":False}
        receipt={"native_qualified":False,"development_only":True,
                 "scientific_first_use_authorized":False,
                 "accepted_ref_mutations":0,"paid_model_calls":0}
        with patch.dict(os.environ,{
             "F139_NATIVE_PROTOCOL":"v3",
             "F139_NATIVE_V3_AUTHORIZATION_PASSED":"true"},clear=True),\
             patch("f139.nci04_worker_v3.run_v3",return_value=report),\
             patch("f139.nci04_worker_v3.receipt_v3",return_value=receipt):
            actual,completed=execute_v3_development(admission,native,scratch,output)
        self.assertFalse(completed)
        self.assertEqual(actual["native_qualified"],False)


if __name__=="__main__":
    unittest.main()

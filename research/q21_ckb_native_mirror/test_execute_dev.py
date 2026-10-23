"""Network-free checks of Q21 science executor's mandatory admission ordering."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import execute_dev as x
import admit_exact as a


class Q21DevelopmentConsumerTests(unittest.TestCase):
    def test_preflight_never_generates_science(self):
        result = x.preflight()
        self.assertEqual(result["development_cohorts_generated"], 0)
        self.assertEqual(result["owner_admission"], "NOT_REQUESTED")
        self.assertFalse(result["protected_or_original_first_use"])

    def test_bad_owner_is_refused_before_source_generation(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "report.json"
            with patch.object(x, "sourcefree_import", side_effect=AssertionError("scientific import before owner")), \
                 patch.object(x, "verify_source", side_effect=AssertionError("source inspect before owner")):
                with self.assertRaises(a.Refused):
                    x.run(Path(td), dest, {}, lambda _: self.fail("unauthorized network"))
            self.assertFalse(dest.exists())

    def test_authenticated_run_cannot_bypass_git_source_identity(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "report.json"
            with patch.object(x, "authenticated_owner", return_value={"decision": "OWNER_AUTHENTICATED_SOURCEFREE_DEVELOPMENT_ONLY"}), \
                 patch.object(x, "verify_source", side_effect=x.Blocked("Q21_DEV_SOURCE_COMMIT_DRIFT")), \
                 patch.object(x, "sourcefree_import", side_effect=AssertionError("should never load model")):
                with self.assertRaisesRegex(x.Blocked, "SOURCE_COMMIT_DRIFT"):
                    x.run(Path(td), dest, {}, lambda _: {})
            self.assertFalse(dest.exists())

    def test_good_source_and_real_owner_yield_mock_report_without_live_cohorts(self):
        class FakeSource:
            PROTOCOL_BLOB = a.PROTOCOL
            def protocol(self): return {"schema":"toy"}
        class FakeRunner:
            def execute_development(self,doc):
                self._called = True
                return {"frozen_preliminary_decision": {"q21_development_thresholds_met": False},
                        "schema":"forge.q21.complete-sourcefree-resource.v1"}
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)
            output=source/"report.json"
            mock=FakeRunner()
            owner_receipt={"decision": "OWNER_AUTHENTICATED_SOURCEFREE_DEVELOPMENT_ONLY",
                           "scientific_execution_performed":False,
                           "ckb_run_id":12345678,"ckb_source_sha":"a"*40,
                           "scope":"FRESH_Q21_FIT_TRAIN_FIT_VALID_DEV_ONLY"}
            with patch.object(x,"authenticated_owner",return_value=owner_receipt), \
                 patch.object(x,"verify_source",return_value=None), \
                 patch.object(x,"sourcefree_import",return_value=(FakeSource(),mock,None)), \
                 patch.object(x,"native_os",return_value="Linux"):
                result=x.run(source,output,{},lambda _: {})
                self.assertTrue(mock._called)
                self.assertFalse(json.loads(output.read_text())["scientific_first_use"])
                self.assertEqual(result["ckb_owner_run_id"],12345678)
                with self.assertRaisesRegex(x.Blocked, "OUTPUT_MUST_BE_NEW_ABSOLUTE_PATH"):
                    x.run(source,output,{},lambda _:{})

    def test_cross_os_reconciliation_refuses_inconsistent_receipts(self):
        with tempfile.TemporaryDirectory() as td:
            tmp=Path(td)
            w=tmp/"win.json";u=tmp/"linux.json";out=tmp/"result.json"
            w.write_text(json.dumps({"os_name":"Windows","candidate_source_sha":a.SOURCE,
                                    "scientific_first_use":False,
                                    "ckb_owner_scope":"FRESH_Q21_FIT_TRAIN_FIT_VALID_DEV_ONLY",
                                    "ckb_owner_run_id":33,
                                    "ckb_owner_source_sha":"a"*40}))
            u.write_text(json.dumps({"os_name":"Linux","candidate_source_sha":a.SOURCE,
                                    "scientific_first_use":False,
                                    "ckb_owner_scope":"FRESH_Q21_FIT_TRAIN_FIT_VALID_DEV_ONLY",
                                    "ckb_owner_run_id":44,
                                    "ckb_owner_source_sha":"a"*40}))
            with patch.object(x,"verify_source",return_value=None), \
                 patch.object(x,"sourcefree_import",side_effect=AssertionError("must not reconcile")):
                with self.assertRaisesRegex(x.Blocked,"DIFFERENT_OWNER_ADMISSIONS"):
                    # A checked contender must not produce any accepted science.
                    x.reconcile(tmp,w,u,out)
            self.assertFalse(out.exists())

    def test_unauthorized_platform(self):
        with patch.object(x.sys,"platform","darwin"):
            with self.assertRaisesRegex(x.Blocked,"UNSUPPORTED_OPERATING_SYSTEM"):
                x.native_os()


if __name__=="__main__":
    unittest.main()

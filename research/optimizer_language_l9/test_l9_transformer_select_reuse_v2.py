"""Fail-closed admission proof for dormant L9 Transformer evaluation recovery v2.

No model/corpus loads, no network calls, no SELECT or AUDIT access.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import l9_transformer_select_reuse_v2 as v2

class RecoveryV2Tests(unittest.TestCase):
    def records(self,seed=1701):
        pair=v2.ORIGINAL_JOBS[seed]
        job={"id":pair["job_id"],"run_id":pair["run_id"],
             "status":"completed","conclusion":"failure"}
        run={"id":pair["run_id"],"head_sha":pair["head_sha"],
             "status":"completed","conclusion":"failure"}
        prefit={"id":v2.REQUIRED_PREFIT_RUN,"head_sha":v2.REQUIRED_PREFIT_HEAD,
                "status":"completed","conclusion":"success"}
        return job,run,prefit

    def test_successful_original_fails_closed(self):
        for seed in (1701,1702):
            for position in (0,1):
                records=list(self.records(seed))
                records[position]["conclusion"]="success"
                with self.subTest(seed=seed,position=position),self.assertRaises(ValueError):
                    v2.assert_admission(seed,*records)

    def test_running_original_fails_closed(self):
        for seed in (1701,1702):
            for position in (0,1):
                records=list(self.records(seed))
                records[position]["status"]="in_progress"
                with self.subTest(seed=seed,position=position),self.assertRaises(ValueError):
                    v2.assert_admission(seed,*records)

    def test_identity_drift_and_missing_prefit_fail_closed(self):
        for seed in (1701,1702):
            for position,key,val in (
                (0,"id",-1),(0,"run_id",-1),
                (1,"id",-1),(1,"head_sha","bad"),
                (2,"id",-1),(2,"head_sha","bad"),
                (2,"conclusion","failure"),(2,"status","queued")
            ):
                records=list(self.records(seed))
                records[position][key]=val
                with self.subTest(seed=seed,position=position,key=key),self.assertRaises(ValueError):
                    v2.assert_admission(seed,*records)

    def test_only_explicit_terminal_failure_admitted(self):
        for seed in (1701,1702):
            records=self.records(seed)
            self.assertTrue(v2.assert_admission(seed,*records))
            records[0]["conclusion"]="timed_out"
            records[1]["conclusion"]="timed_out"
            self.assertTrue(v2.assert_admission(seed,*records))
        with self.assertRaises(ValueError):
            v2.assert_admission(42,*self.records())

    def test_recovery_receipt_is_distinct(self):
        self.assertNotEqual(v2.SCHEMA,"forge.optimizer.language.l9.neural-select-development-v1")
        self.assertEqual(set(v2.ORIGINAL_JOBS),{1701,1702})
        self.assertEqual(v2.REQUIRED_PREFIT_RUN,40050110176)

    def test_missing_attestation_does_not_run(self):
        # All real-run prerequisites are required; absent JSON raises before
        # model import, source dataset access, or any I/O output.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            output=root/"result.json"
            with self.assertRaises(FileNotFoundError):
                v2.run(root,root,1701,output,root/"none-job.json",
                       root/"none-run.json",root/"none-prefit.json")
            self.assertFalse(output.exists())

if __name__=="__main__":
    unittest.main()

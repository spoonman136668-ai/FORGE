"""Cancellation-only L9 SELECT v3 admission: frozen identity and negatives.

No model fitting, corpus reading, network, SELECT evaluation or first-use.
"""
from pathlib import Path
import tempfile
import unittest
import l9_transformer_select_cancel_v3 as v3
import l9_transformer_select_reuse_v2 as v2


class CancelledOriginalRecoveryTests(unittest.TestCase):
    def records(self,seed=1701):
        orig=v3.ORIGINAL_JOBS[seed]
        job={"id":orig["job_id"],"run_id":orig["run_id"],
             "status":"completed","conclusion":"cancelled"}
        run={"id":orig["run_id"],"head_sha":orig["head_sha"],
             "status":"completed","conclusion":"cancelled"}
        prefit={"id":v3.REQUIRED_PREFIT_RUN,
                "head_sha":v3.REQUIRED_PREFIT_HEAD,
                "status":"completed","conclusion":"success"}
        artifacts={"total_count":0,"artifacts":[]}
        return job,run,prefit,artifacts

    def test_strict_original_both_seed_cancellation_only(self):
        for seed in (1701,1702):
            self.assertTrue(v3.assert_admission(seed,*self.records(seed)))
            for field in ("success","failure","timed_out","skipped",None):
                for pos in (0,1):
                    vals=list(self.records(seed))
                    vals[pos]["conclusion"]=field
                    with self.subTest(seed=seed,field=field,pos=pos):
                        with self.assertRaises(ValueError):
                            v3.assert_admission(seed,*vals)

    def test_running_original_prohibited(self):
        for seed in (1701,1702):
            for pos in (0,1):
                vals=list(self.records(seed))
                vals[pos]["status"]="in_progress"
                with self.subTest(seed=seed,pos=pos):
                    with self.assertRaisesRegex(ValueError,"NOT_TERMINAL"):
                        v3.assert_admission(seed,*vals)

    def test_no_other_artifacts_even_unrelated(self):
        for seed in (1701,1702):
            vals=list(self.records(seed))
            vals[3]={"total_count":1,"artifacts":[{"id":1}]}
            with self.assertRaisesRegex(ValueError,"ARTIFACTS_NOT_EMPTY"):
                v3.assert_admission(seed,*vals)
            vals[3]={"total_count":0,"artifacts":[{"id":1}]}
            with self.assertRaisesRegex(ValueError,"ARTIFACTS_NOT_EMPTY"):
                v3.assert_admission(seed,*vals)

    def test_frozen_identity_and_prefit_rejections(self):
        cases=((0,"id",123),(0,"run_id",123),(1,"id",123),
               (1,"head_sha","wrong"),(2,"id",123),
               (2,"head_sha","wrong"),(2,"status","in_progress"),
               (2,"conclusion","failure"))
        for seed in (1701,1702):
            for pos,key,bad in cases:
                vals=list(self.records(seed))
                vals[pos][key]=bad
                with self.subTest(seed=seed,pos=pos,key=key):
                    with self.assertRaises(ValueError):
                        v3.assert_admission(seed,*vals)
        with self.assertRaisesRegex(ValueError,"unfrozen seed"):
            v3.assert_admission(999,*self.records())

    def test_separate_source_schema_and_comparison_boundaries(self):
        self.assertEqual(v3.ORIGINAL_JOBS,v2.ORIGINAL_JOBS)
        self.assertEqual(v3.REQUIRED_PREFIT_RUN,v2.REQUIRED_PREFIT_RUN)
        self.assertNotEqual(v3.SCHEMA,v2.SCHEMA)
        self.assertNotEqual(v3.SCHEMA,
            "forge.optimizer.language.l9.neural-select-development-v1")
        self.assertIn("after-cancellation-v3",v3.SCHEMA)
        self.assertIs(v3.model,v2.model)
        self.assertIs(v3.source,v2.source)

    def test_missing_attestation_prevents_any_science(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            output=root/"out.json"
            with self.assertRaises(FileNotFoundError):
                v3.run(root,root,1701,output,*([root/"missing.json"]*4))
            self.assertFalse(output.exists())

    def test_raw_original_frozen_source_stays_unchanged(self):
        root=Path(__file__).resolve().parent
        s=(root/"l9_transformer_select_cancel_v3.py").read_text()
        for forbidden in ("train_neural(", "load_audit(",
                          "official_test", "select_count=319"):
            if forbidden=="official_test":
                continue
            self.assertNotIn(forbidden,s)
        self.assertIn('"scientific_go":False',s)
        self.assertIn('"audit_dev_reference_consumed":False',s)
        self.assertIn('"new_independent_seal_and_acceptance_required":True',s)

if __name__=="__main__":
    unittest.main()

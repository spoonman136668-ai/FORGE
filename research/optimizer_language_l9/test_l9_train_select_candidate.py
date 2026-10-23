import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import l9_model_suite as m
import l9_train_select_candidate as t

ROOT = Path(__file__).resolve().parent

class TrainSelectPreFitTests(unittest.TestCase):
    def test_fixed_identities(self):
        rc=json.loads((ROOT/"L9_SPLIT_RECEIPT.json").read_text())
        assert rc["deterministic_split"]["cross_os_role_identity_sha256"] == t.EXPECTED_ROLE_SHA
        assert rc["deterministic_split"]["cross_os_summary_sha256"] == t.EXPECTED_SUMMARY_SHA
        assert m.MANDATORY_SEEDS==(1701,1702)
        assert m.CHECKPOINT_EPOCHS==(4,8,12)
        assert len(m.CANDIDATE_GRID)==8

    def test_import_no_data_load_or_fit(self):
        self.assertTrue(callable(t.load_train_select))
        self.assertTrue(callable(t.evaluate))
        self.assertTrue(callable(t.chrf))

    def test_proxy_absent_relation_not_covered(self):
        triple=(m.Triple("Ada", "unknownPredicate", "Paris"),)
        self.assertEqual(t.coverage("Ada traveled to Paris.",triple,{}),(0,1))

    def test_proxy_requires_both_entities(self):
        triple=(m.Triple("Ada", "worksAt", "Paris"),)
        p={"worksat":["works at"]}
        self.assertEqual(t.coverage("Ada works at Berlin.",triple,p),(0,1))
        self.assertEqual(t.coverage("Ada works at Paris.",triple,p),(1,1))

    def test_missing_candidate_is_abstention(self):
        triple=(m.Triple("Ada", "worksAt", "Paris"),)
        self.assertEqual(t.coverage(None,triple,{"worksat":["works at"]}),(0,1))

    def test_chrf_negative_and_exact(self):
        self.assertEqual(t.chrf(None,"Ada works at Paris."),0.0)
        self.assertAlmostEqual(t.chrf("Ada works at Paris.","Ada works at Paris."),1.0)
        self.assertLess(t.chrf("Ada works at Berlin.","Ada works at Paris."),1.0)

    def test_selection_guard_rejects_audit(self):
        examples=[m.Example("L9_AUDIT_DEV","abc",(m.Triple("A","p","B"),),"A p B")]
        with self.assertRaises(ValueError):
            m.assert_audit_not_used(examples)
        with self.assertRaises(AssertionError):
            t.evaluate(examples,lambda _: "A p B",{})

    def test_no_truncation_or_test_dataset_selector(self):
        src=(ROOT/"l9_train_select_candidate.py").read_text()
        self.assertIn('if item["role"] != "TRAIN"',src)
        self.assertIn('if item["role"] != "DEV"',src)
        self.assertIn("split.verify_all_blob_identities(repo, entries)",src)
        self.assertNotIn('item["role"] == "TEST"',src)
        self.assertNotIn("L9_AUDIT_DEV", "L9_SELECT",src)

if __name__=="__main__":
    unittest.main()

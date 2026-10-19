"""F124-BO original source admission negative tests (no registered source use)."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file)
    o=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(o)
    return o


a=module("bo_mod_origin_preuse","f124bo_mod_source.py")
b=module("bo_feistel_origin_preuse","f124bo_feistel_source.py")
w=module("bo_provider_preuse","f124bo_source_witness.py")


class IndependentBornSourceGuard(unittest.TestCase):
    def test_original_commit_births_without_constructing_FIT(self):
        r=w.verify(remote=False)
        self.assertEqual(len(r["original_births"]),4)
        self.assertTrue(r["source_birth_after_frozen_learner"])
        self.assertEqual(r["registered_FIT_cases_constructed"],0)
        self.assertEqual(r["protected_U_R_and_new_holdouts_constructed"],0)
        self.assertFalse(r["independent_external_thirdparty_origin_certified"])

    def test_separate_new_sources_and_reject_old_protected_identity(self):
        self.assertEqual(len(a.FIT),12)
        self.assertEqual(len(b.FIT),12)
        self.assertFalse(set(a.FIT)&set(b.FIT))
        self.assertFalse(set(a.FIT)&set(a.RESERVED))
        self.assertFalse(set(b.FIT)&set(b.RESERVED))
        for m in (a,b):
            for seed in (918000,919000,914000,915000,916000,917000,
                         900000,901000,902000,903000,920100,920227,
                         921100,921227,-940,-939):
                with self.assertRaises(ValueError):
                    m.make(seed)

    def test_source_inverse_reversible_without_consuming_task(self):
        key=(53,359,18)
        for x in range(0,65536,511):
            self.assertEqual(a.inverse(a.forward(x,key),key),x)
        rounds=((5,3,20),(7,11,66),(9,24,55),(13,33,77))
        for x in range(0,65536,997):
            self.assertEqual(b.inverse(b.forward(x,rounds),rounds),x)


if __name__=="__main__":
    unittest.main()

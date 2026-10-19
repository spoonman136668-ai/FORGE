"""F124-BP source-provenance-focused qualification, zero registered use."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


a=module("bp_source_a_new","f124bp_procedural_source.py")
b=module("bp_source_b_new","f124bp_feedback_source.py")
w=module("bp_original_provenance","f124bp_source_witness.py")
eval=module("bp_firstuse_guard","f124bp_fit_eval.py")


class QualifiedBeforeScientificFirstUse(unittest.TestCase):
    def test_parent_source_born_after_unchanged_model_and_original_protocol(self):
        receipt=w.check(provider=False)
        self.assertEqual(len(receipt["verified"]),4)
        self.assertTrue(receipt["original_source_birth_after_qualified_model"])
        self.assertEqual(receipt["registered_cases_generated"],0)
        self.assertEqual(receipt["protected_source_cases_generated"],0)
        self.assertFalse(receipt["third_party_external_scientific_novelty"])

    def test_all_old_consumed_and_protected_identity_denied(self):
        self.assertEqual((a.FIT.start,a.FIT.stop),(922000,922012))
        self.assertEqual((b.FIT.start,b.FIT.stop),(923000,923012))
        self.assertEqual(len(a.SEALED),128)
        self.assertEqual(len(b.SEALED),128)
        for module_ in (a,b):
            for case in (-940,-939,900000,914000,915000,916000,917000,
                         918000,919000,920000,921000,
                         922100,922227,923100,923227,902000,903000):
                with self.assertRaises(ValueError):
                    module_.make(case)
        for case in (900000,914000,915000,916000,917000,
                     920000,921000,922100,923100,902000,903000):
            with self.assertRaises(RuntimeError):
                eval.identity(case)

    def test_invertible_private_relations_without_source_case_construction(self):
        key=( ((23,1),(57,41),(177,15)), ((31,5),(111,129)) )
        for x in range(0,65536,713):
            self.assertEqual(a.inverse(a.forward(x,key),key),x)
        private=((23,11,59,77),(5,113,47,3),(201,189,7,39))
        for x in range(0,65536,829):
            self.assertEqual(b.inverse(b.forward(x,private),private),x)

    def test_original_model_and_control_sha_are_pinned(self):
        self.assertEqual(eval.object_id(eval.HERE/
            "f124bp_compact_learner.py"),eval.BLOBS["learner"])
        self.assertEqual(eval.object_id(eval.NATIVE/
            "f124az_joint_public_inverse.py"),eval.BLOBS["AZ"])
        self.assertEqual(eval.object_id(eval.HERE/
            "f124bp_procedural_source.py"),eval.BLOBS["procedural"])
        self.assertEqual(eval.object_id(eval.HERE/
            "f124bp_feedback_source.py"),eval.BLOBS["feedback"])


if __name__=="__main__":
    unittest.main()

"""F124-BJ nonconsuming source-birth and training resource instrumentation tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

DIR = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, DIR / path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


w = load("f124bj_witness_test", "f124bj_witness.py")
train = load("f124bj_train_measure_test", "f124bj_train_measure.py")
a = load("f124bj_affine_test", "f124bj_affine_source.py")
b = load("f124bj_shear_test", "f124bj_shear_source.py")


class SourceBeforeFirstUse(unittest.TestCase):
    def test_exact_frozen_source_birth_local_custody(self):
        q = w.verify(provider=False)
        self.assertEqual(len(q["birth_order"]), 3)
        self.assertFalse(q["source_git_provider_authenticated"])
        self.assertEqual(q["generated_registered_train"], 0)
        self.assertEqual(q["generated_U_or_R"], 0)
        self.assertFalse(q["historical_source_overlap_comprehensively_audited"])

    def test_independent_numeric_source_identities_without_first_use(self):
        self.assertEqual(len(a.TRAIN), 96)
        self.assertEqual(len(b.TRAIN), 96)
        self.assertTrue(set(a.TRAIN).isdisjoint(set(b.TRAIN)))
        self.assertEqual(a.TRAIN.start, 900000)
        self.assertEqual(b.TRAIN.stop, 900192)
        self.assertNotEqual(a.SALT, b.SALT)
        for mod, synthetic in ((a, -950), (b, -951)):
            pub, private = mod.make(synthetic)
            self.assertEqual(len(pub[0]), 40)
            self.assertEqual(len(pub[1]), 8)
            self.assertEqual(len(private["corruption_private"]), 6)
            self.assertEqual(len({x for x, _ in pub[0] + pub[1]}), 48)
            for forbidden in (0, -939, -940, 901000, 902000, 902127,
                              903000, 903127, 900192):
                with self.assertRaises(ValueError):
                    mod.make(forbidden)

    def test_model_and_baseline_frozen_source(self):
        self.assertEqual(train.file_blob(train.NATIVE /
                         "f124az_joint_public_inverse.py"), train.AZ_BLOB)
        self.assertEqual(train.file_blob(train.HERE /
                         "20261018-mass-learned-kernel.py"), train.KERNEL_BLOB)
        for label in ("U", "R"):
            fit, check = train.source_public(label)
            self.assertEqual(len(fit), 40)
            self.assertEqual(len(check), 8)
        with self.assertRaises(RuntimeError):
            train.source_public("SEALED_902000")

    def test_protected_identity_and_invalid_arm_refusal_without_train(self):
        with self.assertRaises(RuntimeError):
            train.task_fit("invalid", "U", "00000000")
        with self.assertRaises(RuntimeError):
            train.task_fit("prior_kernel", "PROTECTED", "00000000")


if __name__ == "__main__":
    unittest.main()

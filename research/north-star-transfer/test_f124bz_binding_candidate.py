"""F124-BZ source-neutral algebra/fit tests, NOT novel scientific tasks.

Use fresh in-memory deterministic arithmetic examples generated solely
inside this test. They do not correspond to BY, BV, BX, old original source
families, 924xxx/925xxx or protected test data.
"""
from __future__ import annotations
import importlib.util
import random
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
S=importlib.util.spec_from_file_location(
    "f124bz_four_variable_binding",HERE/"f124bz_binding_candidate.py")
binder=importlib.util.module_from_spec(S)
S.loader.exec_module(binder)


def fixture(word,seed):
    rng=random.Random(seed)
    xs=rng.sample(range(65536),48)
    corrupt={1,5,12,19,24,35}
    observations=[(x,binder.forward(x,word)^(1 if i in corrupt else 0))
                  for i,x in enumerate(xs)]
    return observations[:40],observations[40:]


class TrainedVariableBindings(unittest.TestCase):
    def test_exact_31bit_state_and_all_domain_inversion(self):
        designs=[
            ((2,0,3,1),(3,5,7,1),(1,9,4,13),0),
            ((3,1,0,2),(1,9,11,1),(2,0,7,5),1),
            ((1,3,2,0),(15,3,1,1),(12,6,2,15),1)
        ]
        for perm,gains,biases,gate in designs:
            with self.subTest(perm=perm,gate=gate):
                state=binder.pack(perm,gains,biases,gate)
                self.assertLess(state,2**31)
                self.assertEqual(binder.unpack(state),
                                 (perm,gains,biases,gate))
                for x in range(65536):
                    y=binder.forward(x,state)
                    self.assertEqual(binder.inverse(y,state),x)

    def test_training_from_public_fit_only_on_predeclared_math_examples(self):
        cases=[
          ((2,0,3,1),(3,5,7,1),(1,9,4,13),0,620001),
          ((3,1,0,2),(1,9,11,1),(2,0,7,5),1,620002),
        ]
        for perm,gains,biases,gate,seed in cases:
            truth=binder.pack(perm,gains,biases,gate)
            fit,check=fixture(truth,seed)
            candidate,receipt=binder.learn(fit,check)
            self.assertIsNotNone(candidate,receipt)
            self.assertTrue(receipt["confidence"])
            self.assertEqual(receipt["fit_only_relation_flag"],gate)
            self.assertEqual(receipt["training_residual_evaluations"],48000)
            self.assertTrue(receipt["trained_on_public_FIT_only"])
            self.assertTrue(receipt["CHECK_only_veto"])
            self.assertFalse(receipt["source_label_or_private_truth_used"])
            for x in (0,1,0x1234,0x5678,0xffff,0x82a4):
                self.assertEqual(binder.forward(x,candidate),
                                 binder.forward(x,truth))

    def test_check_data_is_veto_only(self):
        truth=binder.pack((2,0,3,1),(3,5,7,1),(1,9,4,13),0)
        fit,check=fixture(truth,620003)
        a,old=binder.learn(fit,check)
        damaged=[(x,y^65535) for x,y in check]
        b,new=binder.learn(fit,damaged)
        self.assertEqual(old["fit_only_permutation_index"],
                         new["fit_only_permutation_index"])
        self.assertEqual(old["fit_only_relation_flag"],
                         new["fit_only_relation_flag"])
        self.assertEqual(old["public_FIT_SHA256"],new["public_FIT_SHA256"])
        self.assertIsNone(b)
        self.assertFalse(new["confidence"])
        self.assertGreater(new["check_error_bits"],2)

    def test_invalid_words_or_duplicate_public_evidence_fail_closed(self):
        with self.assertRaises(ValueError):
            binder.unpack(2**31)
        with self.assertRaises(ValueError):
            binder.unpack(24)
        with self.assertRaises(ValueError):
            binder.pack((0,1,2,3),(2,3,5,1),(1,2,3,4),0)
        repeated=[(1,1)]*40
        with self.assertRaises(ValueError):
            binder.learn(repeated,[(1,1)]*8)

if __name__=="__main__":
    unittest.main()

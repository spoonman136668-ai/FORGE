"""F124-CA nonregistered arithmetic smoke test, not causal novelty."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import random
import unittest

HERE=Path(__file__).resolve().parent
def read(name,file):
    x=importlib.util.spec_from_file_location(name,HERE/file)
    o=importlib.util.module_from_spec(x)
    x.loader.exec_module(o)
    return o
candidate=read("CA_original_BZ","f124bz_binding_candidate.py")
control=read("CA_fully_trained_comparator","f124ca_trained_symbol_control.py")

def observations(state,seed):
    rng=random.Random(seed)
    examples=rng.sample(range(65536),48)
    return [(x,candidate.forward(x,state)^(1 if j in {2,8,13,24,29,34} else 0))
            for j,x in enumerate(examples)]

class EqualInformationTrainedLearning(unittest.TestCase):
    def test_same_public_FIT_8_CHECK_and_original_training_bound(self):
        pairs=[
          ((3,0,1,2),(3,5,11,1),(6,4,12,9),0,630901),
          ((1,2,3,0),(1,7,5,1),(3,10,7,1),1,630902)]
        for perm,gains,biases,gate,seed in pairs:
            word=candidate.pack(perm,gains,biases,gate)
            obs=observations(word,seed)
            trained_a,ra=candidate.learn(obs[:40],obs[40:])
            trained_b,rb=control.train(obs[:40],obs[40:])
            self.assertEqual(ra["training_residual_evaluations"],48000)
            self.assertEqual(rb["full_train_residuals"],48000)
            self.assertEqual(rb["full_train_symbol_score_evaluations"],48000)
            self.assertTrue(rb["sourceblind_FIT_only"])
            self.assertTrue(rb["CHECK_veto_only"])
            self.assertFalse(rb["original_candidate_learn_called"])
            self.assertTrue(rb["same_31bit_state_plus_reserved_zero"])
            self.assertTrue(ra["trained_on_public_FIT_only"])
            self.assertIsNotNone(trained_a,ra)
            self.assertIsNotNone(trained_b,rb)
            self.assertEqual(ra["public_FIT_SHA256"],rb["public_FIT_hash"])
            for x in (0,1,0x1234,0xffff,0x9856):
                self.assertEqual(candidate.forward(x,trained_a),
                                 candidate.forward(x,word))
                self.assertEqual(control.forward(x,trained_b),
                                 candidate.forward(x,word))
                self.assertEqual(control.inverse(
                    control.forward(x,trained_b),trained_b),x)

    def test_CHECK_veto_without_training_changes(self):
        state=candidate.pack((3,0,1,2),(3,5,11,1),(6,4,12,9),0)
        obs=observations(state,630903)
        fit,check=obs[:40],obs[40:]
        accepted,positive=control.train(fit,check)
        rejected,negative=control.train(fit,[(x,y^65535) for x,y in check])
        self.assertEqual(positive["public_FIT_hash"],negative["public_FIT_hash"])
        self.assertEqual(positive["permutation_index"],negative["permutation_index"])
        self.assertEqual(positive["relation_gate"],negative["relation_gate"])
        self.assertIsNotNone(accepted,positive)
        self.assertIsNone(rejected)
        self.assertFalse(negative["accepted"])
        self.assertGreater(negative["CHECK_bit_errors"],2)

    def test_bad_input_fails_closed(self):
        with self.assertRaises(ValueError):
            control.train([(0,0)]*40,[(0,0)]*8)

if __name__=="__main__":
    unittest.main()

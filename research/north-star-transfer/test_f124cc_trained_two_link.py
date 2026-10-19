"""F124-CC fully trained same-size/observations unit qualification.

These are disposable algebra unit fixtures, not the predeclared new
relationship graph families, previous science or protected cohorts.
"""
import importlib.util
import random
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file)
    obj=importlib.util.module_from_spec(sp)
    sp.loader.exec_module(obj)
    return obj
base=load("CC_original_frozen_CB_algebra","f124cb_dual_link_learner.py")
ctrl=load("CC_new_symbol_trained","f124cc_trained_two_link_control.py")

def examples(state,seed):
    rng=random.Random(seed)
    inp=rng.sample(range(65536),48)
    noise={1,5,12,19,24,35}
    obs=[(x,base.forward(x,state)^(1 if j in noise else 0))
         for j,x in enumerate(inp)]
    return obs[:40],obs[40:]

class EqualFullyTrainedControl(unittest.TestCase):
    def test_new_training_has_exact_same_FIT_information_state_and_search_count(self):
        for perm,gains,bias,links,seed in (
            ((0,3,1,2),(3,7,5,1),(8,1,6,12),(1,0),962217),
            ((3,2,0,1),(7,5,1,1),(10,12,1,2),(1,1),962218)
        ):
            state=base.pack(perm,gains,bias,links)
            fit,check=examples(state,seed)
            orig,r0=base.learn(fit,check)
            learned,r=ctrl.train(fit,check)
            self.assertEqual(r["train_residuals"],6560)
            self.assertEqual(r["train_score_samples"],6560)
            self.assertEqual(r["global_layouts_fully_trained"],96)
            self.assertEqual(r["original_public_FIT_sha256"],
                             r0["public_FIT_sha256"])
            self.assertTrue(r["fit_only_full_training"])
            self.assertTrue(r["CHECK_veto_only"])
            self.assertFalse(r["original_CB_model_learn_invoked"])
            self.assertTrue(r["same_32bit_persistent_state"])
            self.assertIsNotNone(orig)
            self.assertIsNotNone(learned)
            self.assertEqual(r["learned_flags"],links)
            for x in (0,1,0x1234,0x9876,0xabcd,65535):
                self.assertEqual(ctrl.forward(x,learned),base.forward(x,state))
                self.assertEqual(ctrl.inverse(ctrl.forward(x,learned),learned),x)

    def test_CHECK_is_only_a_veto(self):
        word=base.pack((0,3,1,2),(3,7,5,1),(8,1,6,12),(1,1))
        fit,check=examples(word,962219)
        a,correct=ctrl.train(fit,check)
        b,poison=ctrl.train(fit,[(x,y^65535) for x,y in check])
        self.assertEqual(correct["learned_flags"],poison["learned_flags"])
        self.assertEqual(correct["original_public_FIT_sha256"],
                         poison["original_public_FIT_sha256"])
        self.assertEqual(correct["FIT_bit_errors"],poison["FIT_bit_errors"])
        self.assertIsNotNone(a)
        self.assertIsNone(b)
        self.assertFalse(poison["confidence"])
        self.assertGreater(poison["CHECK_bit_errors"],2)

    def test_bad_data_fail_closed(self):
        with self.assertRaises(ValueError):
            ctrl.train([(0,0)]*40,[(0,0)]*8)

if __name__=="__main__":
    unittest.main()

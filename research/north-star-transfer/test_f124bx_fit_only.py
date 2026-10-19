"""F124-BX synthetic, nonregistered learner tests (no scientific source use)."""
import importlib.util
import random
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj
fit=load("bx_candidate","f124bx_learned_flag.py")
parent=load("bx_original","f124bq_program_learner.py")

def observations(p,flag,seed):
    rng=random.Random(seed)
    xs=rng.sample(range(65536),48)
    return [(x,fit._gate_y(parent.forward(x,p),flag)^
            (1 if i in {1,5,12,19,24,35} else 0))
            for i,x in enumerate(xs)]

class BoundedPublicFit(unittest.TestCase):
    def test_learn_flag_from_fit_and_keep_original(self):
        for p,flag,seed in (((1,0,1,0,1,1),1,31001),
                            ((53,37,41,19,0,1),0,31002),
                            ((87,109,9,173,1,0),0,31003)):
            sample=observations(p,flag,seed)
            word,receipt,possible=fit.learn(sample[:40],sample[40:],parent)
            self.assertIsNotNone(word,receipt)
            self.assertEqual(receipt["learned_structural_flag"],flag)
            self.assertEqual(receipt["actual_packed_state_bits"],32)
            self.assertEqual(receipt["original_BQ_FIT_error_bits"],6)
            self.assertEqual(receipt["original_BQ_CHECK_error_bits"],0)
            self.assertEqual(receipt["preselection_residual_observations"],10240)
            self.assertFalse(receipt["preselection_CHECK_used"])
            self.assertIn(word,possible)
            for x in range(0,65536,353):
                y=fit._gate_y(parent.forward(x,p),flag)
                self.assertEqual(fit.forward(x,word,parent),y)
                self.assertEqual(fit.inverse(y,word,parent),x)

    def test_check_veto_without_retry(self):
        sample=observations((1,0,1,0,1,1),1,31111)
        fail=[(x,y^65535) for x,y in sample[40:]]
        word,receipt,possible=fit.learn(sample[:40],fail,parent)
        self.assertIsNone(word)
        self.assertFalse(possible)
        self.assertEqual(receipt["learned_structural_flag"],1)
        self.assertFalse(receipt["preselection_CHECK_used"])

    def test_storage_remains_32_bits(self):
        for params in ((1,0,1,0,1,1),(127,255,127,255,1,0)):
            for third in (0,1):
                word=fit.encode(params,third)
                self.assertLess(word,2**31)
                self.assertEqual(fit.decode(word),(params,third))
        with self.assertRaises(ValueError):
            fit.decode(2**31)

if __name__=="__main__":
    unittest.main()

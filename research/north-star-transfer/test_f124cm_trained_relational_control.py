"""No-source engineering qualification of independent CM recurrent control."""
import importlib.util
from pathlib import Path
import random
import unittest
spec=importlib.util.spec_from_file_location('f124cm_control',Path(__file__).with_name('f124cm_trained_relational_control.py'))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fixture():
    # Deterministic synthetic engineering fixture, never an experiment family.
    model=m.Model((0x1047,0x4143,0x8200b,0x100201))
    rng=random.Random(18261019)
    seen=set();rows=[]
    while len(rows)<48:
        e,s,h=(rng.randrange(16) for _ in range(3))
        if (e,s,h) in seen:continue
        seen.add((e,s,h))
        rows.append((e,s,h,m.step(model,e,m.State(s,h)).current))
    return rows[:40],rows[40:]

class ControlEngineering(unittest.TestCase):
    def test_fully_trained_independent_nonlinear_control(self):
        fit,check=fixture();model,receipt=m.train(fit,check)
        self.assertIsNotNone(model,receipt)
        self.assertEqual(receipt['rank'],25)
        self.assertEqual(receipt['FIT_errors'],0)
        self.assertEqual(receipt['CHECK_errors'],0)
        self.assertEqual(receipt['coefficient_bits'],100)
        self.assertEqual(receipt['history_bits'],8)
        self.assertFalse(receipt['science_accepted'])
    def test_check_veto_only(self):
        fit,check=fixture();check=list(check)
        e,s,h,y=check[0];check[0]=(e,s,h,y^1)
        model,receipt=m.train(fit,check)
        self.assertIsNone(model)
        self.assertEqual(receipt['CHECK_errors'],1)
    def test_rank_insufficient_refuses(self):
        fit=[(e,s,0,0) for e in range(4) for s in range(10)]
        check=[(e,s,1,0) for e in range(2) for s in range(4)]
        model,receipt=m.train(fit,check)
        self.assertIsNone(model)
        self.assertLess(receipt['rank'],25)
    def test_boolean_and_bad_width_rejected(self):
        fit,check=fixture()
        with self.assertRaises(ValueError):m.train(fit[:39],check)
        with self.assertRaises(ValueError):m.train([(True,*r[1:]) for r in fit],check)
        with self.assertRaises(ValueError):m.step(m.Model((0,0,0,1<<25)),0,m.State(0,0))

if __name__=='__main__':unittest.main()

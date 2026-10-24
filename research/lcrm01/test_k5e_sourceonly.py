"""K5E source-only negative/protocol gates, no original heldout consumption."""
import unittest
from k5e_nonlinear_trial import (METHODS,COHORTS,SCHEMA,freeze,verdict,
                                 IndependentExhaustiveTriple)
from k5e_nonlinear_world import NonlinearParentWorld,depends_on_all_three

def synthetic():
 rows=[{"seed":seed,"exact":{m:m in ("ygg_R7_causal_parent_model",
 "conventional_exhaustive_triple") for m in METHODS}}
 for seed in COHORTS["DEV"] for _ in range(16)]
 cost={m:.0001 for m in METHODS};size={m:1800 for m in METHODS}
 return rows,cost,size

class K5EFrozenGuards(unittest.TestCase):
 def test_protocol_and_worlds(self):
  p=freeze()
  self.assertEqual(p["parent_K5D"],"7ce3c69ae8a8445256413318294e273f7dbf4d8a")
  self.assertEqual(len(set(COHORTS["FIT"]+COHORTS["CHECK"]+COHORTS["DEV"])),10)
  self.assertTrue(p["governance"]["original_K5D_prereg_interleaving_deviation_preserved"])
  self.assertFalse(p["governance"]["scientific_accepted"])
 def test_actual_world_nonlinear_and_deterministic(self):
  for state in (0,47,123,255):
   a=NonlinearParentWorld(311);b=NonlinearParentWorld(311)
   for op in (0,1,2):
    a.reset(state);b.reset(state)
    self.assertEqual(a.step(op),b.step(op))
  self.assertTrue(depends_on_all_three([0,1,1,0,1,0,0,1]))
 def test_matched_exhaustive_conventional_strong(self):
  w=NonlinearParentWorld(312);b=IndependentExhaustiveTriple()
  import random
  for op in (0,1,2):
   for x in random.Random(312+op).sample(range(256),192):
    w.reset(x);_,a,result=w.step(op);b.observe("w",a,x,result)
  b.fit()
  for state in (0,127,253):
   w.reset(state)
   for a in (0,1,2,0,1):w.step(a)
   self.assertEqual(b.predict("w",state,[0,1,2,0,1]),w.current())
 def test_no_unsupported_novelty_when_fitted_conventional_ties(self):
  rows,cost,size=synthetic()
  r=verdict(rows,cost,size)
  self.assertEqual(r["result"],"BOUNDED_LEARNED_NONLINEAR_CAUSAL_COMPOSITION")
  self.assertFalse(r["native_architecture_superiority"])
  self.assertFalse(r["scientific_accepted"])
 def test_require_all_new_original_worlds(self):
  rows,cost,size=synthetic();rows.pop()
  with self.assertRaises(ValueError):verdict(rows,cost,size)
 def test_scientific_action_ablations(self):
  for x in ("native_R7_no_composition","native_R7_no_world_identity",
            "conventional_exhaustive_triple","conventional_greedy_depth3"):
   self.assertIn(x,METHODS)
  self.assertEqual(SCHEMA,"mass.lcrm01.k5e.original-interleaved-nonlinear-causality-v1")
if __name__=="__main__":unittest.main()

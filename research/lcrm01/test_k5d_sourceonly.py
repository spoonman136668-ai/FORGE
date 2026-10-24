"""K5D frozen source-only falsification guards; zero holdout execution."""
import json
import unittest
from k5d_causal_world import CausalSixBitWorld,INPUTS,OPS
from k5d_causal_trial import (SCHEMA,METHODS,PHASE_WORLDS,frozen,
    GF2Conventional,SingleStepNearest,science)

def synthetic():
 raw=[]
 for seed in PHASE_WORLDS["DEV"]:
  for i in range(16):
   raw.append({"seed":seed,"is_correct":{m:m in
    ("ygg_R6_native_composition","conventional_GF2_solver")
    for m in METHODS}})
 cost={m:{"wall_seconds":.001,"queries":64} for m in METHODS}
 sizes={m:200 for m in METHODS}
 return raw,cost,sizes

class K5DSourceOnly(unittest.TestCase):
 def test_original_protocol_preserves_previous(self):
  p=frozen()
  self.assertEqual(p["parent_K5C_head"],"15e18aef3a271c675dd7007fbdb8d869bfc682da")
  self.assertTrue(p["governance"]["preserve_K5C"])
  self.assertEqual(len(set(PHASE_WORLDS["FIT"])|set(PHASE_WORLDS["DEV"])),8)
  self.assertFalse(p["governance"]["scientific_accepted"])
 def test_true_environment_action_is_deterministic(self):
  a=CausalSixBitWorld(901);b=CausalSixBitWorld(901);c=CausalSixBitWorld(902)
  for x in (0,1,13,31,63):
   for act in OPS:
    a.reset(x);b.reset(x)
    self.assertEqual(a.step(act),b.step(act))
  self.assertFalse(all((lambda aa,bb:(aa.reset(x),aa.step(act))[1]==(bb.reset(x),bb.step(act))[1])(a,c)
    for x in range(12) for act in OPS))
 def test_conventional_solver_is_competent_on_novel_compositions(self):
  env=CausalSixBitWorld(923);fit=GF2Conventional()
  for inp in INPUTS:
   for act in OPS:
    env.reset(inp);_,a,after=env.step(act)
    fit.learn("w",a,inp,after)
  env.reset(29)
  for act in (1,0,2,2,0):
   env.step(act)
  self.assertEqual(fit.predict("w",29,(1,0,2,2,0)),env.current())
 def test_predeclared_no_fake_novelty_on_GF2_tie(self):
  raw,cost,size=synthetic()
  x=science(raw,cost,size)
  self.assertEqual(x["result"],"BOUNDED_PUBLIC_CAUSAL_COMPOSITION_LEARNED")
  self.assertFalse(x["native_novelty_established"])
  self.assertFalse(x["scientific_accepted"])
 def test_bad_source_or_missing_world_fails(self):
  raw,cost,size=synthetic()
  with self.assertRaises(ValueError):science(raw[:-1],cost,size)
  self.assertIn("ygg_R6_no_composition",METHODS)
  self.assertIn("conventional_GF2_solver",METHODS)
 def test_cannot_call_world_params_as_native_feature(self):
  self.assertEqual(SCHEMA,"mass.lcrm01.k5d.true-public-causal-composition-v1")
  self.assertEqual(INPUTS,(0,1,2,4,8,16,32))
  self.assertNotIn("latent_permutation",METHODS)
if __name__=="__main__":unittest.main()

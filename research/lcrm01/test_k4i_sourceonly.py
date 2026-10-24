"""K4I source-only tests: no hindsight tuning, heldout control, FIT sufficiency."""
import copy
import json
import unittest
import numpy as np
from k4i_information_sufficiency import (
 load,source_config,partition,information_support,train,predict,choose,
 context_plan,verdict,METHODS,canonical
)

def synthetic(fit_diverse=True):
 p=load();rs=[]
 for family in p["world"]["families"]:
  for v in partition(p,"FIT"):
   for arm in range(4):
    best=(3 if v["goal_dx"]>.0 else 1) if fit_diverse else 1
    rs.append({"family":family,"variant":v["id"],"arm":arm,
      "features":[v["goal_dx"],v["goal_dy"]]+[0.0]*126,
      "initial_observation_sha256":family+":"+str(v["id"]),
      "reward":2.0 if arm==best else 0.0,
      "action_sha256":str(arm),"steps":8})
 return p,rs

class K4IResearchGuards(unittest.TestCase):
 def test_preregistered_symmetric_fit_grid(self):
  p=load();f=partition(p,"FIT")
  self.assertEqual(len(f),12)
  self.assertEqual({v["goal_dx"] for v in f},{-.06,-.02,.02,.06})
  self.assertEqual({v["goal_dy"] for v in f},{-.04,0,.04})
  self.assertEqual(len(partition(p,"CHECK")),2)
  self.assertEqual(len(partition(p,"DEV")),4)
  self.assertFalse(p["governance"]["scientific_first_use"])

 def test_ancestor_public_world_constructor_unmodified(self):
  p=load();world=source_config(p)
  self.assertEqual(world["world"]["seed"],827)
  self.assertEqual(world["world"]["steps"],8)
  self.assertEqual(world["variants"],p["variants"])

 def test_fit_action_support_detects_crossover(self):
  p,rs=synthetic()
  z=information_support(rs,p)
  self.assertEqual(z["reaching"]["best_arm_ids"],[1,3])
  self.assertTrue(z["pushing"]["action_ranking_diverse"])
  self.assertEqual(z["reaching"]["unique_public_FIT_contexts"],12)

 def test_fit_action_support_rejects_noninformative(self):
  p,rs=synthetic(False)
  z=information_support(rs,p)
  self.assertFalse(z["reaching"]["action_ranking_diverse"])
  self.assertEqual(z["pushing"]["best_arm_ids"],[1])

 def test_missing_action_experience_denied(self):
  p,rs=synthetic()
  with self.assertRaises(ValueError):
   information_support(rs[:-1],p)
  with self.assertRaises(ValueError):
   train(np,rs[:-1],p)

 def test_fitted_family_methods_equal_data(self):
  p,rs=synthetic();s=train(np,rs,p)
  for fam in p["world"]["families"]:
   for arm in range(4):
    self.assertEqual(len(s["by_family"][fam]["records"][str(arm)]),12)
    self.assertEqual(len(s["by_family"][fam]["ridge"][str(arm)]),129)
   self.assertEqual(len(s["by_family"][fam]["feature_scale"]),128)

 def test_full_checkpoint_predictions_survive_reload(self):
  p,rs=synthetic();s=train(np,rs,p)
  restored=json.loads(canonical(s))
  for m in METHODS:
   for arm in range(4):
    self.assertEqual(predict(np,s,"reaching",rs[0]["features"],arm,m),
                     predict(np,restored,"reaching",rs[0]["features"],arm,m))

 def test_fixed_low_not_oracle(self):
  p,rs=synthetic();s=train(np,rs,p)
  self.assertEqual(choose(np,s,"pushing",rs[0]["features"],"fixed_low"),0)
  with self.assertRaises(ValueError):
   choose(np,s,"pushing",rs[0]["features"],"oracle")

 def test_plan_from_public_reset_only(self):
  p,rs=synthetic();s=train(np,rs,p)
  contexts=[{"family":"reaching","variant":15,
             "features":[0.045,0.025]+[0.0]*126,
             "initial_observation_sha256":"fresh-public-reset"}]
  plan=context_plan(np,s,p,contexts)
  self.assertEqual(plan[0]["public_observation_sha256"],"fresh-public-reset")
  self.assertEqual(set(plan[0]["choices"]),set(METHODS))
  self.assertNotIn("reward",plan[0])

 def test_learnability_not_claimed_when_fit_diversity_absent(self):
  p,rs=synthetic(False)
  fit=information_support(rs,p)
  self.assertFalse(any(z["action_ranking_diverse"] for z in fit.values()))

 def test_frozen_hyperparameters_not_source_result(self):
  p=load()
  self.assertEqual(p["hyperparameters"],{"ridge_lambda":1,"nearest_neighbors":1,"std_floor":0.05})
  self.assertFalse(p["governance"]["scientific_accepted"])

if __name__=="__main__":
 unittest.main()

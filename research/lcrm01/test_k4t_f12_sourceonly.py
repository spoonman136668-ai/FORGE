"""F12 source-only cases: physical return, true public edge history and parity."""
import unittest
from k4t_f12_physical_return import (
 FIT,DEV,ACTIONS,CATEGORIES,contract,category,graph_features,map_features,
 FullyTrained,choose
)

def public(x=4,direction=0,blocked=False):
 return {"X":x,"Y":5,"GoalX":11,"GoalY":9,
  "Direction":direction,"FrontBlocked":blocked}

def outcome(a):
 return {"intervened_action":a,
  "actual_public_action_consequence_trace":[{"action":a}],
  "discounted_true_source_return":float(a==1)}

def row(i):
 s=public(i%5+4)
 h={"action":2,"physically_moved":True,"front_blocked_before":False,
    "public_before":s,"public_after":public(s["X"]+1)}
 edge=str(s["X"])+","+str(s["Y"])+","+str(s["Direction"])
 return {"six_public_before":s,"witnessed_action_consequence_history":[h],
    "local_forward_edge_counts":{edge:[1,0]},
    "public_history_counts":{"unique_observed_cells":6,
      "reentered_departed_cells":2,"failed_forward_actions":1,
      "ticks_since_last_physical_move":3},
    "true_source_three_arm_interventions":{str(a):outcome(a) for a in ACTIONS}}

class FrozenF12(unittest.TestCase):
 def test_cohorts_protocol(self):
  p=contract()
  self.assertEqual(len(FIT),48)
  self.assertEqual(len(DEV),16)
  self.assertFalse(set(FIT)&set(DEV))
  self.assertFalse(set(DEV)&set(range(161400,161416)))
  self.assertFalse(p["governance"]["scientificAccepted"])
 def test_revisit_requires_actual_reentry_not_heading_change(self):
  s=public()
  self.assertEqual(category(s,5,[],True,set()),"actual_physical_reentry")
  self.assertNotEqual(category(s,5,[],False,{(s["X"],s["Y"])}),"actual_physical_reentry")
  self.assertEqual(category(public(blocked=True),5,[],False,set()),"public_front_blocked")
 def test_local_graph_excludes_unobserved_or_privileged_edges(self):
  r=row(0)
  self.assertEqual(len(graph_features(r)),12)
  self.assertEqual(len(map_features(r,2)),21+12*6+4+12)
  r["local_forward_edge_counts"]={"24,24,0":[2,0]}
  with self.assertRaises(ValueError):graph_features(r)
 def test_false_action_outcome_excluded_and_equal_competitor_fit(self):
  training=[row(i) for i in range(110)]
  x=FullyTrained(training)
  self.assertEqual(x.n,330)
  for model in ("current_ridge","history12_ridge","physical_graph_ridge","graph_empirical","source_action_prior"):
   self.assertIn(choose(x.score(row(0)),model),ACTIONS)
  training[0]["true_source_three_arm_interventions"]["2"]["actual_public_action_consequence_trace"][0]["action"]=0
  with self.assertRaises(ValueError):FullyTrained(training)
if __name__=="__main__":unittest.main()

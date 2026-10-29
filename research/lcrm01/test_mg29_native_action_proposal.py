"""MG29 synthetic-only pre-source negative controls. No original world actions."""
import unittest
from mg29_policy_proposal_proxy import Prefix,observed_context

def scene(mission="pick up the blue ball",direction=0,front=(6,2,0)):
 p={"mission":mission,"direction":direction,
    "image":[[[1,0,0] for _ in range(7)] for _ in range(7)]}
 p["image"][3][5]=list(front)
 return p

class TestMG29(unittest.TestCase):
 def test_frozen_three_support_margin_and_no_future(self):
  p=scene();state=Prefix()
  self.assertIsNone(state.before(p,0)["full_proposal"])
  for _ in range(3):
   state.after(p,2,True,False,False)
  self.assertEqual(state.before(p,0)["full_proposal"],2)
  self.assertEqual(state.before(p,0)["action_only_proposal"],2)
  # The actual source action at the new position is not trained until AFTER.
  self.assertEqual(state.events,3)
  state.after(p,0,True,False,False)
  self.assertEqual(state.events,4)

 def test_weak_support_never_override(self):
  s=Prefix();p=scene()
  for _ in range(2):s.after(p,2,True,False,False)
  self.assertIsNone(s.before(p,0)["full_proposal"])
  self.assertEqual(s.before(p,0)["full_support"],0)

 def test_action_only_does_not_assume_context(self):
  s=Prefix()
  first=scene()
  other=scene("pick up the red box",1,(7,0,0))
  for _ in range(3):s.after(first,2,True,False,False)
  self.assertIsNone(s.before(other,0)["full_proposal"])
  self.assertEqual(s.before(other,0)["action_only_proposal"],2)

 def test_no_cross_mission_or_front_cell_evidence(self):
  s=Prefix();p=scene()
  for _ in range(5):s.after(p,3,True,False,False)
  self.assertIsNone(s.before(scene("pick up the yellow key"),0)["full_proposal"])
  self.assertIsNone(s.before(scene(front=(6,2,1)),0)["full_proposal"])
  self.assertIsNone(s.before(scene(direction=1),0)["full_proposal"])

 def test_only_selected_outcomes_not_hypothetical(self):
  s=Prefix();p=scene()
  with self.assertRaises(ValueError):s.after(p,2,False,True,False)
  with self.assertRaises(ValueError):s.after(p,7,True,False,False)
  self.assertEqual(s.events,0)

 def test_public_invalid_rejected(self):
  p=scene();del p["mission"]
  with self.assertRaises(ValueError):observed_context(p)
  p=scene();p["image"][3][5]=[2,5,300]
  with self.assertRaises(ValueError):observed_context(p)

 def test_context_hash_key_same_only_if_equal(self):
  a=scene();b=scene()
  self.assertEqual(observed_context(a),observed_context(b))
  self.assertNotEqual(observed_context(a),observed_context(scene(front=(5,2,0))))

if __name__=="__main__":unittest.main()

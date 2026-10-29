"""AC-27 independent forensic attribution tests; no original source actions."""
import copy
import json
import unittest
import ac27_mg12_goal_attribution as a

def public():
    return {"image":[[[0,0,0] for _ in range(7)] for _ in range(7)],
            "direction":0,"mission":"use the key"}

class AC27OriginalSourceAttribution(unittest.TestCase):
    def test_original_public_only_and_no_private_pose(self):
        valid=public()
        self.assertEqual(len(a.verify_public(valid)),64)
        x=copy.deepcopy(valid);x["agent_pos"]=[1,2]
        with self.assertRaisesRegex(RuntimeError,"AC27_PRIVATE_OR_FORGED_PUBLIC_VISUAL"):
            a.verify_public(x)
        x=copy.deepcopy(valid);x["image"][2][3][0]=True
        with self.assertRaisesRegex(RuntimeError,"AC27_PRIVATE_OR_FORGED_PUBLIC_VISUAL"):
            a.verify_public(x)
        x=copy.deepcopy(valid);x["direction"]=False
        with self.assertRaisesRegex(RuntimeError,"AC27_PRIVATE_OR_FORGED_PUBLIC_VISUAL"):
            a.verify_public(x)

    def test_canonical_sha_is_crossplatform_binary_json(self):
        x=public()
        self.assertEqual(a.sha(a.canonical(x)),a.verify_public(x))
        self.assertEqual(a.SOURCE_SHA,
           "4c5b48288f1d8c61561527da5b4f0767c220d06d3f1fbeaf07f27b3d8ca6675c")
        self.assertEqual(a.FIT_SHA,
           "9c640b0ae6a0865b9db7147d4b816643962ee69141950e7639dcc09b832d0e24")

    def test_source_parent_forgery_rejected_before_goal_attribution(self):
        with self.assertRaisesRegex(RuntimeError,"AC27_MG12_PARENT_QUALIFICATION_FAILED"):
            a.verify_parent({}, {}, {})
        x={"schema":"itd02.mg12.original-public-successor-persistence-world.v1",
           "classification":a.EXPECTED_CLASS,"scientific_first_use":False,
           "external_live_actions":0,"original_episode_count":12,
           "accepted_native_model_promoted":False}
        c={"schema":"itd02.mg12.two-process-selected-original-evidence.v1",
           "classification":a.EXPECTED_CLASS,
           "two_independent_fresh_original_source_processes":True,
           "selected_source_actions_not_external":True,
           "equal_policy_public_observation":True,
           "scientific_first_use":False}
        with self.assertRaisesRegex(RuntimeError,"AC27_ORIGINAL_SOURCE_EVIDENCE_MISSING"):
            a.verify_parent(x,x,c)

    def test_action_equality_requires_full_source_episode(self):
        def event(act,old,new):
            return {"actual_original_source_action":act,
                    "original_public_before_sha256":old,
                    "original_public_after_sha256":new}
        x={"real_source_events":[event(1,"a","b"),event(2,"b","c")]}
        y={"real_source_events":[event(1,"a","b"),event(2,"b","c")]}
        r=a.comparison_replay(x,y)
        self.assertEqual(r["action_disagreements"],0)
        self.assertTrue(r["complete_original_selected_episode_identical"])
        y["real_source_events"][1]["actual_original_source_action"]=3
        r=a.comparison_replay(x,y)
        self.assertEqual(r["action_disagreements"],1)
        self.assertFalse(r["complete_original_selected_episode_identical"])
        z={"real_source_events":[event(1,"a","b")]}
        r=a.comparison_replay(x,z)
        self.assertEqual(r["aligned_source_action_steps"],1)
        self.assertFalse(r["episode_lengths_equal"])
        self.assertFalse(r["complete_original_selected_episode_identical"])

    def test_no_implicit_synthetic_sourced_goals(self):
        with self.assertRaisesRegex(RuntimeError,"AC27_UNREGISTERED_SELECTED_SOURCE_EPISODE"):
            a.verify_record({"role":"wingless_dk13","seed_evaluator_only":72307,
                             "original_live_selected_steps":1,
                             "real_source_events":[{"source_reward":1,"agent_pos":[1,2]}]})
        self.assertEqual(a.SEEDS,(72301,72303,72307))
        self.assertEqual(a.ROLES,("wingless_dk13","yggdrasil_r17",
          "conventional_public_successor","random"))

if __name__=="__main__":
    unittest.main()

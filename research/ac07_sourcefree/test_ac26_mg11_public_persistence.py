"""AC-26 focused source-free tests of actual online-safe public graph accounting."""
import copy
import unittest
import ac26_mg11_public_persistence as m

def public(direction=0):
    return {"image":[[[0,0,0] for _ in range(7)] for _ in range(7)],
            "direction":direction,"mission":"reach the goal"}

class AC26PublicPersistenceTests(unittest.TestCase):
    def test_original_public_source_only_and_no_privileged_pose(self):
        a=public(0);b=public(1)
        self.assertNotEqual(m.verify_public(a),m.verify_public(b))
        q=copy.deepcopy(a);q["agent_pos"]=[1,2]
        with self.assertRaisesRegex(RuntimeError,"AC26_INVALID_OR_PRIVILEGED_PUBLIC_VISUAL_INPUT"):
            m.verify_public(q)
        q=copy.deepcopy(a);q["image"][0][0][0]=False
        with self.assertRaisesRegex(RuntimeError,"AC26_INVALID_OR_PRIVILEGED_PUBLIC_VISUAL_INPUT"):
            m.verify_public(q)
        q=copy.deepcopy(a);q["direction"]="0"
        with self.assertRaisesRegex(RuntimeError,"AC26_INVALID_OR_PRIVILEGED_PUBLIC_VISUAL_INPUT"):
            m.verify_public(q)

    def test_changed_view_is_not_persistent_novel_successor(self):
        a=m.verify_public(public(0));b=m.verify_public(public(1))
        g=m.PublicGraphObserver(a)
        first=g.learn_selected(a,5,b)
        self.assertTrue(first["changed"] and first["novel"])
        second=g.learn_selected(b,5,a)
        self.assertTrue(second["changed"] and second["revisited"])
        self.assertTrue(second["reverse"] and second["immediate_reversal"])
        third=g.learn_selected(a,5,b)
        self.assertTrue(third["changed"] and third["revisited"])
        self.assertTrue(third["reverse"] and third["immediate_reversal"])
        self.assertEqual(g.counts["public_changed"],3)
        self.assertEqual(g.counts["novel_public_successor"],1)
        self.assertEqual(g.counts["changed_successor_already_seen"],2)
        self.assertEqual(g.counts["immediate_two_step_reversal"],2)
        self.assertEqual(g.counts["repeated_same_selected_public_transition"],1)

    def test_no_source_action_decision_and_strict_continuity(self):
        a=m.verify_public(public(0));b=m.verify_public(public(1))
        g=m.PublicGraphObserver(a)
        with self.assertRaisesRegex(RuntimeError,"AC26_PUBLIC_CONTINUITY_STATE_ABSENT"):
            g.learn_selected(b,5,a)
        self.assertFalse(hasattr(g,"choose"))
        self.assertFalse(hasattr(g,"act"))
        self.assertFalse(hasattr(g,"reward"))
        self.assertEqual(g.learn_selected(a,0,a)["novel"],False)

    def test_original_two_process_custody_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError,"AC26_ORIGINAL_MG11_PARENT_NEGATIVE_NOT_QUALIFIED"):
            m.verify_two_processes({}, {}, {})
        good={"schema":"itd02.mg11.authentic-original-public-nonrotational-motion.v1",
          "classification":"MG11_ORIGINAL_NATIVE_GOALS_NOT_BOTH_ESTABLISHED__NO_SCIENCE",
          "original_episode_count":12,"external_live_actions":0,
          "scientific_first_use":False,"accepted_native_model_promoted":False}
        with self.assertRaisesRegex(RuntimeError,"AC26_TWO_PROCESS_CANONICAL_SOURCE_CUSTODY_FAILED"):
            m.verify_two_processes(good,good,{})

    def test_predeclared_native_roles_and_cohorts(self):
        self.assertEqual(len(m.ROLES)*len(m.SEEDS),12)
        self.assertEqual(m.SEEDS,(71301,71303,71307))
        self.assertEqual(m.CANON_SHA,
          "84e93a1cc86addfc27622ea860eac9ea7c6d4b3cfec02ec3e01e04d56b475ba2")
        self.assertEqual(m.SOURCE_FARAMA,
          "7f5853792ea7f04f75614661006d87fcf949f26d")

if __name__=="__main__":
    unittest.main()

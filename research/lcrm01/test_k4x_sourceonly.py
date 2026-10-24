"""K4X focused source-only freeze, causal protocol and leakage guards."""
import json
import pathlib
import unittest
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import k4x_synthetic_credit as k

class PublicGrid:
    def __init__(self,x,y,goal_x,goal_y,direction,front_blocked):
        self.x=x
        self.y=y
        self.goal_x=goal_x
        self.goal_y=goal_y
        self.direction=direction
        self.front_blocked=front_blocked
class PublicNative:
    PublicGrid=PublicGrid

class K4XProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=json.loads(k.FREEZE.read_text())
    def test_source_only_gates(self):
        self.assertEqual(self.p["world"]["synthetic_fit_episodes"],576)
        self.assertEqual(self.p["world"]["synthetic_eval_episodes"],128)
        self.assertTrue(self.p["no_scientific_first_use"])
        self.assertTrue(self.p["no_Yggdrasil_modification"])
        self.assertEqual(self.p["sources"]["yggdrasil_native_commit"],
            "1b042d6bf4832d885d80ef73f3ab29d8a600bfe2")
    def test_schedule_role_separation(self):
        fit=k.schedule(self.p,"FIT")
        test=k.schedule(self.p,"TEST")
        self.assertEqual(len(fit),576)
        self.assertEqual(len(test),128)
        self.assertEqual(set(x for x,_ in fit),{2,6})
        self.assertEqual(set(x for x,_ in test),{3,7})
        self.assertTrue(set(x for x,_ in fit).isdisjoint(set(x for x,_ in test)))
    def test_balanced_public_executed_actions(self):
        fit=k.schedule(self.p,"FIT")
        for x in (2,6):
            for a in (0,1,2):
                self.assertEqual(fit.count((x,a)),96)
    def test_synthetic_reward_delayed_only_on_real_selected_action(self):
        for x in (2,3,6,7):
            for a in (0,1,2):
                rows=k.synthetic(PublicNative,x,a)
                self.assertEqual([r[1] for r in rows],[a,2,2])
                self.assertEqual([r[3] for r in rows[:2]],[0.,0.])
                self.assertEqual([r[4] for r in rows],[False,False,True])
                self.assertEqual(rows[-1][3],float(a==k.target(x)))
    def test_source_only_role_and_invalid_action_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"UNQUALIFIED_ROLE"):
            k.schedule(self.p,"DEV")
        with self.assertRaisesRegex(ValueError,"ILLEGAL_ACTION"):
            k.synthetic(PublicNative,2,3)
        with self.assertRaisesRegex(ValueError,"UNDECLARED_CONTEXT"):
            k.target(4)
    def test_tabular_trace_not_expert_planner(self):
        m=k.TabularTrace(.9)
        for _ in range(3):
            m.train(2,0,1)
            m.train(6,1,1)
            m.train(2,1,0)
            m.train(6,0,0)
            m.train(2,2,0)
            m.train(6,2,0)
        self.assertEqual(m.choose(3),0)
        self.assertEqual(m.choose(7),1)
    def test_frozen_no_simulator_dependency(self):
        import ast
        src=pathlib.Path(k.__file__).read_text()
        tree=ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                self.assertTrue(all(not alias.name.startswith("minigrid") for alias in node.names))
            if isinstance(node,ast.ImportFrom) and node.module:
                self.assertFalse(node.module.startswith("minigrid"))
if __name__=="__main__":
    unittest.main()

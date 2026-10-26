"""Fixture-only statistical episode tests; no original-world execution."""
import unittest
from unittest.mock import patch
import itd02_r8_statistical_episode as subject
from itd02_r8_conditional_beta import ConditionalBeta
from itd02_r8_previous_action_ablation import PreviousActionAblatedBeta

class FakeEnv:
    def __init__(self):self.closed=False
    def reset(self,seed):return {"tick":0},{}
    def step(self,action):return {"tick":1},1.0,True,False,{}
    def close(self):self.closed=True

class StatisticalEpisodeTest(unittest.TestCase):
    def test_both_methods(self):
        for method,model in (("independent_conditional_beta",ConditionalBeta()),
                             ("r8_previous_action_ablated",PreviousActionAblatedBeta())):
            env=FakeEnv()
            def pub(obs,goal=None):
                return {"tick":obs["tick"],"goal":(5,5),"grid_sha256":"fixture"}
            with patch.object(subject,"make_env",return_value=env),patch.object(subject,"public",side_effect=pub),patch.object(subject,"public_grid",side_effect=lambda s:{"FrontBlocked":False}):
                row=subject.run_statistical_episode("empty",82400,model,lambda state:2,method)
            self.assertEqual(row["steps"],1)
            self.assertTrue(row["success"])
            self.assertTrue(env.closed)
            self.assertEqual(row["trace"][0]["action"],2)
    def test_invalid_method_prevents_reset(self):
        with patch.object(subject,"make_env") as env:
            with self.assertRaises(ValueError):
                subject.run_statistical_episode("empty",82400,ConditionalBeta(),lambda s:2,"unknown")
            env.assert_not_called()

if __name__=="__main__":unittest.main()

"""Fixture-only R8 original episode adapter tests; never starts MiniGrid."""
import unittest
from unittest.mock import patch
import itd02_r8_original_episode as subject

class FakeBridge:
    def __init__(self): self.steps=0
    def request(self,operation,**kwargs):
        if operation=="episode_start": self.steps=0; return {"ok":True}
        if operation=="choose": return {"action":2}
        if operation=="feedback":
            self.steps+=1
            return {"steps":self.steps}
        raise AssertionError(operation)

class FakeEnv:
    closed=False
    def reset(self,seed):
        self.seed=seed
        return {"state":0},{}
    def step(self,action):
        assert action==2
        return {"state":1},1.0,True,False,{}
    def close(self):self.closed=True

class OriginalEpisodeFixtureTest(unittest.TestCase):
    def test_trace_and_custody(self):
        env=FakeEnv()
        def pub(obs,goal=None):
            return {"grid_sha256":"fixed","goal":(5,5),"state":obs["state"]}
        with patch.object(subject,"make_env",return_value=env),patch.object(subject,"public",side_effect=pub),patch.object(subject,"public_grid",side_effect=lambda s:s),patch.object(subject,"wingless_wire_grid",side_effect=lambda s:s):
            row=subject.run_episode("empty",82400,"wingless_r8_online_beliefs",FakeBridge())
        self.assertTrue(row["success"])
        self.assertEqual(row["steps"],1)
        self.assertEqual(row["real_total_reward"],1.0)
        self.assertTrue(env.closed)
        self.assertEqual(row["trace"][0]["action"],2)
    def test_reject_fit_before_env_creation(self):
        with patch.object(subject,"make_env") as env:
            with self.assertRaises(ValueError):
                subject.run_episode("empty",81400,"wingless_r8_online_beliefs",FakeBridge())
            env.assert_not_called()

if __name__=="__main__": unittest.main()

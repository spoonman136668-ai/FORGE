"""MG01 public-only, exact Go JSON, independently sourced MiniGrid boundary."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from mg01_paired_live_minigrid import (
    protocol,exact,public_wire,canonical_from_k4u,colony_input,
    verify_go_wire,SCHEMA,FIELDS,NATIVE_TYPES,FAMILIES,SEEDS
)
from k4r_minigrid_source import make_env,public
from k4u_native_minigrid import WingBridge


class MG01PublicOnlyTests(unittest.TestCase):
    def test_prereg_before_code_and_original_sources_unmodified(self):
        p=protocol()
        self.assertEqual(p["scope"],"SOURCE_ONLY_ENGINEERING_CONNECTIVITY_NOT_SCIENCE_OR_MODEL_PROMOTION")
        self.assertEqual(len(NATIVE_TYPES),2)
        self.assertEqual(FAMILIES,("empty","fourrooms"))
        self.assertEqual(SEEDS,(9200,9201))
        self.assertEqual(SCHEMA,"itd02.mg01.paired-authentic-minigrid-live-native.v1")
        self.assertFalse(p["authority"]["original_models_modified"])
        self.assertEqual(p["parent"]["PR"],877)

    def test_strict_sixfield_canonical_not_k4u_camel(self):
        valid={"x":3,"y":4,"goal_x":6,"goal_y":7,"direction":2,"front_blocked":True}
        self.assertEqual(exact(valid),valid)
        with self.assertRaises(ValueError):
            exact({"X":3,"Y":4,"GoalX":6,"GoalY":7,"Direction":2,
                   "FrontBlocked":True})
        for k in FIELDS:
            invalid=dict(valid);invalid.pop(k)
            with self.assertRaises(ValueError):
                exact(invalid)
        for k in ("x","y","goal_x","goal_y","direction"):
            invalid=dict(valid);invalid[k]=False
            with self.assertRaises(ValueError):exact(invalid)
        invalid=dict(valid);invalid["front_blocked"]=1
        with self.assertRaises(ValueError):exact(invalid)
        invalid=dict(valid);invalid["world"]="D1"
        with self.assertRaises(ValueError):exact(invalid)
        self.assertEqual(canonical_from_k4u({
            "X":3,"Y":4,"GoalX":6,"GoalY":7,"Direction":2,"FrontBlocked":True}),valid)

    def test_both_native_interfaces_receive_same_canonical_public_values(self):
        import native_policy
        fields={"x":3,"y":4,"goal_x":6,"goal_y":7,"direction":2,"front_blocked":True}
        ygg=colony_input(native_policy,fields)
        self.assertEqual(tuple(vars(ygg).keys()),FIELDS)
        self.assertTrue(ygg.front_blocked)
        self.assertEqual((ygg.goal_x,ygg.goal_y),(6,7))
        e=os.environ.get("MG01_WINGLESS_BRIDGE","")
        self.assertTrue(e, "MG01 must test real compiled original Go binary")
        w=WingBridge(e)
        try:
            verify_go_wire(w,fields)
            ans=w.request("public_echo",before=fields)
            self.assertEqual(ans["public"],fields)
            with self.assertRaises(ValueError):
                w.request("public_echo",before={
                    "X":3,"Y":4,"GoalX":6,"GoalY":7,
                    "Direction":2,"FrontBlocked":True})
            with self.assertRaises(ValueError):
                w.request("public_echo",before={**fields,"hidden_grid":[]})
        finally:
            w.close()

    def test_genuine_original_minigrid_same_seed_identical_initial_public(self):
        # Tests REAL original Farama env.reset, not a self-authored stand-in.
        for family in FAMILIES:
            for seed in SEEDS:
                before=[]
                for _ in range(2):
                    env=make_env(family)
                    try:
                        obs,_=env.reset(seed=seed)
                        st=public(obs)
                        native=public_wire(st)
                        self.assertEqual(set(native),set(FIELDS))
                        before.append((st["grid_sha256"],native))
                    finally:env.close()
                self.assertEqual(before[0],before[1])
    
    def test_real_step_and_original_reward_action_feedback(self):
        for family in FAMILIES:
            env=make_env(family)
            try:
                obs,_=env.reset(seed=SEEDS[0])
                st=public(obs)
                before=public_wire(st)
                next_obs,r,t,tr,_=env.step(0)
                after=public(next_obs,st["goal"])
                next_wire=public_wire(after)
                self.assertEqual(set(before),set(next_wire))
                self.assertIsInstance(r,(int,float))
                self.assertIsInstance(t,bool)
                self.assertIsInstance(tr,bool)
            finally:env.close()

if __name__=="__main__":
    unittest.main()

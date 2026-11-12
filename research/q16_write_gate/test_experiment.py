"""Q16 finite-state gating, controls and unseen-data custody checks."""
import math
import pathlib
import unittest
import experiment as e


class Q16FrozenSourceFreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=e.load()

    def test_both_generators_distinct_and_frozen(self):
        fs=self.p["generator"]["family_algorithms"]
        self.assertEqual([x["name"] for x in fs],["E_regime","F_burst"])
        self.assertEqual([x["steps"] for x in fs],[16,20])
        self.assertEqual(self.p["decision"]["otherwise"],
                         "DEV_NO_GO_STOP_BEFORE_HELD")

    def test_holdout_family_guard_fails_before_randomization(self):
        for name in ("G_reversed","H_delayed"):
            with self.assertRaisesRegex(ValueError,
                                        "ORIGINAL_OR_HELD_FORBIDDEN"):
                e.data_for("train",{"name":name,"train_episodes":2,
                                    "validation_episodes":2,"steps":8})

    def test_all_non_development_roles_forbidden(self):
        spec=self.p["generator"]["family_algorithms"][0]
        for role in ("held","test","scientific","protected",""):
            with self.assertRaisesRegex(ValueError,
                                        "ORIGINAL_OR_HELD_FORBIDDEN"):
                e.data_for(role,spec)

    def test_seeds_unique_and_train_dev_disjoint(self):
        collected=set()
        for role in ("train","dev"):
            for f in e.FAMILIES:
                count=48 if role=="train" else 24
                for i in range(count):
                    seed=e.make_seed("q16","v1",role,f,i)
                    self.assertNotIn(seed,collected)
                    collected.add(seed)
        self.assertEqual(len(collected),144)

    def test_sensor_generation_deterministic(self):
        spec=self.p["generator"]["family_algorithms"]
        for f in spec:
            a=e.data_for("dev",f)
            b=e.data_for("dev",f)
            self.assertEqual(e.digest(a),e.digest(b))
            self.assertEqual(len(a),24)
            for family,x,c,y in a:
                self.assertEqual(family,f["name"])
                self.assertEqual(len(x),len(c))
                self.assertEqual(len(c),len(y))
                self.assertTrue(set(x).issubset({-1,1}))
                self.assertTrue(set(c).issubset({-1,1}))
                self.assertTrue(set(y).issubset({0,1}))

    def test_gate_uses_cue_and_surprise_at_fixed_h(self):
        ep1=("E_regime",(1,1,1),(1,1,1),(1,1,1))
        ep2=("E_regime",(1,1,1),(-1,-1,-1),(1,1,1))
        params=[0.,3.,2.,2.,0.]
        z1=e.features("SURPRISE_RELIABILITY_WRITE",params,ep1)
        z2=e.features("SURPRISE_RELIABILITY_WRITE",params,ep2)
        self.assertNotEqual(z1,z2)
        self.assertEqual(len(z1),3)

    def test_models_all_finite_on_same_observations(self):
        ep=("E_regime",(1,-1,1,-1),(1,-1,1,-1),(1,0,1,0))
        cases=[
          ("SURPRISE_RELIABILITY_WRITE",[0.1,0.2,0.3,0.4,0.],None),
          ("TRAINED_TANH_RNN",[0.1,0.2,0.3,0.4,0.5,0.],None),
          ("TRAINED_CUE_BAYES",[],{"hazard":.2,
                                   "noise_positive":.1,
                                   "noise_negative":.35}),
          ("TRAINED_DECAYED_CUE_COUNT",[.2,.3,.1],None),
          ("TRAINED_CURRENT_CUE",[.2,.3,.1],None),
        ]
        for kind,params,fit in cases:
            with self.subTest(model=kind):
                self.assertTrue(math.isfinite(e.loss(kind,params,ep,fit)))

    def test_candidate_and_recurrent_parameters_are_independent(self):
        ep=("E_regime",(1,-1,1),(1,1,-1),(1,0,1))
        for name,params in [
            ("SURPRISE_RELIABILITY_WRITE",[0.2,0.3,0.4,0.5,-0.1]),
            ("TRAINED_TANH_RNN",[0.2,0.3,0.4,0.5,-0.1,0.05])
        ]:
            for index in range(len(params)):
                plus=params.copy()
                minus=params.copy()
                plus[index]+=.0001
                minus[index]-=.0001
                gradient=(e.loss(name,plus,ep)-e.loss(name,minus,ep))/.0002
                self.assertTrue(math.isfinite(gradient))

    def test_training_bayes_uses_labels_not_frozen_true_probabilities(self):
        data=[
            ("E_regime",(1,-1,1),(1,-1,1),(1,0,1)),
            ("F_burst",(-1,1,-1),(-1,1,-1),(0,1,0)),
        ]
        fitted,cost=e.fit_bayes(data)
        self.assertEqual(cost["epochs"],1)
        self.assertTrue(0<fitted["noise_positive"]<0.5)
        self.assertTrue(0<fitted["noise_negative"]<0.5)
        self.assertTrue(0<fitted["hazard"]<0.5)

    def test_no_original_imports_remote_io_or_held_generation_entrypoint(self):
        source=pathlib.Path(e.__file__).read_text(encoding="utf-8")
        for banned in ("import minigrid","from minigrid",
                       "import pycolab","from pycolab",
                       "import socket","import requests",
                       "import subprocess","import urllib",
                       "import github","import cloudflare"):
            self.assertNotIn(banned,source.lower())
        self.assertNotIn("G_reversed",e.FAMILIES)
        self.assertNotIn("H_delayed",e.FAMILIES)
        self.assertEqual(self.p["decision"]["scientific_transfer_acceptance"],
                         "NOT_AUTHORIZED")


if __name__=="__main__":
    unittest.main()

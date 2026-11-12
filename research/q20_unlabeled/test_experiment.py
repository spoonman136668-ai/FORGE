"""Q20 adversarial tests: no hidden-state training labels or protected sources."""
import math
import pathlib
import unittest
import experiment as q

class Q20NoLatentLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=q.protocol()
        cls.fit,cls.fit_private=q.generate("fit",cls.p)
        cls.dev,cls.dev_private=q.generate("dev",cls.p)

    def test_frozen_protocol_before_source(self):
        self.assertEqual(q.BLOB,"b517e5fc03680bdd04ec357e6d84ebdf3cb3b4c8")
        self.assertEqual(self.p["training"]["epochs"],14)
        self.assertEqual(self.p["training"]["hmm_em_epochs"],12)
        self.assertEqual(self.p["training"]["restarts"],[0,1])

    def test_train_dev_sources_are_new_and_separate(self):
        self.assertEqual(len(self.fit),192)
        self.assertEqual(len(self.dev),64)
        self.assertEqual({x[0] for x in self.fit},{"FIT_L1","FIT_L2"})
        self.assertEqual({x[0] for x in self.dev},{"DEV_L3","DEV_L4"})
        self.assertNotEqual(q.digest(self.fit),q.digest(self.dev))

    def test_no_held_or_original_generation_even_for_known_string(self):
        for role in ("held","HELD_NEW_SENSOR_FAMILY",
                     "HELD_LONG_HORIZON_TRANSFER","original","scientific",""):
            with self.subTest(role=role):
                with self.assertRaisesRegex(RuntimeError,
                                            "UNKNOWN_OR_HELD_ROLE_FORBIDDEN"):
                    q.generate(role,self.p)

    def test_replay_deterministic_with_distinct_episode_seeds(self):
        replay,_=q.generate("fit",self.p)
        self.assertEqual(q.digest(replay),q.digest(self.fit))
        self.assertNotEqual(q.initial_seed("q20","v1","fit","FIT_L1",0),
                            q.initial_seed("q20","v1","dev","DEV_L3",0))

    def test_public_data_contains_no_hidden_labels(self):
        for row in self.fit[:10]:
            self.assertEqual(len(row),3)
            fam,obs,actions=row
            self.assertEqual(len(obs),13)
            self.assertEqual(len(actions),12)
            self.assertTrue(all(isinstance(x,tuple) and len(x)==2 for x in obs))
            self.assertTrue(all(set(x).issubset({0,1}) for x in obs))
            self.assertTrue(set(actions).issubset({0,1}))
            self.assertEqual(type(fam),str)
        self.assertEqual(len(self.fit_private),len(self.fit))

    def test_candidate_permutation_equivariance(self):
        row=self.fit[0]
        swapped=(row[0],tuple((b,a) for a,b in row[1]),row[2])
        params=[.2,-.1,.3,.2,.1,.05,0.,.8,-.1]
        a=q.model_predictions(q.CAND,params,row)
        b=q.model_predictions(q.CAND,params,swapped)
        for x,y in zip(a,b):
            self.assertAlmostEqual(x[0],y[1],places=14)
            self.assertAlmostEqual(x[1],y[0],places=14)

    def test_all_empirical_arms_use_same_next_observation(self):
        row=self.fit[1]
        arms=[(q.CAND,[.1]*9),(q.RNN,[.1]*16),(q.FLAT,[.1]*12),
              (q.SYM,[[[.25]*4 for _ in range(4)] for _ in range(2)]),
              (q.HMM,q.hmm_init(0))]
        for name,p in arms:
            with self.subTest(name=name):
                pred=q.model_predictions(name,p,row)
                self.assertEqual(len(pred),12)
                self.assertTrue(all(len(x)==2 and
                                    all(math.isfinite(y) and 0<y<1 for y in x)
                                    for x in pred))

    def test_symbolic_fits_public_joint_observation_counts(self):
        model,receipt=q.train_symbolic(self.fit)
        self.assertEqual(receipt["calibrated_action_state_contexts"],8)
        for block in model:
            self.assertEqual(len(block),4)
            for row in block:
                self.assertEqual(len(row),4)
                self.assertAlmostEqual(sum(row),1.0,places=12)

    def test_hmm_trains_only_from_visible_obs_action_sequences(self):
        d=q.hmm_init(1)
        result=q.hmm_em_step(d,self.fit[:4],.5)
        self.assertAlmostEqual(sum(result["prior"]),1.0)
        for t in result["transition"]:
            for row in t:
                self.assertAlmostEqual(sum(row),1.0)
                self.assertTrue(all(0<v<1 for v in row))
        for row in result["emission"]:
            self.assertAlmostEqual(sum(row),1.0)
            self.assertTrue(all(v>0 for v in row))

    def test_privileged_oracle_is_separate_and_marked(self):
        scores=q.privileged_oracle_forecasts(self.dev[0],self.dev_private[0])
        self.assertEqual(len(scores),12)
        self.assertTrue(all(len(x)==2 for x in scores))
        self.assertTrue(self.p["models"]["oracle"]["privileged"])
        self.assertFalse(self.p["boundaries"]["not_scientific_transfer_acceptance"] is False)

    def test_train_labels_are_only_next_public_bits(self):
        self.assertEqual(self.p["models"]["candidate"]["objective"],
                         "FIT-only next observed bit crossentropy; no latent state labels")
        self.assertTrue(self.p["boundaries"]["sourcefree_synthetic_only"])
        self.assertTrue(self.p["boundaries"]["no_CKB_controller_dispatch_or_unpause"])

    def test_numerical_finite_difference_fixed_source(self):
        episodes=self.fit[:3]
        for name,params in ((q.CAND,[.1]*9),(q.FLAT,[.1]*12),
                            (q.RNN,[.1]*16)):
            with self.subTest(name=name):
                hi=params[:];lo=params[:]
                hi[0]+=.0001;lo[0]-=.0001
                val=(q.empirical_loss(name,hi,episodes)-
                     q.empirical_loss(name,lo,episodes))/.0002
                self.assertTrue(math.isfinite(val))

    def test_no_real_original_network_or_disclosed_secrets_in_inference(self):
        text=pathlib.Path(q.__file__).read_text().lower()
        for term in ("import minigrid","import pycolab",
                     "import subprocess","import requests","import socket",
                     "import cloudflare","import urllib","import github"):
            self.assertNotIn(term,text)
        self.assertNotIn("responsive",q.model_predictions.__code__.co_varnames)
        self.assertNotIn("secret",q.empirical_loss.__code__.co_varnames)

if __name__=="__main__":
    unittest.main()

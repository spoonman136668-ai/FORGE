"""O7 public-only source custody, representation ablations and trained controls."""
import hashlib
import math
import unittest

from public_source import (
    FAMILIES,ROLES,ROLE_COUNTS,STEPS,PublicSourceRefused,
    episode,episodes,seed,digest,public_examples,
)
from predictive_partition import (
    CAPACITIES,PredictivePartition,FixedPublicCounts,PublicLogistic,
    public_score,
)
from runner import ARMS,fit_select,frozen_protocol


class O7PredictiveRepresentationTests(unittest.TestCase):
    def test_frozen_source_and_model_inventory(self):
        p=frozen_protocol()
        self.assertEqual(tuple(p["models"]),ARMS)
        self.assertEqual(p["episodes_per_family"],ROLE_COUNTS)
        self.assertEqual(p["steps_per_episode"],32)
        self.assertEqual(p["decision"]["cross_os"].startswith("Every family/role"),True)

    def test_fresh_roles_are_public_binary_and_disjoint(self):
        for family in FAMILIES:
            role_hashes=[]
            for role in ROLES:
                batch=episodes(role,family)
                self.assertEqual(len(batch),ROLE_COUNTS[role])
                self.assertEqual(len(batch[0]),STEPS)
                self.assertTrue(all(len(row)==3 and
                                    all(type(bit) is int and bit in (0,1)
                                        for bit in row)
                                    for ep in batch for row in ep))
                self.assertTrue(all(ep[i][2]==ep[i+1][0]
                                    for ep in batch for i in range(STEPS-1)))
                role_hashes.append(digest(batch))
            self.assertEqual(len(set(role_hashes)),3)

    def test_protected_and_previous_experiment_roles_fail_closed(self):
        for role in ("FIT_TRAIN","FIT_VALID","DEV","HELD","ORIGINAL",
                     "O6_PUBLIC_DEV","O5_PUBLIC_TRAIN","Q21N01_FIT_TRAIN"):
            with self.assertRaises(PublicSourceRefused):
                episode(role,FAMILIES[0],0)
        for idx in (-1,96,True,"1",1.0):
            with self.assertRaises(PublicSourceRefused):
                seed("O7_TRAIN",FAMILIES[0],idx)

    def test_public_history_feature_follows_current_not_future(self):
        ep=((0,1,1),(1,0,0),(0,1,0))
        rows=public_examples((ep,))
        self.assertEqual(rows[0],((0,1,0,0,0,0),1))
        self.assertEqual(rows[1],((1,0,0,1,0,0),0))
        self.assertEqual(rows[2],((0,1,1,0,0,1),0))

    def test_supervised_partition_discovers_predictive_split(self):
        examples=[]
        for i in range(256):
            x=(i%2,(i//2)%2,(i//4)%2,(i//8)%2,0,0)
            examples.append((x,i%2))
        m=PredictivePartition(2)
        m.fit(tuple(examples))
        self.assertEqual(len(m.nodes),2)
        self.assertEqual({path[0] for path in [n["path"] for n in m.nodes]},
                         {(0,0),(0,1)})
        self.assertLess(m.predict_feature((0,0,0,0,0,0)),0.1)
        self.assertGreater(m.predict_feature((1,0,0,0,0,0)),0.9)

    def test_random_topology_control_same_data_capacity_and_budget(self):
        train=public_examples(episodes("O7_TRAIN",FAMILIES[0])[:12])
        for randomized in (False,True):
            m=PredictivePartition(8,randomized)
            m.fit(train)
            self.assertLessEqual(len(m.nodes),8)
            self.assertEqual(m.updates,len(train))
            self.assertTrue(all(node["n"]>=64 for node in m.nodes))
            self.assertTrue(math.isfinite(public_score(
                m,episodes("O7_SELECT",FAMILIES[0])[:2])))

    def test_full_capacity_variants_fit_identical_public_train(self):
        examples=public_examples(episodes("O7_TRAIN",FAMILIES[1])[:8])
        results=[]
        for indices,name in (((0,1),"CURRENT_ONLY_COUNTS"),
                             ((0,1,2),"FIXED_FIRST3_PARTITION"),
                             ((0,1,2,3,4,5),"FULL_SIX_FEATURE_COUNTS")):
            m=FixedPublicCounts(indices,name)
            m.fit(examples)
            self.assertEqual(m.updates,len(examples))
            self.assertTrue(all(0<v<1 for v in m.predict(
                episodes("O7_SELECT",FAMILIES[1])[0])))
            results.append(m.checkpoint())
        self.assertEqual(len(set(results)),3)

    def test_logistic_is_fitted_and_dev_does_not_train(self):
        train=public_examples(episodes("O7_TRAIN",FAMILIES[0])[:6])
        m=PublicLogistic()
        before=m.checkpoint()
        m.fit(train)
        self.assertNotEqual(before,m.checkpoint())
        self.assertEqual(m.updates,20*len(train))
        frozen=m.checkpoint()
        loss=public_score(m,episodes("O7_DEV",FAMILIES[0])[:2])
        self.assertTrue(math.isfinite(loss))
        self.assertEqual(frozen,m.checkpoint())

    def test_all_eight_arms_fit_with_select_only_and_dev_frozen(self):
        tr=episodes("O7_TRAIN",FAMILIES[1])[:8]
        sel=episodes("O7_SELECT",FAMILIES[1])[:2]
        dev=episodes("O7_DEV",FAMILIES[1])[:2]
        for arm in ARMS:
            with self.subTest(arm=arm):
                model,meta=fit_select(arm,tr,sel)
                self.assertGreater(model.updates,0)
                self.assertTrue(math.isfinite(meta["selection_nll"]))
                cp=model.checkpoint()
                self.assertTrue(math.isfinite(public_score(model,dev)))
                self.assertEqual(cp,model.checkpoint())

    def test_development_sources_are_deterministic_and_new(self):
        for f in FAMILIES:
            self.assertEqual(episode("O7_TRAIN",f,0),episode("O7_TRAIN",f,0))
        self.assertNotEqual(digest(episodes("O7_TRAIN",FAMILIES[0])),
                            digest(episodes("O7_TRAIN",FAMILIES[1])))


if __name__=="__main__":
    unittest.main()

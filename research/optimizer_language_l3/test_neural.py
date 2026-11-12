"""L3 exact new public role identity and analytic recurrent-gradient checks."""
import json
from pathlib import Path
import math
import unittest

import numpy as np

from public_source import (
    NAMESPACE,ROLES,COUNTS,SIZES,FIELDS,SLOTS,PARTITIONS,
    SourceRoleDenied,_holdout,canonical,surface,dataset,row,sha,
)
from neural import ARMS,SEEDS,NeuralChunkModel,public_inputs
from l2_original_categorical import PublicChunkLearner
from runner import guard


class L3BoundedLanguage(unittest.TestCase):
    def test_frozen_prior_research_is_additive(self):
        p=guard()
        self.assertEqual(p["governance"]["mode"],
                         "ADDITIVE_PUBLIC_DEVELOPMENT_ONLY")
        self.assertEqual(p["roles"],COUNTS)
        self.assertEqual(tuple(p["arms"]),ARMS+(
            "PARALLEL_CATEGORICAL_4","UNCONDITIONAL"))
        for name in ("NCI-04","ITD-01","BIO","Mass Research",
                     "Q21 successor","FORGE controller"):
            self.assertIn(name,p["governance"]["unchanged"])

    def test_no_reuse_across_five_train_select_dev_and_null_roles(self):
        observed=[]
        for role in ROLES:
            batch=dataset(role)
            own={tuple(r["meaning"]) for r in batch}
            self.assertEqual(len(batch),COUNTS[role])
            self.assertEqual(len(own),COUNTS[role])
            for old in observed:
                self.assertFalse(old&own)
            observed.append(own)

    def test_holdout_new_pair_has_no_fitted_exposure(self):
        for role in ("L3_TRAIN","L3_SELECT","L3_COMPOSITION_DEV",
                     "L3_NULL_CORRUPT"):
            self.assertTrue(all(not(s[0]==4 and s[2]==4)
                                for s in PARTITIONS[role]))
        self.assertTrue(all(s[0]==4 and s[2]==4
                            for s in PARTITIONS["L3_UNFAMILIAR_PAIR_DEV"]))
        self.assertTrue(all(not _holdout(s) for role in (
            "L3_TRAIN","L3_SELECT") for s in PARTITIONS[role]))
        self.assertTrue(all(_holdout(s) for role in (
            "L3_COMPOSITION_DEV","L3_NULL_CORRUPT")
                            for s in PARTITIONS[role]))

    def test_old_scientific_and_invalid_ids_fail_closed(self):
        for role in ("HELD","ORIGINAL","Q21N01","FSA_FIRST_USE",
                     "L1_NOVEL_COMPOSITION_DEV","L2_DEV_COMPOSE",
                     "L3_DEV","NCI04"):
            with self.assertRaises(SourceRoleDenied):
                dataset(role)
        for role in ROLES:
            for idx in (-1,COUNTS[role],True,1.0,"0"):
                with self.assertRaises(SourceRoleDenied):
                    row(role,idx)

    def test_training_vocabulary_and_all_public_fields_observed(self):
        batch=dataset("L3_TRAIN")
        for j,n in enumerate(SIZES):
            self.assertEqual({r["meaning"][j] for r in batch},set(range(n)))
        words={t for x in batch for t in x["slots"]}
        self.assertIn("",words)
        self.assertIn("not",words)
        self.assertIn("did",words)
        self.assertIn("will",words)
        self.assertEqual(len(SLOTS),8)

    def test_null_corruption_preserves_source_but_flips_polarity(self):
        for r in dataset("L3_NULL_CORRUPT"):
            honest=surface(tuple(r["meaning"]))
            bad=tuple(r["slots"])
            self.assertNotEqual(bad,honest)
            self.assertEqual(bad[0],honest[0])
            self.assertEqual(bad[4:],honest[4:])
            self.assertNotEqual(bad[2],honest[2])

    def test_five_new_source_role_digests_are_unique_and_reproducible(self):
        hashes=[sha(role) for role in ROLES]
        self.assertEqual(len(set(hashes)),len(ROLES))
        self.assertTrue(all(len(d)==64 for d in hashes))
        self.assertEqual(sha(ROLES[0]),sha(ROLES[0]))

    def test_neural_semantic_onehot_is_strictly_public(self):
        x=public_inputs([r["meaning"] for r in dataset("L3_TRAIN")[:3]])
        self.assertEqual(x.shape,(3,sum(SIZES)))
        self.assertTrue(np.all(x.sum(axis=1)==6))
        with self.assertRaises(ValueError):
            public_inputs([[5,0,0,0,0,0]])

    def test_native_neural_arms_forward_use_own_generated_previous(self):
        train=dataset("L3_TRAIN")[:8]
        vocab={z for r in dataset("L3_TRAIN") for z in r["slots"]}
        for arm in ARMS:
            with self.subTest(arm=arm):
                m=NeuralChunkModel(arm,17,vocab)
                initial=m.checkpoint()
                gen,work=m.generate(train[0]["meaning"])
                self.assertEqual(len(gen),8)
                self.assertGreater(work,0)
                self.assertEqual(initial,m.checkpoint())
                nll,g=m.loss_and_gradient(train)
                self.assertTrue(math.isfinite(nll))
                self.assertTrue(all(np.all(np.isfinite(x)) for x in g.values()))
                self.assertEqual(initial,m.checkpoint())

    def test_true_recurrent_bptt_gradient_finite_difference(self):
        examples=dataset("L3_TRAIN")[:4]
        vocab={z for r in dataset("L3_TRAIN") for z in r["slots"]}
        for arm in ARMS:
            with self.subTest(arm=arm):
                m=NeuralChunkModel(arm,31,vocab)
                base,g=m.loss_and_gradient(examples)
                for parameter,index in (
                    ("E",(0,0)),("W",(0,0)),
                    (("recur" if arm=="RNN_H12"
                      else "retention" if arm=="SSM_DIAGONAL_H14"
                      else "slot_e"),
                     (0,0) if arm!="SSM_DIAGONAL_H14" else (0,)),
                ):
                    saved=m.p[parameter][index]
                    h=1e-5
                    m.p[parameter][index]=saved+h
                    plus=m.loss_and_gradient(examples)[0]
                    m.p[parameter][index]=saved-h
                    minus=m.loss_and_gradient(examples)[0]
                    m.p[parameter][index]=saved
                    self.assertAlmostEqual(g[parameter][index],
                                           (plus-minus)/(2*h),delta=2e-6)
                self.assertAlmostEqual(base,m.loss_and_gradient(examples)[0])

    def test_neural_adam_updates_trainable_parameter_not_only_readout(self):
        train=dataset("L3_TRAIN")[:8]
        vocab={z for r in dataset("L3_TRAIN") for z in r["slots"]}
        for arm in ARMS:
            m=NeuralChunkModel(arm,17,vocab)
            before=m.checkpoint()
            w=m.p["E"].copy()
            loss=m.step(train)
            self.assertTrue(math.isfinite(loss))
            self.assertEqual(m.updates,1)
            self.assertFalse(np.array_equal(w,m.p["E"]))
            self.assertNotEqual(before,m.checkpoint())

    def test_immutable_original_categorical_capacity_variation(self):
        tr=dataset("L3_TRAIN")[:64]
        se=dataset("L3_SELECT")[:16]
        a=PublicChunkLearner(4,False).fit(tr,se)
        cp=a.checkpoint()
        self.assertTrue(a.trained)
        self.assertTrue(all(len(s)<=4 for s in a.subsets))
        self.assertEqual(len(a.generate(se[0]["meaning"])[0]),8)
        self.assertEqual(cp,a.checkpoint())


if __name__=="__main__":
    unittest.main()

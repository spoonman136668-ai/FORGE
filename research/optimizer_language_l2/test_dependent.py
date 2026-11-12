"""L2 adversarial source custody and fitted mechanism tests; no science admission."""
import hashlib
import json
from pathlib import Path
import math
import unittest

from public_source import (
    NAMESPACE,ROLES,COUNTS,FIELD_SIZES,FIELDS,SLOTS,PARTITION,
    RoleCustodyError,holdout,source_tokens,record,dataset,digest,
)
from learners import PublicChunkLearner,FittedSelectiveRepair,FittedTupleLookup
from runner import ARMS,guard,evaluate


class L2BoundedLanguageTests(unittest.TestCase):
    def test_prospectively_frozen_protocol_and_no_research_displacement(self):
        p=guard()
        self.assertEqual(tuple(p["models"]),ARMS)
        self.assertEqual(p["governance"]["mode"],"ADDITIVE_DEVELOPMENT_ONLY")
        self.assertEqual(p["role_counts"],COUNTS)
        for name in ("NCI-04","ITD-01","BIO","Mass Research",
                     "Q21 successor","FORGE controller/custody"):
            self.assertIn(name,p["governance"]["unchanged"])

    def test_exact_roles_sizes_unique_no_train_select_dev_overlap(self):
        all_roles={}
        for role in ROLES:
            batch=dataset(role)
            self.assertEqual(len(batch),COUNTS[role])
            own={tuple(x["meaning"]) for x in batch}
            self.assertEqual(len(own),COUNTS[role])
            self.assertTrue(all(len(x["slots"])==8 for x in batch))
            all_roles[role]=own
        for i,left in enumerate(ROLES):
            for right in ROLES[i+1:]:
                self.assertFalse(all_roles[left]&all_roles[right])
        self.assertTrue(all(not holdout(x) for role in ROLES[:2]
                            for x in all_roles[role]))
        self.assertTrue(all(holdout(x) for role in ROLES[2:]
                            for x in all_roles[role]))

    def test_protected_prior_and_role_index_refusal(self):
        for role in ("O14_ZERO_SHOT_TRANSFER","O13_PUBLIC_DEV",
                     "L1_TRAIN","L1_NOVEL_COMPOSITION_DEV",
                     "L2_HELD","HELD","Q21","FSA","ORIGINAL"):
            with self.assertRaises(RoleCustodyError):
                dataset(role)
        for role in ROLES:
            for i in (-1,COUNTS[role],True,1.0,"0"):
                with self.assertRaises(RoleCustodyError):
                    record(role,i)

    def test_every_field_present_and_training_lexical_coverage(self):
        train=dataset("L2_TRAIN")
        for i,n in enumerate(FIELD_SIZES):
            self.assertEqual({x["meaning"][i] for x in train},set(range(n)))
        self.assertEqual(len(FIELDS),6)
        self.assertEqual(len(SLOTS),8)
        self.assertEqual(len({x["slots"][1] for x in train}),30)
        self.assertEqual(len({x["slots"][2] for x in train}),8)

    def test_dependent_verb_uses_four_semantic_input_fields(self):
        # Changing any of actor, verb, tense, negative while preserving
        # other three changes the synthetic dependent-verb target on at least
        # one pair. A 3-field predictor cannot represent this relation in
        # general from any fixed subset of these four fields.
        meaning=[0,0,0,0,0,0]
        base=source_tokens(meaning)[2]
        for i in (0,1,3,4):
            test=meaning[:]
            test[i]=1
            self.assertNotEqual(source_tokens(test)[2],base)
        self.assertEqual(source_tokens([0,0,1,0,0,2])[2],base)

    def test_null_corpus_is_not_a_valid_truthful_target(self):
        for row in dataset("L2_NULL_CORRUPTION"):
            sem=row["meaning"]
            honest=source_tokens(sem)
            corrupt=tuple(row["slots"])
            self.assertEqual(corrupt[1],honest[1])
            self.assertNotEqual(corrupt[2],honest[2])
            self.assertEqual(corrupt[:2],honest[:2])
            self.assertEqual(corrupt[3:],honest[3:])

    def test_source_sha256_reproducible_and_distinct(self):
        hashes=[digest(role) for role in ROLES]
        self.assertEqual(len(set(hashes)),4)
        self.assertTrue(all(len(x)==64 for x in hashes))
        for role in ROLES:
            self.assertEqual(digest(role),digest(role))

    def test_parallel_and_ar_fit_actual_counts_without_oracle(self):
        train=dataset("L2_TRAIN")[:64]
        sel=dataset("L2_SELECT")[:16]
        for cap,ar in ((3,False),(4,False),(3,True),(0,False)):
            m=PublicChunkLearner(cap,ar).fit(train,sel)
            self.assertTrue(m.trained)
            self.assertEqual(len(m.subsets),8)
            self.assertTrue(all(len(x)<=cap for x in m.subsets))
            cp=m.checkpoint()
            generated,ops=m.generate(sel[0]["meaning"])
            self.assertEqual(len(generated),8)
            self.assertGreater(ops,0)
            self.assertEqual(cp,m.checkpoint())
            with self.assertRaises(ValueError):
                m.fit(train,sel)

    def test_sequential_previous_generated_chunk_does_not_see_gold(self):
        train=dataset("L2_TRAIN")[:64]
        select=dataset("L2_SELECT")[:16]
        ar=PublicChunkLearner(3,True).fit(train,select)
        src=select[0]["meaning"]
        generated,ops=ar.generate(src)
        self.assertEqual(len(generated),8)
        self.assertGreater(ops,0)
        # The autoregressive head can condition on previous GENERATED
        # token, not an oracle teacher-forced test-time target.
        for j in range(8):
            probs=ar.distribution(j,src,generated[j-1] if j else "")
            self.assertAlmostEqual(sum(probs.values()),1.,places=12)

    def test_selective_repair_reuses_both_frozen_checkpoints(self):
        train=dataset("L2_TRAIN")[:64]
        sel=dataset("L2_SELECT")[:16]
        p=PublicChunkLearner(3).fit(train,sel)
        a=PublicChunkLearner(3,True).fit(train,sel)
        pc,ac=p.checkpoint(),a.checkpoint()
        r=FittedSelectiveRepair(p,a).select(sel)
        self.assertIn(r.threshold,(.05,.15,.30))
        vals=r.generate(sel[0]["meaning"])
        self.assertEqual(len(vals[0]),8)
        self.assertGreaterEqual(vals[2],0)
        self.assertEqual(pc,p.checkpoint())
        self.assertEqual(ac,a.checkpoint())
        with self.assertRaises(ValueError):
            r.select(sel)

    def test_fitted_memorization_control_abstains_on_unseen_tuples(self):
        train=dataset("L2_TRAIN")[:64]
        sel=dataset("L2_SELECT")[:16]
        majority=PublicChunkLearner(0).fit(train,sel)
        lookup=FittedTupleLookup(train,majority)
        self.assertEqual(lookup.generate(train[0]["meaning"])[0],
                         tuple(train[0]["slots"]))
        result=lookup.generate(sel[0]["meaning"])
        self.assertEqual(len(result[0]),8)
        self.assertTrue(lookup.checkpoint())

    def test_public_scoring_does_not_mutate_fitted_checkpoint(self):
        train=dataset("L2_TRAIN")[:64]
        select=dataset("L2_SELECT")[:16]
        model=PublicChunkLearner(3).fit(train,select)
        checkpoint=model.checkpoint()
        stats=evaluate(model,select,"L2_SELECT")
        self.assertEqual(stats["records"],16)
        self.assertGreaterEqual(stats["meaning_fidelity_exact"],0)
        self.assertLessEqual(stats["meaning_fidelity_exact"],1)
        self.assertIsNone(stats["corrupted_gold_exact_false_positive_rate"])
        self.assertEqual(checkpoint,model.checkpoint())


if __name__=="__main__":
    unittest.main()

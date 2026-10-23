"""L4 real external corpus custody, source disjointness and trained controls."""
import os
from pathlib import Path
import math
import unittest

from source import (
    EXPECTED_GIT_SHA1,EXPECTED_SIZE,SOURCE_URL,ROLES,COUNTS,
    canonical,verify,load_file,examples_from_bytes,digest
)
from models import CategoricalCounts,SelectiveRepair
from runner import ARMS,protocol_guard,fit,evaluate


class L4RealCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        corpus=os.environ.get("L4_EXTERNAL_CORPUS_PATH")
        if not corpus:
            raise RuntimeError("L4_PINNED_EXTERNAL_SOURCE_NOT_STAGED")
        cls.raw=Path(corpus).read_bytes()
        cls.sha,cls.roles=load_file(corpus)

    def test_frozen_charter_enforces_additive_research_scope(self):
        p=protocol_guard()
        self.assertEqual(p["governance"]["scope"],
                         "ADDITIVE_PUBLIC_REALTEXT_DEVELOPMENT_ONLY")
        self.assertEqual(tuple(p["models"]),ARMS)
        for name in ("NCI-04","ITD-01","BIO","Mass Research",
                     "Q21 successor","FORGE controller and scientific custody"):
            self.assertIn(name,p["governance"]["unchanged"])

    def test_exact_pinned_external_source_identity_and_no_rewrites(self):
        self.assertEqual(len(self.raw),EXPECTED_SIZE)
        self.assertEqual(verify(self.raw),self.sha)
        self.assertEqual(len(self.sha),64)
        self.assertEqual(EXPECTED_GIT_SHA1,
                         "7dcb3a2d4cc3b48b6283dd46870bfeb78f88aac9")

    def test_single_byte_source_mutation_fails_closed(self):
        mutant=bytearray(self.raw)
        mutant[123]^=1
        with self.assertRaisesRegex(ValueError,"GIT_OBJECT_DRIFT"):
            verify(bytes(mutant))
        with self.assertRaisesRegex(ValueError,"BYTE_CUSTODY_DRIFT"):
            verify(self.raw[:-1])

    def test_three_chronologically_disjoint_source_roles_and_counts(self):
        all_lines=[]
        all_windows=[]
        for role in ROLES:
            batch=self.roles[role]
            self.assertEqual(len(batch),COUNTS[role])
            self.assertEqual(len(set(x["physical_line"] for x in batch)),
                             COUNTS[role])
            self.assertEqual(len(set(canonical((
                x["left"],x["gold"],x["right"])) for x in batch)),
                             COUNTS[role])
            self.assertTrue(all(len(x["left"])==3 and
                                len(x["gold"])==2 and
                                len(x["right"])==3 for x in batch))
            self.assertEqual(len(digest(batch)),64)
            all_lines.append((batch[0]["physical_line"],
                              batch[-1]["physical_line"]))
            all_windows.append({canonical((x["left"],x["gold"],x["right"]))
                                for x in batch})
        self.assertLess(all_lines[0][1],all_lines[1][0])
        self.assertLess(all_lines[1][1],all_lines[2][0])
        self.assertFalse(all_windows[0]&all_windows[1])
        self.assertFalse(all_windows[0]&all_windows[2])
        self.assertFalse(all_windows[1]&all_windows[2])

    def test_no_prior_development_roles_or_protected_science_names(self):
        self.assertEqual(tuple(ROLES),
                         ("L4_REAL_TRAIN","L4_REAL_SELECT","L4_REAL_DEV"))
        self.assertTrue(all(not n.startswith("L3_") for n in ROLES))

    def test_corpus_tokenizer_and_partition_repeat_byte_exact(self):
        again=examples_from_bytes(self.raw)
        for role in ROLES:
            self.assertEqual(digest(again[role]),digest(self.roles[role]))

    def test_frozen_fit_models_are_supervised_same_training_examples(self):
        train=self.roles["L4_REAL_TRAIN"][:40]
        select=self.roles["L4_REAL_SELECT"][:10]
        learned,stats=fit(train,select)
        self.assertEqual(set(learned),set(ARMS))
        for arm in ARMS:
            self.assertTrue(learned[arm].checkpoint())
            self.assertGreater(stats[arm]["checkpoint_bytes_including_underlying_models"],0)

    def test_train_backoff_refuses_double_fit(self):
        train=self.roles["L4_REAL_TRAIN"][:16]
        m=CategoricalCounts("parallel").fit(train)
        initial=m.checkpoint()
        with self.assertRaisesRegex(ValueError,"DOUBLE_FIT"):
            m.fit(train)
        self.assertEqual(initial,m.checkpoint())

    def test_train_ar_uses_prior_generated_word_not_test_gold(self):
        train=self.roles["L4_REAL_TRAIN"][:60]
        test=self.roles["L4_REAL_DEV"][0]
        m=CategoricalCounts("sequential").fit(train)
        cp=m.checkpoint()
        guess,work=m.generate(test)
        self.assertEqual(len(guess),2)
        self.assertGreater(work,0)
        self.assertEqual(cp,m.checkpoint())

    def test_train_select_only_repair_does_not_mutate_models(self):
        tr=self.roles["L4_REAL_TRAIN"][:60]
        sel=self.roles["L4_REAL_SELECT"][:20]
        p=CategoricalCounts("parallel").fit(tr)
        s=CategoricalCounts("sequential").fit(tr)
        original=(p.checkpoint(),s.checkpoint())
        repair=SelectiveRepair(p,s).select(sel)
        self.assertIn(repair.margin,(0.,.5,1.))
        self.assertEqual(len(repair.generate(sel[0])[0]),2)
        self.assertEqual(original,(p.checkpoint(),s.checkpoint()))
        with self.assertRaises(ValueError):
            repair.select(sel)

    def test_trained_independent_and_joint_are_not_same_model(self):
        tr=self.roles["L4_REAL_TRAIN"][:40]
        ind=CategoricalCounts("parallel").fit(tr)
        joint=CategoricalCounts("joint").fit(tr)
        self.assertNotEqual(ind.checkpoint(),joint.checkpoint())
        x,y=ind.generate(self.roles["L4_REAL_DEV"][0]),joint.generate(
            self.roles["L4_REAL_DEV"][0])
        self.assertEqual(len(x[0]),2)
        self.assertEqual(len(y[0]),2)

    def test_evaluate_dev_fixed_checkpoint_and_truthful_metrics(self):
        train=self.roles["L4_REAL_TRAIN"][:40]
        model=CategoricalCounts("parallel").fit(train)
        before=model.checkpoint()
        word_vocab={w for x in train for w in x["gold"]}
        result=evaluate(model,self.roles["L4_REAL_DEV"][:15],word_vocab)
        self.assertEqual(result["evaluated_rows"],15)
        self.assertTrue(0<=result["two_word_exact_match"]<=1)
        self.assertEqual(len(result["predicted_gaps_sha256"]),64)
        self.assertEqual(before,model.checkpoint())


if __name__=="__main__":
    unittest.main()

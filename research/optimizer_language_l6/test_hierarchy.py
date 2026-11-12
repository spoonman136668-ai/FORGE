"""L6 prospective genuine external source/ablation/neural gradient tests."""
import hashlib
import math
import os
from pathlib import Path
import unittest

from source import GIT_BLOB,RAW_BYTES,ROLES,COUNTS,load,rows_from_raw,verify,digest,canonical
from hierarchy import HierarchicalStemAffix
from l5_original_models import FittedPrefixLexicon,FittedSuffixReuse,FittedCharGram
from neural import TrainedCharRNN
from runner import ARMS,prereg,edit,eval_one


class L6IsolatedPublicMechanisms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=os.environ.get("L6_EXTERNAL_CORPUS_PATH")
        if not path:
            raise RuntimeError("L6_EXTERNAL_FROZEN_FILE_NOT_STAGED")
        cls.raw=Path(path).read_bytes()
        cls.sha,cls.cohorts=load(path)

    def test_first_frozen_protocol_and_prior_native_science_retained(self):
        p=prereg()
        self.assertEqual(p["governance"]["mode"],
                         "ADDITIVE_BOUNDED_PUBLIC_LANGUAGE_EXPLORATION_ONLY")
        self.assertEqual(p["source"]["roles"],COUNTS)
        self.assertEqual(tuple(p["arms"]),ARMS)
        for term in ("NCI-04","ITD-01","BIO","Mass Research",
                     "Q21 successor","FORGE controller/custody"):
            self.assertIn(term,p["governance"]["retain"])

    def test_exact_external_byte_and_git_blob_hash(self):
        self.assertEqual(len(self.raw),RAW_BYTES)
        self.assertEqual(GIT_BLOB,"20c3737a33af2501e4c0597285ad630ef42e8e46")
        self.assertEqual(verify(self.raw),self.sha)

    def test_single_byte_changes_and_truncation_fail_closed(self):
        bad=bytearray(self.raw)
        bad[213]^=1
        with self.assertRaisesRegex(ValueError,"GIT_BLOB_DRIFT"):
            verify(bytes(bad))
        with self.assertRaisesRegex(ValueError,"LENGTH_DRIFT"):
            verify(self.raw[:-1])

    def test_all_new_source_roles_are_unique_chronological_and_no_prior_role(self):
        visited=set()
        last=-1
        for role in ROLES:
            rows=self.cohorts[role]
            self.assertEqual(len(rows),COUNTS[role])
            self.assertLess(last,rows[0]["line"])
            last=rows[-1]["line"]
            for r in rows:
                self.assertEqual(len(r["left"]),3)
                self.assertEqual(len(r["right"]),3)
                self.assertEqual(r["prefix"],r["gold"][:3])
                fp=canonical((r["left"],r["gold"],r["right"]))
                self.assertNotIn(fp,visited)
                visited.add(fp)
        self.assertEqual(set(self.cohorts),set(ROLES))
        self.assertNotIn("L5_DEV",self.cohorts)
        self.assertNotIn("Q21N01",self.cohorts)

    def test_role_identities_repeat_without_any_source_mutation(self):
        other=rows_from_raw(self.raw)
        self.assertEqual({r:digest(self.cohorts[r]) for r in ROLES},
                         {r:digest(other[r]) for r in ROLES})
        self.assertEqual(len({digest(self.cohorts[r]) for r in ROLES}),3)

    def test_train_discovered_morpheme_library_not_handcoded(self):
        train=self.cohorts["L6_TRAIN"][:70]
        hierarchy=HierarchicalStemAffix(True).fit(train)
        self.assertTrue(0<len(hierarchy.suffixes)<=32)
        self.assertTrue(all(1<=len(s)<=5 for s in hierarchy.suffixes))
        self.assertTrue(hierarchy.stems)
        self.assertTrue(hierarchy.pairs)
        with self.assertRaises(ValueError):
            hierarchy.fit(train)

    def test_ablation_and_recombined_candidate_use_same_fitted_stem_inventory(self):
        train=self.cohorts["L6_TRAIN"][:85]
        strong=HierarchicalStemAffix(True).fit(train)
        ablated=HierarchicalStemAffix(False).fit(train)
        self.assertEqual(strong.stems,ablated.stems)
        self.assertEqual(strong.suffix_frequency,ablated.suffix_frequency)
        self.assertEqual(strong.words,ablated.words)
        assert strong.checkpoint()!=ablated.checkpoint()
        inp={k:self.cohorts["L6_DEV"][0][k] for k in ("left","right","prefix")}
        for model in (strong,ablated):
            old=model.checkpoint()
            word,ops=model.predict(inp)
            self.assertTrue(word.startswith(inp["prefix"]))
            self.assertGreaterEqual(ops,1)
            self.assertEqual(old,model.checkpoint())
        ablated_word=ablated.predict(inp)[0]
        self.assertTrue(ablated_word==inp["prefix"] or
                        ablated_word in {r["gold"] for r in train})

    def test_matched_supervised_lexicon_suffix_and_char_ngram_fit(self):
        train=self.cohorts["L6_TRAIN"][:64]
        for model in (FittedPrefixLexicon().fit(train),
                      FittedSuffixReuse().fit(train),
                      FittedCharGram(3).fit(train)):
            public={k:self.cohorts["L6_DEV"][0][k]
                    for k in ("left","right","prefix")}
            state=model.checkpoint()
            output,ops=model.predict(public)
            self.assertTrue(output.startswith(public["prefix"]))
            self.assertGreater(ops,0)
            self.assertEqual(state,model.checkpoint())

    def test_genuine_BPTT_RNN_gradient_matches_finite_difference(self):
        words=[r["gold"] for r in self.cohorts["L6_TRAIN"][:5]]
        model=TrainedCharRNN(17)
        loss,g=model.loss_grad(words)
        self.assertTrue(math.isfinite(loss))
        for key,index in (("E",(0,0)),("U",(0,0)),("V",(0,0)),("b",(0,))):
            old=model.p[key][index]
            h=1e-5
            model.p[key][index]=old+h
            positive=model.loss_grad(words)[0]
            model.p[key][index]=old-h
            negative=model.loss_grad(words)[0]
            model.p[key][index]=old
            self.assertAlmostEqual(g[key][index],
                                   (positive-negative)/(2*h),
                                   delta=2e-6)

    def test_RNN_true_train_updates_and_gold_free_prefix_inference(self):
        train=self.cohorts["L6_TRAIN"][:8]
        model=TrainedCharRNN(31)
        before=model.checkpoint()
        loss=model.step([r["gold"] for r in train])
        self.assertTrue(math.isfinite(loss))
        self.assertEqual(model.updates,1)
        self.assertNotEqual(before,model.checkpoint())
        public={k:self.cohorts["L6_DEV"][0][k]
                for k in ("left","right","prefix")}
        out,ops=model.predict(public)
        self.assertTrue(out.startswith(public["prefix"]))
        self.assertGreater(ops,0)

    def test_fidelity_scoring_uses_real_unseen_gold_and_does_not_mutate(self):
        train=self.cohorts["L6_TRAIN"][:48]
        m=FittedSuffixReuse().fit(train)
        cp=m.checkpoint()
        stats=eval_one(m,self.cohorts["L6_DEV"][:8],
                       {r["gold"] for r in train})
        self.assertEqual(stats["examples"],8)
        self.assertGreaterEqual(stats["unseen_gold_hits"],0)
        self.assertEqual(len(stats["predicted_words_sha256"]),64)
        self.assertEqual(m.checkpoint(),cp)

    def test_normalized_edit_distance_basics(self):
        self.assertEqual(edit("cat","cat"),0)
        self.assertEqual(edit("cat","cats"),1)
        self.assertEqual(edit("door","book"),2)


if __name__=="__main__":
    unittest.main()

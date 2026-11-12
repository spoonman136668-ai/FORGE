"""L5 source and mechanism integrity, isolated from previous studies."""
import hashlib
import json
import os
from pathlib import Path
import unittest

from source import SIZE,BLOB,ROLES,COUNTS,verify,load,rows_from_bytes,digest,canonical
from models import (ARMS,FittedCharGram,FittedPrefixLexicon,
                    FittedSuffixReuse,ContextualCharGram)
from runner import guard,evaluate,edit_distance


class L5ProspectiveSubword(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=os.environ.get("L5_EXTERNAL_CORPUS_PATH")
        if not path:
            raise RuntimeError("L5_EXTERNAL_SOURCE_NOT_STAGED")
        cls.raw=Path(path).read_bytes()
        cls.sha,cls.roles=load(path)

    def test_prospective_protocol_does_not_displace_existing_science(self):
        p=guard()
        self.assertEqual(p["stage"],"FIRST_PROTOCOL_ONLY_COMMIT_BEFORE_SOURCE_LEARNER_AND_DEV")
        self.assertEqual(tuple(p["arms"]),ARMS)
        for name in ("NCI-04","ITD-01","BIO","Mass Research",
                     "Q21 successor","FORGE controller/authority"):
            self.assertIn(name,p["governance"]["preserve"])

    def test_original_external_source_exact_git_blob_and_raw_bytes(self):
        self.assertEqual(len(self.raw),SIZE)
        self.assertEqual(verify(self.raw),self.sha)
        self.assertEqual(BLOB,"0f25e9af379233267a09623e0c650472f9e463ea")

    def test_external_one_byte_corruption_fails_closed(self):
        bad=bytearray(self.raw)
        bad[119]^=1
        with self.assertRaisesRegex(ValueError,"GIT_BLOB_DRIFT"):
            verify(bytes(bad))
        with self.assertRaisesRegex(ValueError,"SIZE_DRIFT"):
            verify(self.raw[:-1])

    def test_three_unique_source_role_gaps_are_chronologically_disjoint(self):
        maxline=-1
        fingerprints=set()
        for role in ROLES:
            data=self.roles[role]
            self.assertEqual(len(data),COUNTS[role])
            self.assertLess(maxline,data[0]["line"])
            maxline=data[-1]["line"]
            for r in data:
                self.assertEqual(len(r["left"]),3)
                self.assertEqual(len(r["right"]),3)
                self.assertEqual(r["prefix"],r["gold"][:3])
                self.assertTrue(5<=len(r["gold"])<=18)
                self.assertTrue(r["gold"].isalpha() and r["gold"].isascii())
                key=canonical((r["left"],r["gold"],r["right"]))
                self.assertNotIn(key,fingerprints)
                fingerprints.add(key)

    def test_role_digests_are_identical_across_regeneration(self):
        fresh=rows_from_bytes(self.raw)
        digests={r:digest(self.roles[r]) for r in ROLES}
        self.assertEqual({r:digest(fresh[r]) for r in ROLES},digests)
        self.assertEqual(len(set(digests.values())),3)

    def test_prefix_lexicon_only_emits_known_training_targets(self):
        model=FittedPrefixLexicon().fit(self.roles["L5_TRAIN"][:30])
        first=self.roles["L5_DEV"][0]
        prediction,work=model.predict({
            "prefix":first["prefix"],"left":first["left"],"right":first["right"]})
        self.assertGreater(work,0)
        self.assertTrue(prediction.startswith(first["prefix"]))
        self.assertTrue(prediction==first["prefix"] or
                        prediction in {r["gold"] for r in self.roles["L5_TRAIN"][:30]})

    def test_char_bigram_trigram_fourgram_generate_from_public_prefix(self):
        train=self.roles["L5_TRAIN"][:30]
        dev=self.roles["L5_DEV"][0]
        public={"prefix":dev["prefix"],"left":dev["left"],"right":dev["right"]}
        for order in (2,3,4):
            with self.subTest(order=order):
                model=FittedCharGram(order).fit(train)
                before=model.checkpoint()
                out,work=model.predict(public)
                self.assertTrue(out.startswith(public["prefix"]))
                self.assertTrue(5<=len(out)<=18)
                self.assertGreater(work,0)
                self.assertEqual(before,model.checkpoint())

    def test_hybrid_rerank_and_suffix_reuse_do_not_reach_dev_gold(self):
        tr=self.roles["L5_TRAIN"][:40]
        row=self.roles["L5_DEV"][0]
        public={k:row[k] for k in ("left","right","prefix")}
        for m in (ContextualCharGram().fit(tr),FittedSuffixReuse().fit(tr)):
            before=m.checkpoint()
            out,ops=m.predict(public)
            self.assertTrue(out.startswith(public["prefix"]))
            self.assertGreater(ops,0)
            self.assertEqual(before,m.checkpoint())

    def test_scoring_does_not_mutate_categorical_source_models(self):
        train=self.roles["L5_TRAIN"][:35]
        model=FittedPrefixLexicon().fit(train)
        cp=model.checkpoint()
        trainset={r["gold"] for r in train}
        result=evaluate(model,self.roles["L5_DEV"][:8],trainset)
        self.assertEqual(result["examples"],8)
        self.assertEqual(len(result["output_sha256"]),64)
        self.assertLessEqual(result["full_word_exact_match"],1.0)
        self.assertEqual(cp,model.checkpoint())

    def test_edit_distance_true_for_compositional_new_lexemes(self):
        self.assertEqual(edit_distance("cat","cats"),1)
        self.assertEqual(edit_distance("cat","cat"),0)
        self.assertEqual(edit_distance("cold","warm"),4)
        self.assertEqual(edit_distance("abc","xyz"),3)

    def test_data_does_not_include_prior_private_or_protected_roles(self):
        self.assertEqual(set(self.roles),set(ROLES))
        self.assertNotIn("L4_REAL_DEV",self.roles)
        self.assertNotIn("HELD",self.roles)
        self.assertNotIn("Q21N01",self.roles)


if __name__=="__main__":
    unittest.main()

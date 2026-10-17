"""Adversarial F109-O original TRAIN chain SHAPE, not values or QA."""
import copy
import json
import unittest
from pathlib import Path
import f109o_train_chain_shape as f

def original(qid,chain,answer):
    return {"Question-ID":qid,"RawQuestion":"Who directed film?",
            "Parses":[{"TopicEntityMid":"opaque-mid",
                       "TopicEntityName":"Some Film",
                       "PotentialTopicEntityMention":"film",
                       "InferentialChain":chain,
                       "Answers":[{"AnswersName":answer,"AnswersMid":"PRIVATE"}]}]}
def doc(rows):
    return {"Dataset":"FreebaseQA","Version":"1.0","Questions":rows}

class OriginalShapeTests(unittest.TestCase):
    def test_synthetic_chain_shapes_without_source_values(self):
        rows=[original("1","/film/film.directed_by","SECRET"),
              original("2","/a.b,/c.d","PRIVATE"),
              original("3","a.b c.d","GOLD"),
              original("4","","UNKNOWN")]
        x=f.inventory(doc(rows),4,4)
        self.assertEqual(x["original_train_rows"],4)
        self.assertEqual(x["distinct_full_opaque_chain_strings"],4)
        counts=x["source_only_count_categories"]
        self.assertEqual(counts["chain_contains_dot"],3)
        self.assertEqual(counts["chain_contains_comma"],1)
        self.assertEqual(counts["chain_has_whitespace"],1)
        self.assertEqual(counts["chain_starts_slash"],2)
        self.assertEqual(counts["chain_empty"],1)
        dump=json.dumps(x)
        for secret in ("/film/film.directed_by","/a.b","SECRET","PRIVATE","GOLD","UNKNOWN","opaque-mid"):
            self.assertNotIn(secret,dump)

    def test_answer_mutation_same_structural_outcome(self):
        x=doc([original("1","/film/a","TRUE_ANSWER")])
        y=copy.deepcopy(x)
        y["Questions"][0]["Parses"][0]["Answers"][0]["AnswersName"]="WRONG_ANSWER"
        self.assertEqual(f.inventory(x,1,1),f.inventory(y,1,1))

    def test_source_label_mutation_preserves_shape_categories(self):
        x=doc([original("1","film.film.directed_by","PRIVATE")])
        y=doc([original("1","film.actor.written_by","PRIVATE")])
        self.assertEqual(f.inventory(x,1,1),f.inventory(y,1,1))

    def test_strict_original_rows_parse_denominators_and_flat_schema(self):
        a=doc([original("1","role","x")])
        with self.assertRaises(f.Denied):f.inventory(a,2,1)
        with self.assertRaises(f.Denied):f.inventory(a,1,2)
        b=copy.deepcopy(a)
        b["Questions"][0]["Parses"][0]["InferentialChain"]=["role"]
        with self.assertRaises(f.Denied):f.inventory(b,1,1)
        d=doc([original("x","role","a"),original("x","role","b")])
        with self.assertRaises(f.Denied):f.inventory(d,2,2)

    def test_denied_qa_content_fetch_and_git_blob_drifts(self):
        for args in (["show","HEAD:"+f.EVAL],["show","HEAD:"+f.DEV],
                     ["cat-file","-p","HEAD:"+f.DEV],
                     ["rev-parse","HEAD:secret.json"]):
            with self.assertRaises(f.Denied):f.metadata(Path("."),args)
        self.assertNotEqual(f.TRAIN_BLOB,f.DEV_BLOB)
        self.assertEqual(f.band(""),"empty")
        self.assertEqual(f.band("a"*513),"bytes_513_plus")
        self.assertEqual(f.arity(1),"one")
        self.assertEqual(f.arity(4),"four_plus")

if __name__=="__main__":unittest.main()

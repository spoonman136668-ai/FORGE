"""Adversarial F110-O Stage B source grammar, no graph or gold labels."""
import copy
import json
import unittest
from f110o_empty_dot_candidate import (
    candidate_one_role,subtype,inspect,Denied
)
from f110o_graph_custody_policy import evaluate_manifest,FIELDS

def row(qid,role,gold="SECRET_ANSWER"):
    return {"Question-ID":qid,"RawQuestion":"Who worked on this?",
            "Parses":[{"InferentialChain":role,
                       "TopicEntityMid":"SOURCE_MID",
                       "TopicEntityName":"source_name",
                       "PotentialTopicEntityMention":"source_mention",
                       "Answers":[{"AnswersName":gold}]}]}
def document(rows):
    return {"Dataset":"FreebaseQA","Version":"v1","Questions":rows}

class FrozenSubtypes(unittest.TestCase):
    def test_distinct_dot_shapes_exclusive(self):
        for value,kind in (
            (".people.person.parents.","leading_and_trailing_dot"),
            (".people.person.parents","leading_dot_only"),
            ("people.person.parents.","trailing_dot_only"),
            ("people..person.parents","interior_repeated_dot"),
            (".","leading_and_trailing_dot"),
        ):
            self.assertEqual(subtype(value),kind,value)

    def test_only_one_leading_dot_preselected_no_direction(self):
        for accepted in (".film.film.directed_by",
                         "._film._role10",
                         ".Upper.Lower"):
            source,status=candidate_one_role(accepted)
            self.assertEqual(source,accepted)
            self.assertEqual(status,"candidate_one_leading_dot_accepted")
            self.assertIsInstance(source,str)
        for denied in ("film.film.directed_by",
                       ".film.",".film..role","..film.role",
                       "film..role","film.role.",".film.role.",
                       ".single",".film.8bad",".film.#bad",
                       ".film.actor\nBAD","."+"x"*513+".a"):
            parsed,status=candidate_one_role(denied)
            self.assertIsNone(parsed,denied)
            self.assertEqual(status,"candidate_additional_rejected")

    def test_complete_synthetic_original_f109_and_candidate_reconciliation(self):
        src=document([
            row("1","film.film.directed_by"),
            row("2",".film.film.directed_by"),
            row("3","film.film.directed_by."),
            row("4","film..role"),
            row("5","role#other"),
        ])
        got=inspect(src,5,5)
        orig=got["exclusive_original_subtype_counts"]
        self.assertEqual(orig["f109_accepted"],1)
        self.assertEqual(orig["f109_non_empty_dot_rejected"],1)
        self.assertEqual(orig["leading_dot_only"],1)
        self.assertEqual(orig["trailing_dot_only"],1)
        self.assertEqual(orig["interior_repeated_dot"],1)
        self.assertEqual(got["one_preselected_candidate_status_counts"]
                         ["candidate_one_leading_dot_accepted"],1)
        self.assertEqual(got["one_preselected_candidate_status_counts"]
                         ["candidate_additional_rejected"],2)
        serialized=json.dumps(got)
        for private in ("film.film.directed_by","role#other",
                        "SOURCE_MID","SECRET_ANSWER","source_name"):
            self.assertNotIn(private,serialized)
        self.assertFalse(got["role_direction_inferred"])

    def test_answer_swap_invariance_and_source_denominator(self):
        x=document([row("a",".film.role","GOLD")])
        y=copy.deepcopy(x)
        y["Questions"][0]["Parses"][0]["Answers"][0]["AnswersName"]="FORGED"
        self.assertEqual(inspect(x,1,1),inspect(y,1,1))
        with self.assertRaises(Denied):inspect(x,2,1)
        with self.assertRaises(Denied):inspect(x,1,2)
        with self.assertRaises(Denied):
            inspect(document([row("a",".film.role"),row("a",".film.role")]),2,2)

    def test_fabricated_fully_populated_manifest_never_activates_graph(self):
        complete={
            k: ("0"*64 if "sha256" in k else
                1000 if k in ("archive_bytes","extracted_edge_bytes",
                              "exact_complete_edge_count") else
                "Freebase" if k in ("entity_namespace","role_namespace") else
                "source-example")
            for k in FIELDS
        }
        for forged in (None,{},{"read_only_streaming_index_version":"v1"},
                       complete,{**complete,"archive_bytes":-1}):
            outcome=evaluate_manifest(forged)
            self.assertFalse(outcome["admitted"])
            self.assertEqual(outcome["status"],
                             "FREEBASE_GRAPH_SOURCE_NOT_QUALIFIED")
            self.assertFalse(outcome["original_full_edge_corpus_read"])
            self.assertEqual(outcome["real_graph_calls"],0)
            self.assertFalse(outcome["claimed_complete_metadata_is_independent_evidence"])

if __name__=="__main__":unittest.main()

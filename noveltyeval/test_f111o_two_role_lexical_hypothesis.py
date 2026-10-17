"""F111-O adverse frozen two-role lexical hypothesis, no graph semantics."""
import copy
import json
import unittest
from pathlib import Path

import f111o_two_role_lexical_hypothesis as f

def row(qid,source,answer="PRIVATE_GOLD"):
    return {"Question-ID":qid,"RawQuestion":"What film is this?",
            "Parses":[{"InferentialChain":source,
                       "TopicEntityMid":"source-id-not-read",
                       "TopicEntityName":"not-read","PotentialTopicEntityMention":"not-read",
                       "Answers":[{"AnswersName":answer,"AnswersMid":"private"}]}]}
def document(records):
    return {"Dataset":"FreebaseQA","Version":"v1","Questions":records}

class DoubleDotBoundaryTests(unittest.TestCase):
    def test_two_complete_dotted_predicates_exactly_one_source_separator(self):
        for role in ("film.film.directed_by..people.person.parents",
                     "_film._name.._actors._member",
                     "A.B..C.D"):
            parts,status=f.parse_two(role)
            self.assertEqual(status,"candidate_two_roles_lexically_admitted")
            self.assertEqual("..".join(parts),role)
            self.assertEqual(len(parts),2)
            self.assertIsInstance(parts[0],str)
        # A source label is NOT graph steps and the marker cannot infer direction.

    def test_two_hop_hypothesis_negative_cases_fail_closed(self):
        negatives={
            "film.film.directed_by":"unsupported_other_source_label",
            "..film.role":"unsupported_other_source_label",
            ".film.role..person.parents":"unsupported_other_source_label",
            "film.role..people.person.":"unsupported_other_source_label",
            "film.role..people.person..another.role":"multiple_double_dot_delimiters",
            "film.role...people.person":"right_predicate_invalid",
            "film.role..person":"right_predicate_invalid",
            "film..people.person.parents":"left_predicate_invalid",
            "film..person":"both_predicates_invalid",
            "film.role..people..person":"multiple_double_dot_delimiters",
            "film.role..people.per#son":"right_predicate_invalid",
            "film.role..people.per son":"right_predicate_invalid",
            "film.role..people.per\nson":"unsupported_other_source_label",
            "film.role..Ⅷ.person":"unsupported_other_source_label",
            "film.role..people."+("x"*513):"unsupported_other_source_label",
        }
        for value,expected in negatives.items():
            parts,status=f.parse_two(value)
            self.assertIsNone(parts,value)
            self.assertEqual(status,expected,value)

    def test_complete_original_source_population_and_frozen_f109_controls(self):
        src=document([
            row("a","film.film.directed_by"),
            row("b","film.film.directed_by..people.person.parents"),
            row("c","film.role..person"),
            row("d","film..person"),
            row("e","film.role..people.person..other.other"),
            row("f","nondotted"),
        ])
        x=f.inventory(src,6,6)
        self.assertEqual(x["original_parse_entries"],6)
        self.assertEqual(x["f109_original_single_accepted"],1)
        self.assertEqual(x["f110_original_interior_double_dot"],4)
        self.assertEqual(x["source_label_cardinalities_only"]["f110_original_interior_double_dot"],4)
        self.assertEqual(x["f109_original_other_rejected"],1)
        buckets=x["exclusive_two_role_hypothesis_outcomes"]
        self.assertEqual(sum(buckets.values()),4)
        self.assertEqual(buckets["candidate_two_roles_lexically_admitted"],1)
        self.assertEqual(buckets["right_predicate_invalid"],1)
        self.assertEqual(buckets["both_predicates_invalid"],1)
        self.assertEqual(buckets["multiple_double_dot_delimiters"],1)
        self.assertFalse(x["role_direction_known"])
        self.assertFalse(x["two_hop_graph_semantics_qualified"])
        report=json.dumps(x)
        for hidden in ("film.film.directed_by","people.person.parents",
                       "PRIVATE_GOLD","source-id-not-read"):
            self.assertNotIn(hidden,report)

    def test_source_answer_perturbation_does_not_change_any_criterion(self):
        x=document([row("a","film.role..people.person","TRUE")])
        y=copy.deepcopy(x)
        y["Questions"][0]["Parses"][0]["Answers"][0]["AnswersName"]="FALSE"
        self.assertEqual(f.inventory(x,1,1),f.inventory(y,1,1))

    def test_denominator_and_flat_types_hard_denial(self):
        src=document([row("a","film.role..people.person")])
        with self.assertRaises(f.Denied):f.inventory(src,2,1)
        with self.assertRaises(f.Denied):f.inventory(src,1,2)
        dupe=document([row("a","film.role..people.person"),
                       row("a","film.role..people.person")])
        with self.assertRaises(f.Denied):f.inventory(dupe,2,2)
        invalid=copy.deepcopy(src)
        invalid["Questions"][0]["Parses"][0]["InferentialChain"]=["film.role","people.person"]
        with self.assertRaises(f.Denied):f.inventory(invalid,1,1)

    def test_dev_eval_source_bytes_disallowed_and_graph_never_admitted(self):
        g=f.graph_custody.evaluate_manifest({
            "publisher_source_url":"fake",
            "independent_archive_sha256":"0"*64,
            "archive_bytes":5000,
            "independent_extracted_edge_sha256":"0"*64,
            "extracted_edge_bytes":6000})
        self.assertEqual(g["status"],"FREEBASE_GRAPH_SOURCE_NOT_QUALIFIED")
        self.assertFalse(g["admitted"])
        self.assertEqual(g["real_graph_calls"],0)
        for op in (["show","HEAD:"+f.original_f110.source.DEV],
                   ["show","HEAD:"+f.original_f110.source.EVAL]):
            with self.assertRaises(f.original_f110.source.Denied):
                f.original_f110.source.metadata(Path("."),op)

if __name__=="__main__":unittest.main()

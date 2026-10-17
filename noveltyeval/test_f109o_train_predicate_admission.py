"""F109-O synthetic strict Freebase single-role original TRAIN grammar tests."""
import copy
import json
import unittest
from pathlib import Path
import f109o_train_predicate_admission as f

def row(qid,pred,answer):
    return {"Question-ID":qid,"RawQuestion":"Who directed the film?",
            "Parses":[{"TopicEntityMid":"m.123","TopicEntityName":"film",
                      "PotentialTopicEntityMention":"film",
                      "InferentialChain":pred,
                      "Answers":[{"AnswersName":answer,"AnswersMid":"private"}]}]}
def doc(rows):
    return {"Dataset":"FreebaseQA","Version":"1","Questions":rows}

class FreebaseSourcePredicateTests(unittest.TestCase):
    def test_strict_unchanged_one_predicate_and_no_implicit_direction(self):
        for value in ("film.film.directed_by","people.person.parents",
                      "a.b","_leading._sub2","Film.Actor.Role_A"):
            role,reason=f.admit_one_predicate(value)
            self.assertEqual(role,value)
            self.assertEqual(reason,"accepted_one_opaque_predicate")
        # The dot inside one Freebase role never means a graph hop.
        role,_=f.admit_one_predicate("film.film.directed_by")
        self.assertIsInstance(role,str)
        self.assertNotIsInstance(role,list)

    def test_frozen_adversarial_source_rejections(self):
        for value,reason in (
            ("","empty"),("film","no_dotted_structure"),
            ("film.film.#actor","invalid_segment_syntax"),
            ("film..actor","invalid_segment_syntax"),
            (".film.actor","invalid_segment_syntax"),
            ("film.actor.","invalid_segment_syntax"),
            ("film/actor","no_dotted_structure"),
            ("film.actor other","invalid_segment_syntax"),
            ("film.actor\nMORE","control_or_non_ascii"),
            ("film.Ⅷ","control_or_non_ascii"),
            ("f"+("a"*512)+".r","too_long"),
            ("film.9digits","invalid_segment_syntax"),
        ):
            got,why=f.admit_one_predicate(value)
            self.assertIsNone(got)
            self.assertEqual(why,reason,value)

    def test_all_source_rows_and_regressions_in_one_report(self):
        inputs=[
            row("a","film.film.directed_by","SECRET"),
            row("b","film.actor.directed_by","SECRET"),
            row("c","bad#name","SECRET"),
            row("d","","SECRET"),
        ]
        report=f.syntax_inventory(doc(inputs),4,4)
        self.assertEqual(report["original_parse_entries"],4)
        self.assertEqual(report["unique_whole_valid_predicates"],2)
        expected=report["predicate_status_counts"]
        self.assertEqual(expected["accepted_one_opaque_predicate"],2)
        self.assertEqual(expected["no_dotted_structure"],1)
        self.assertEqual(expected["empty"],1)
        self.assertFalse(report["original_source_direction_provided"])
        public=json.dumps(report)
        for actual in ("SECRET","film.actor","bad#name","m.123"):
            self.assertNotIn(actual,public)

    def test_labels_mutated_without_role_count_changing(self):
        x=doc([row("a","people.person.parents","CORRECT")])
        y=copy.deepcopy(x)
        y["Questions"][0]["Parses"][0]["Answers"][0]["AnswersName"]="DIFFERENT"
        self.assertEqual(f.syntax_inventory(x,1,1),f.syntax_inventory(y,1,1))

    def test_source_schema_denominator_and_identity_denied(self):
        a=doc([row("a","film.film.role","private")])
        with self.assertRaises(f.Denied):f.syntax_inventory(a,2,1)
        with self.assertRaises(f.Denied):f.syntax_inventory(a,1,2)
        duplicate=doc([row("a","film.film.role","1"),row("a","film.film.role","2")])
        with self.assertRaises(f.Denied):f.syntax_inventory(duplicate,2,2)
        changed=copy.deepcopy(a)
        changed["Questions"][0]["Parses"][0]["InferentialChain"]=["film.film.role"]
        with self.assertRaises(f.Denied):f.syntax_inventory(changed,1,1)

    def test_untrusted_graph_manifest_never_authorizes_huge_original_graph(self):
        forged={"original_sha256":"0"*64,"source_license":"claimed",
                "rows":182_000_000,"slices":[1,2,3],"signed":True}
        for val in (None,{},forged,{"plan":"full FREEBASE graph"}):
            self.assertEqual(f.can_admit_original_freebase_graph(val),
                             "FREEBASE_GRAPH_SOURCE_NOT_QUALIFIED")

if __name__=="__main__":unittest.main()

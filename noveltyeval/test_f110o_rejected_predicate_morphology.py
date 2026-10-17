"""F110-O frozen rejection taxonomy fixtures; no semantic source value release."""
import copy
import json
import unittest
from pathlib import Path

import f110o_rejected_predicate_morphology as m

def question(i,value,label="SECRET"):
    return {"Question-ID":str(i),"RawQuestion":"Which movie is named?",
            "Parses":[{"TopicEntityMid":"opaque","TopicEntityName":"Entity",
                       "PotentialTopicEntityMention":"Entity",
                       "InferentialChain":value,
                       "Answers":[{"AnswersName":label}]}]}
def doc(rows):
    return {"Dataset":"FreebaseQA","Version":"v1","Questions":rows}

class FrozenTrainingMorphology(unittest.TestCase):
    def test_exclusive_registered_taxonomy_and_reconciliation(self):
        samples=[
            ("film.actor","accepted"),
            ("","empty"),("a"*513+".b","over_512_bytes"),
            ("film.a\n","control_or_non_ascii"),
            ("filmpredicate","no_dot"),("film.a#b","contains_hash"),
            ("film-a.b","contains_dash"),("film:a.b","contains_colon"),
            ("film .actor","contains_whitespace"),
            ("film/a.b","contains_slash_pipe_comma_semicolon"),
            ("film..actor","contains_empty_dot_segment"),
            ("4film.actor","leading_digit_any_segment"),
            ("film.$actor","invalid_other"),
        ]
        for value,bucket in samples:
            if bucket!="accepted":
                self.assertEqual(m.category(value),bucket,value)
        data=m.inventory(doc([question(i,v) for i,(v,_) in enumerate(samples)]),
                         len(samples),len(samples))
        out=data["exclusive_morphology_counts"]
        self.assertEqual(out["f109_accepted"],1)
        self.assertEqual(sum(out.values()),len(samples))
        self.assertEqual(out["invalid_other"],1)
        self.assertEqual(data["original_parse_instances"],len(samples))
        self.assertFalse(data["source_answers_examined"])

    def test_gold_label_perturbation_cannot_affect_shape(self):
        a=doc([question("q","film.$role","GOLD")])
        b=copy.deepcopy(a)
        b["Questions"][0]["Parses"][0]["Answers"][0]["AnswersName"]="FORGED"
        self.assertEqual(m.inventory(a,1,1),m.inventory(b,1,1))
        output=json.dumps(m.inventory(a,1,1))
        for forbidden in ("film.$role","GOLD","Entity","opaque"):
            self.assertNotIn(forbidden,output)

    def test_refuse_partial_source_and_changed_schema(self):
        a=doc([question("q","film.actor")])
        with self.assertRaises(m.Denied):m.inventory(a,2,1)
        with self.assertRaises(m.Denied):m.inventory(a,1,2)
        b=doc([question("q","film.actor"),question("q","film.actor")])
        with self.assertRaises(m.Denied):m.inventory(b,2,2)
        c=copy.deepcopy(a)
        c["Questions"][0]["Parses"][0]["InferentialChain"]=["film.actor"]
        with self.assertRaises(m.Denied):m.inventory(c,1,1)

    def test_no_dev_eval_read_capability_in_source_commands(self):
        for op in (["show","HEAD:"+m.source.DEV],
                   ["show","HEAD:"+m.source.EVAL],
                   ["cat-file","-p","HEAD:"+m.source.EVAL]):
            with self.assertRaises(m.source.Denied):
                m.source.metadata(Path("."),op)

if __name__=="__main__":unittest.main()

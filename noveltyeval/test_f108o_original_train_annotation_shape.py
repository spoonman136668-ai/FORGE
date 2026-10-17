"""F108-O original TRAIN annotation shape, never source scalar value, tests."""
import hashlib
import json
import unittest
from collections import Counter

import f108o_original_train_annotation_shape as f

def fixture():
    return {
        "Dataset":"FreebaseQA","Version":"1.0",
        "Questions":[{"Question-ID":"test001","RawQuestion":"Who knew Y?",
         "Parses":[
             {"TopicEntity":{"TopicEntityMid":"/m/private_entity",
                             "TopicEntityName":"DONOTEMIT"},
              "InferentialChain":{"Relations":["/people/person/parents"]},
              "Answers":[{"AnswersName":"SECRET_ANSWER"}]},
             {"TopicEntityMid":"/m/test","AnswersMid":"SECRET_ANSWER"},
         ]},
        ],
    }

class SourceShapeTests(unittest.TestCase):
    def test_schema_paths_types_only_no_values(self):
        obj=fixture()
        count=Counter();unsafe=Counter()
        f.shape(obj["Questions"][0]["Parses"],"Questions[].Parses",count,unsafe)
        dump=json.dumps({str(k):v for k,v in count.items()})
        for forbidden in ("DONOTEMIT","SECRET_ANSWER","/m/private_entity",
                          "/people/person/parents"):
            self.assertNotIn(forbidden,dump)
        self.assertEqual(count[("Questions[].Parses[]","object")],2)
        self.assertEqual(count[("Questions[].Parses[].TopicEntity","object")],1)
        self.assertEqual(count[("Questions[].Parses[].TopicEntity.TopicEntityMid","string")],1)
        self.assertEqual(unsafe["skipped_answer_subtree_occurrences"],2)

    def test_replaced_answer_values_do_not_affect_shape(self):
        first=fixture()["Questions"][0]["Parses"]
        second=fixture()["Questions"][0]["Parses"]
        second[0]["Answers"][0]["AnswersName"]="DIFFERENT_PRIVATE_LABEL"
        second[1]["AnswersMid"]="SOMETHING_ELSE"
        a,b=Counter(),Counter()
        u,v=Counter(),Counter()
        f.shape(first,"P",a,u)
        f.shape(second,"P",b,v)
        self.assertEqual(a,b)
        self.assertEqual(u,v)

    def test_original_blob_differences_rejected(self):
        b=b'{"Questions":[]}\n'
        sha=hashlib.sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()
        self.assertEqual(f.blob_id(b),sha)
        self.assertNotEqual(f.blob_id(b.replace(b"\n",b"\r\n")),sha)

    def test_bad_denominator_and_duplicate_ids_denied(self):
        with self.assertRaises(f.Denied):
            f.inventory(json.dumps(fixture()).encode())
        self.assertFalse(f.KEY.fullmatch("bad\ntitle"))
        self.assertFalse(f.KEY.fullmatch("private:secret"))
        self.assertTrue(f.KEY.fullmatch("TopicEntity"))

    def test_field_depth_abstains_instead_of_revealing_nested_values(self):
        x="SECRET"
        for _ in range(9):x={"Container":x}
        count=Counter();unsafe=Counter()
        f.shape(x,"Parses",count,unsafe)
        self.assertIn(("Parses.Container.Container.Container.Container.Container.Container.Container",
                       "depth_budget_refused"),count)
        self.assertNotIn("SECRET",str(count))

    def test_git_metadata_does_not_allow_qa_content_lookup(self):
        for args in (["show","HEAD:"+f.EVAL],
                     ["show","HEAD:"+f.DEV],
                     ["cat-file","-p","HEAD:"+f.DEV],
                     ["rev-parse","HEAD:unapproved.json"]):
            with self.assertRaises(f.Denied):
                f.git_info(__import__("pathlib").Path("."),args)

if __name__=="__main__":unittest.main()

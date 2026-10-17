"""F106-O dev-only source gate: question-only projections and eval isolation."""
import json
import hashlib
import unittest
from pathlib import Path
from unittest import mock

import f106o_crosskg_dev_inventory as f


def fixture(answers=("Answer X", "Answer Y")):
    return {
        "Dataset":"FreebaseQA",
        "Version":"v1.0",
        "Questions":[
            {"Question-ID":"dev-001","RawQuestion":"Who directed Film One?",
             "ProcessedQuestion":"ignore answer-derived transformations",
             "Parses":[{"InferentialChain":["LEAK_PRIVATE_RELATION"],
                        "Answers":[{"AnswersName":answers[0]}]}]},
            {"Question-ID":"dev-002","RawQuestion":"When was Film Two released?",
             "ProcessedQuestion":"IGNORE",
             "Parses":[{"TopicEntityMid":"/m/never_use",
                        "Answers":[{"AnswersName":answers[1]}]}]},
        ],
    }


def encode(doc):
    return json.dumps(doc,ensure_ascii=True).encode("utf-8")


class DevOnlySchemaAdversarialTests(unittest.TestCase):
    def test_annotation_changes_cannot_change_question_only_projection(self):
        a=f.inventory(encode(fixture()),2)
        b=f.inventory(encode(fixture(("Wrong A","Incorrect B"))),2)
        self.assertEqual(a,b)
        self.assertEqual(a["unique_question_ids"],2)
        self.assertEqual(a["raw_question_length_bands"]["001_128"],2)
        self.assertNotIn("LEAK_PRIVATE_RELATION",str(a))
        self.assertNotIn("Answer X",str(a))
        self.assertFalse(a["development_labels_used_for_planning"])

    def test_modified_question_population_denied(self):
        for bad in [
            {"Dataset":"x","Version":"v","Questions":[]},
            {"Dataset":"x","Version":"v","Questions":"not-list"},
            {"Dataset":"x","Version":"v"},
            [],
        ]:
            with self.assertRaises(f.Denied):
                f.inventory(encode(bad),2)
        original=fixture()
        original["Questions"][1]["Question-ID"]="dev-001"
        with self.assertRaises(f.Denied):
            f.inventory(encode(original),2)
        with self.assertRaises(f.Denied):
            f.inventory(encode(fixture()),3)

    def test_invalid_question_and_control_rejected_not_published(self):
        for bad in ("","A\nGold","B\tAnswer","X"+chr(0)+"Y","Q"*2049):
            original=fixture()
            original["Questions"][0]["RawQuestion"]=bad
            with self.assertRaises(f.Denied):
                f.inventory(encode(original),2)
        bad=fixture()
        bad["Questions"][0]["Question-ID"]=7
        with self.assertRaises(f.Denied):
            f.inventory(encode(bad),2)

    def test_original_git_identity_byte_level(self):
        raw=encode(fixture())
        want=hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()
        self.assertEqual(f.blob_sha1(raw),want)
        self.assertNotEqual(f.blob_sha1(raw+b"\n"),want)

    def test_github_git_data_read_whitelist_never_eval(self):
        for name in (f.EVAL_FILE,"FreebaseQA-partial.json","README.md"):
            with self.assertRaises(f.Denied):
                f.git_dev_bytes(Path("."),name)
        with self.assertRaises(f.Denied):
            f.git_metadata(Path("."),["rev-parse","HEAD:unknown.json"])
        with self.assertRaises(f.Denied):
            f.git_metadata(Path("."),["show","HEAD:"+f.EVAL_FILE])

    def test_output_is_aggregate_only_no_question_or_answer(self):
        r=f.inventory(encode(fixture()),2)
        serialized=json.dumps(r)
        for forbidden in ("Who directed","When was","AnswersName",
                          "InferentialChain","TopicEntityMid","Film One","Answer X"):
            self.assertNotIn(forbidden,serialized)

if __name__=="__main__":
    unittest.main()

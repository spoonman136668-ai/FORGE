"""P9 metadata-only cohort selection and checksum-custody regressions."""
import copy
import hashlib
import json
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
import mpai05_p9_dataset_freeze as p9

def fixture():
    kinds=sorted(p9.TYPES)
    qs=[]
    for i in range(451):
        qs.append({"id":"qid_%04d"%i,"domain":"web" if i%2==0 else "enterprise",
           "question_type":kinds[i%len(kinds)],"image":None,
           "question":"UNSEEN_QUESTION_%d"%i,"answer":"UNSEEN_GOLD_%d"%i,
           "eval_function":"fake"})
    h={q["id"]:["trajectory_%03d"%k for k in range(100)] for q in qs}
    return qs,h

class P9CohortTests(unittest.TestCase):
    def test_balanced_deterministic_cohort(self):
        q,h=fixture()
        x=p9.choose(q,h)
        self.assertEqual(x["questions"],16)
        self.assertEqual(x["domain_counts"],{"enterprise":8,"web":8})
        self.assertTrue(x["text_only"])
        self.assertEqual(len(x["cohort_sha256"]),64)
        self.assertEqual(x,p9.choose(q,h))
    def test_gold_and_question_text_are_not_selection_inputs(self):
        q,h=fixture()
        before=p9.choose(q,h)["cohort_sha256"]
        for row in q:
            row["question"]="MUTATED_PRIVATE_PROMPT"
            row["answer"]="MUTATED_PRIVATE_GOLD"
            row["eval_function"]="forged_scorer"
        self.assertEqual(before,p9.choose(q,h)["cohort_sha256"])
    def test_duplicate_question_id_is_denied(self):
        q,h=fixture();q[1]["id"]=q[0]["id"]
        with self.assertRaisesRegex(ValueError,"DUPLICATE_QUESTION_ID"):
            p9.choose(q,h)
    def test_altered_haystack_is_denied(self):
        q,h=fixture();h[q[0]["id"]].pop()
        # Altering a nonselected haystack does not alter selected cohort;
        # force the alteration onto a selected ID for a deterministic denial.
        chosen=p9.choose(q,{**h,q[0]["id"]:["trajectory_%03d"%i for i in range(100)]})
        target=chosen["cohort"][0]["id"]
        h[target]=["duplicate"]*100
        with self.assertRaisesRegex(ValueError,"SMALL_HAYSTACK_INVALID"):
            p9.choose(q,h)
    def test_wrong_haystack_key_set_denied(self):
        q,h=fixture();h.pop(q[0]["id"])
        with self.assertRaisesRegex(ValueError,"HAYSTACK_QUESTION_ID_PARITY"):
            p9.choose(q,h)
    def test_question_count_denied(self):
        q,h=fixture()
        with self.assertRaisesRegex(ValueError,"QUESTION_COUNT_OR_TYPE"):
            p9.choose(q[:-1],h)
    def test_question_type_denied(self):
        q,h=fixture();q[0]["question_type"]="unrecognized"
        with self.assertRaisesRegex(ValueError,"QUESTION_TYPE_OR_DOMAIN"):
            p9.choose(q,h)
    def test_manifest_exact_hashes_pass(self):
        data="\n".join(f"{v}  {k}" for k,v in p9.FILE_HASHES.items()).encode()
        self.assertTrue(p9.check_manifest(data))
    def test_manifest_drift_denied(self):
        d=dict(p9.FILE_HASHES);d["questions.jsonl"]="a"*64
        data="\n".join(f"{v}  {k}" for k,v in d.items()).encode()
        with self.assertRaisesRegex(ValueError,"PUBLISHED_DATA_HASH_DRIFT"):
            p9.check_manifest(data)
    def test_manifest_duplicate_denied(self):
        data="\n".join(f"{v}  {k}" for k,v in p9.FILE_HASHES.items())
        data+="\n"+f"{p9.FILE_HASHES['questions.jsonl']}  questions.jsonl"
        with self.assertRaisesRegex(ValueError,"CHECKSUM_MANIFEST_DUPLICATE"):
            p9.check_manifest(data.encode())
    def test_no_model_api_or_durable_store(self):
        s=pathlib.Path(p9.__file__).read_text("utf-8")
        for forbidden in ("llama_cpp", "openai.Completion", "from huggingface_hub",
                          "write_accepted_ice(", "trajectories.jsonl?download", "model.create"):
            self.assertNotIn(forbidden,s)
        self.assertFalse(p9.freeze.__doc__=="independent first use")
if __name__=="__main__":
    unittest.main()

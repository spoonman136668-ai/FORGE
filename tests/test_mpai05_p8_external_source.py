"""Source-only P8 fail-closed negative tests, zero benchmark task consumption."""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
import mpai05_p8_external_source_intake as p8

README = ("LongMemEval-V2 contains 451 manually curated questions for both "
          "web and enterprise environments using memory_modules/ and evaluation/ "
          "with --memory-context-max-tokens query.")

class TestP8ExternalSource(unittest.TestCase):
    def good(self):
        return p8.gate_record(p8.UPSTREAM_SHA,dict(p8.BLOBS),README)
    def test_public_source_does_not_claim_science(self):
        x=self.good()
        self.assertEqual(x["model_calls"],0)
        self.assertEqual(x["dataset_questions_opened"],0)
        self.assertFalse(x["independently_sealed_first_use"])
        self.assertFalse(x["independent_grading"])
        self.assertFalse(x["scientific_accepted"])
        self.assertFalse(x["composition_authorized"])
        self.assertEqual(x["accepted_memory_writes"],0)
        self.assertEqual(len(x["source_intake_sha256"]),64)
    def test_wrong_source_denied(self):
        with self.assertRaisesRegex(ValueError,"UPSTREAM_COMMIT_DRIFT"):
            p8.gate_record("a"*40,dict(p8.BLOBS),README)
    def test_wrong_source_syntax_denied(self):
        with self.assertRaisesRegex(ValueError,"UPSTREAM_SHA_SYNTAX"):
            p8.gate_record("main",dict(p8.BLOBS),README)
    def test_blob_tamper_denied(self):
        a=dict(p8.BLOBS);a["evaluation/harness.py"]="a"*40
        with self.assertRaisesRegex(ValueError,"UPSTREAM_SOURCE_BLOB_DRIFT"):
            p8.gate_record(p8.UPSTREAM_SHA,a,README)
    def test_extra_blob_denied(self):
        a=dict(p8.BLOBS);a["dataset_answers.json"]="a"*40
        with self.assertRaisesRegex(ValueError,"BLOB_SET_DRIFT"):
            p8.gate_record(p8.UPSTREAM_SHA,a,README)
    def test_removed_blob_denied(self):
        a=dict(p8.BLOBS);a.pop("data/public_data.py")
        with self.assertRaisesRegex(ValueError,"BLOB_SET_DRIFT"):
            p8.gate_record(p8.UPSTREAM_SHA,a,README)
    def test_wrong_project_denied(self):
        with self.assertRaisesRegex(ValueError,"UPSTREAM_INTERFACE_DRIFT"):
            p8.gate_record(p8.UPSTREAM_SHA,dict(p8.BLOBS),
                           README.replace("LongMemEval-V2","OtherBench"))
    def test_zero_code_inference_deps(self):
        src=pathlib.Path(p8.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import llama_cpp",src)
        self.assertNotIn("import openai",src)
        self.assertNotIn("from huggingface_hub",src)
        self.assertNotIn("snapshot_download(",src)
        self.assertNotIn("read_jsonl(",src)

if __name__=="__main__":unittest.main()

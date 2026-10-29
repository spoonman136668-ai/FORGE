"""P10 focused mechanism guards; no data download or model inference."""
import hashlib
import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
import mpai05_p10_public_development as p10

class P10Guards(unittest.TestCase):
    def test_source_dataset_and_model_immutable_pins(self):
        self.assertEqual(p10.PIN_COHORT,
                         "103dbf87dda69f03b32f4c6a3a987b5ab5b7a8d3c3ceeb11f223ad5cf358ae52")
        self.assertEqual(p10.BYTES_TRAJECTORIES,1195604539)
        self.assertEqual(p10.SHA_TRAJECTORIES,
                         "363cec9a8e87aa8d9101ce4e600aadbf7031d674056ebe4f969e8424abc5f3c6")
        self.assertEqual(p10.SHA_MODEL,
                         "2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2")
    def test_four_arms_fixed(self):
        self.assertEqual(p10.ARMS,
                         ("no_memory","memory_only","memory_reflection","char_matched_placebo"))
        self.assertEqual(p10.MAX_OUTPUT_TOKENS,96)
        self.assertEqual(p10.SEED,137)
    def test_retrieval_provenance_and_bounded_output(self):
        m={"id1":["Goal: edit account settings","action: change shipping address",
                  "accessibility_tree: apply settings"],
           "id2":["Goal: unrelated page","action: open settings view"]}
        s=p10.retrieve("How do I edit account settings?",["id1","id2"],m)
        self.assertIn("Evidence [",s)
        self.assertLessEqual(len(s),p10.CONTEXT_CHARS)
    def test_retrieval_no_spurious_evidence(self):
        s=p10.retrieve("bizarreforgottenword",["id1"],{"id1":["Goal: welcome page"]})
        self.assertEqual(s,"")
    def test_retrieval_order_is_deterministic(self):
        m={"id1":["Goal: edit settings","action: open controls"],
           "id2":["Goal: open settings","thought: edit controls"]}
        a=p10.retrieve("edit settings",["id1","id2"],m)
        b=p10.retrieve("edit settings",["id2","id1"],m)
        self.assertEqual(a,b)
    def test_llm_judges_refused_before_call(self):
        fake=MagicMock()
        fake.eval_name.return_value="llm_abstention_checker"
        score,status=p10.official_grade(fake,"llm_abstention_checker","answer","gold")
        self.assertIsNone(score)
        self.assertEqual(status,"OFFICIAL_LLM_JUDGE_NOT_AUTHORIZED")
        fake.eval_from_spec.assert_not_called()
    def test_unknown_scorer_refused_before_call(self):
        fake=MagicMock()
        fake.eval_name.return_value="arbitrary_remote_plugin"
        score,status=p10.official_grade(fake,"arbitrary_remote_plugin","answer","gold")
        self.assertIsNone(score)
        self.assertEqual(status,"OFFICIAL_UNRECOGNIZED_OR_UNSUPPORTED_SCORER")
        fake.eval_from_spec.assert_not_called()
    def test_exact_pure_scorer_allowed(self):
        fake=MagicMock()
        fake.eval_name.return_value="norm_phrase_set_match"
        fake.eval_from_spec.return_value=True
        fake.score_to_bool.return_value=True
        score,status=p10.official_grade(fake,"norm_phrase_set_match","answer","gold")
        self.assertTrue(score)
        self.assertEqual(status,"OFFICIAL_PURE_SCORER")
        fake.eval_from_spec.assert_called_once_with("norm_phrase_set_match","answer","gold")
    def test_no_fake_grader_defaults(self):
        names=p10.SCORER_ALLOWED
        self.assertTrue(names)
        self.assertFalse(names&p10.JUDGE_REQUIRED)
        for name in ("llm_abstention_checker","llm_gotchas_checker"):
            self.assertIn(name,p10.JUDGE_REQUIRED)
    def test_model_and_accepted_memory_unchanged(self):
        text=pathlib.Path(p10.__file__).read_text("utf-8")
        self.assertNotIn("Qwen",p10.MODEL_URL)
        self.assertNotIn("from openai import",text)
        self.assertNotIn("accepted_ice_write(",text)
        self.assertNotIn("compose_or_deploy_authorized=True",text)
    def test_explicit_rejects(self):
        with self.assertRaisesRegex(RuntimeError,"MPAI05_P10_EXPLICIT_DENIAL"):
            p10.require(False,"EXPLICIT_DENIAL")
if __name__=="__main__":unittest.main()

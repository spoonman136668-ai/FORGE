"""P14 scorer-custody guards, synthetic only; no internet or model."""
from pathlib import Path
import inspect
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import mpai05_p14_scorer_calibration as c

class FakeScorer:
    @staticmethod
    def eval_name(spec):return spec.split("|",1)[0]
    @staticmethod
    def extract_boxed_answer(t):return t[len("\\boxed{"):-1]
    @staticmethod
    def eval_from_spec(spec,pred,gold):
        return pred==gold
    @staticmethod
    def score_to_bool(value):return bool(value)

class P14ScorerTests(unittest.TestCase):
    def test_frozen_source_and_cohort(self):
        self.assertEqual(c.COHORT_SHA,
          "103dbf87dda69f03b32f4c6a3a987b5ab5b7a8d3c3ceeb11f223ad5cf358ae52")
        self.assertEqual(c.OFFICIAL_BLOB,
          "6197efa64d1d47bff73c2523f4728c41ec78fd74")
    def test_model_calls_intentionally_zero(self):
        txt=Path(c.__file__).read_text("utf-8")
        for forbidden in ("Llama(", "create_chat_completion(", "from openai import",
                          "write_accepted_ice(", "promote_candidate("):
            self.assertNotIn(forbidden,txt)
        self.assertIn("MPAI05_P14_MODEL_CALLS=0",txt)
    def test_same_official_adapter(self):
        text=Path(c.__file__).read_text("utf-8")
        self.assertIn("p10.official_grade(",text)
        self.assertIn("scorer.extract_boxed_answer(",text)
        self.assertIn("p10.official_scorer(",text)
        self.assertNotIn("eval_from_spec(",text)
    def test_positive_control_with_synthetic_reference(self):
        s=FakeScorer()
        row=c.reference_control(s,"norm_phrase_set_match","Synthetic Correct")
        self.assertEqual(row,{"kind":"norm_phrase_set_match",
           "positive":True,"negative":False,"boxed_identity":True})
    def test_judge_skip_does_not_call_official_evaluator(self):
        s=MagicMock()
        s.eval_name.return_value="llm_abstention_checker"
        out=c.reference_control(s,"llm_abstention_checker","Synthetic Correct")
        self.assertEqual(out["kind"],"UNSCORABLE")
        s.eval_from_spec.assert_not_called()
        s.extract_boxed_answer.assert_not_called()
    def test_unknown_scorer_skip(self):
        s=MagicMock();s.eval_name.return_value="not_approved_judge"
        x=c.reference_control(s,"not_approved_judge","answer")
        self.assertIsNone(x["positive"])
    def test_no_empty_or_nonstring_gold_allowed(self):
        with self.assertRaisesRegex(RuntimeError,"SOURCE_SCHEMA"):
            c.reference_control(FakeScorer(),"norm_phrase_set_match",None)
    def test_negative_control_colliding_with_gold_denied(self):
        with self.assertRaisesRegex(RuntimeError,"NEGATIVE_COLLISION"):
            c.reference_control(FakeScorer(),"norm_phrase_set_match",
                                "P14_DELIBERATELY_INCORRECT_9F2C6B")
if __name__=="__main__":unittest.main()

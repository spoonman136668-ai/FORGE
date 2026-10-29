"""P17 positive/negative scorer and gold-after-context attribution controls."""
import pathlib
import sys
import unittest
from unittest.mock import MagicMock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
import mpai05_p17_evidence_attribution as p17

class SyntheticScorer:
    @staticmethod
    def eval_name(spec):return spec.split("|",1)[0]
    @staticmethod
    def extract_boxed_answer(s):return s[len("\\boxed{"):-1]
    @staticmethod
    def eval_from_spec(spec,pred,gold):return pred==gold
    @staticmethod
    def score_to_bool(x):return bool(x)

class TestP17Attribution(unittest.TestCase):
    def test_exact_new_source(self):
        self.assertEqual(p17.COHORT,
          "81be63f61ee45231985c9341419a3abb1f42f40930a95be8337d16375ba1b696")
        self.assertNotEqual(p17.COHORT,p17.p15.PRIOR_COHORT_SHA)
    def test_method_count_and_pure_scoring(self):
        self.assertEqual(p17.CONDITIONS,
          ("all_source","p10_extracted","lexical_retrieved","idf_retrieved"))
        self.assertEqual(p17.GRADED,("official_gradeable","unscorable"))
    def test_positive_reference_and_negative_control(self):
        kind,r=p17.score_controls(SyntheticScorer(),"norm_phrase_set_match","synthetic gold")
        self.assertEqual(kind,"official_gradeable")
        self.assertTrue(r["positive"])
        self.assertFalse(r["negative"])
    def test_judge_is_never_invoked(self):
        fake=MagicMock()
        fake.eval_name.return_value="llm_abstention_checker"
        kind,r=p17.score_controls(fake,"llm_abstention_checker","gold")
        self.assertEqual(kind,"unscorable")
        fake.eval_from_spec.assert_not_called()
    def test_known_correct_rejected_fails_closed(self):
        fake=MagicMock()
        fake.eval_name.return_value="norm_phrase_set_match"
        fake.extract_boxed_answer.return_value="known"
        fake.eval_from_spec.return_value=False
        fake.score_to_bool.return_value=False
        with self.assertRaisesRegex(RuntimeError,"KNOWN_CORRECT_SCORER_REJECTED"):
            p17.score_controls(fake,"norm_phrase_set_match","known")
    def test_wrong_answer_accepted_fails_closed(self):
        fake=MagicMock()
        fake.eval_name.return_value="norm_phrase_set_match"
        fake.extract_boxed_answer.return_value="known"
        fake.eval_from_spec.return_value=True
        fake.score_to_bool.return_value=True
        with self.assertRaisesRegex(RuntimeError,"DELIBERATELY_WRONG_SCORER_ACCEPTED"):
            p17.score_controls(fake,"norm_phrase_set_match","known")
    def test_no_model_inference_or_production_writer(self):
        s=pathlib.Path(p17.__file__).read_text("utf-8")
        for phrase in ("create_chat_completion(", "Llama(", "openai.OpenAI(",
                       "write_accepted_ice(", "promote_candidate("):
            self.assertNotIn(phrase,s)
        self.assertIn("MPAI05_P17_MODEL_CALLS=0",s)
        self.assertIn("MPAI05_P17_SCIENTIFIC_ACCEPTANCE=FALSE",s)
    def test_original_retrieval_called_before_gold_control(self):
        import inspect
        s=inspect.getsource(p17.diagnostic)
        self.assertLess(s.index("contexts,cpu=p16.make_context"),
                        s.index("grade_kind,control=score_controls"))
        self.assertLess(s.index("frozen={"),s.index("grade_kind,control=score_controls"))

if __name__=="__main__":unittest.main()

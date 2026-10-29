"""P13 original-Windows preflight guards; synthetic inputs, zero model calls."""
import inspect
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import mpai05_p13_behavioral_validation as p13

class P13SourceAndControls(unittest.TestCase):
    def test_frozen_arms(self):
        self.assertEqual(p13.ARMS,("no_memory","lexical_memory",
            "idf_diverse_memory","idf_diverse_reflection",
            "char_matched_placebo"))
    def test_same_inference_budgets(self):
        self.assertEqual(p13.MAX_OUTPUT,96)
        self.assertEqual(p13.MAX_INPUT,2048)
        self.assertEqual(p13.MAX_CONTEXT,2300)
        self.assertEqual(p13.SEED,137)
    def test_same_public_source_and_weights(self):
        self.assertEqual(p13.COHORT_SHA,
           "103dbf87dda69f03b32f4c6a3a987b5ab5b7a8d3c3ceeb11f223ad5cf358ae52")
        self.assertEqual(p13.MODEL_SHA,
           "2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2")
        self.assertEqual(p13.P10_SOURCE_BLOB,"7bd698e3265cc41ee4d286461980d7586a25ac99")
        self.assertEqual(p13.P12_SOURCE_BLOB,"de13820b5598e2cabf8432481b9a34abfd6e461b")
    def test_question_to_context_cannot_take_reference(self):
        self.assertEqual(list(inspect.signature(p13.prepare_contexts).parameters),
                         ["question","ids","memory"])
        self.assertEqual(list(inspect.signature(p13.system_prompt).parameters),["arm"])
    def test_memory_only_system_equal(self):
        self.assertEqual(p13.system_prompt("lexical_memory"),
                         p13.system_prompt("idf_diverse_memory"))
        self.assertEqual(p13.system_prompt("no_memory"),
                         p13.p10.SYSTEM["no_memory"])
        self.assertNotEqual(p13.system_prompt("idf_diverse_memory"),
                            p13.system_prompt("idf_diverse_reflection"))
    def test_source_haystack_and_matching_placebo(self):
        memory={}
        ids=[]
        for i in range(100):
            name=f"t{i:04}"
            ids.append(name)
            memory[name]=[
                "Goal: account profile change",
                "Action: open customer settings",
                "accessibility_tree: a shipping address",
            ]
        memory["foreign"]=["secret outside haystack"]
        ctx,cpu=p13.prepare_contexts("Where is the shipping address?",ids,memory)
        self.assertEqual(ctx["no_memory"],"")
        self.assertEqual(ctx["idf_diverse_memory"],ctx["idf_diverse_reflection"])
        self.assertEqual(len(ctx["idf_diverse_memory"]),len(ctx["char_matched_placebo"]))
        self.assertNotIn("secret outside haystack",str(ctx))
        self.assertTrue(all(len(v)<=2308 for v in ctx.values()))
        self.assertEqual(cpu["idf_diverse_memory"],cpu["idf_diverse_reflection"])
        self.assertEqual(cpu["idf_diverse_memory"],cpu["char_matched_placebo"])
        self.assertGreater(cpu["idf_diverse_memory"],0)
    def test_wrong_case_size_denied(self):
        with self.assertRaisesRegex(RuntimeError,"CASE_INPUT_FORMAT"):
            p13.prepare_contexts("q",["one"],{"one":["action: hello"]})
    def test_missing_trajectory_denied(self):
        with self.assertRaisesRegex(RuntimeError,"CASE_SOURCE_MISSING"):
            p13.prepare_contexts("q",[f"x{i}" for i in range(100)],{})
    def test_exact_grade_denominator(self):
        fake=[]
        for arm in p13.ARMS:
            for i in range(16):
                fake.append({
                    "arm":arm,"case_digest":f"case{i:02}",
                    "official_score":False if i<11 else None,
                    "hit_output_cap":False,"boxed_nonempty":True,
                    "input_tokens":100,"output_tokens":10,
                    "inference_ms":20,"retrieval_cpu_ns":100,
                    "context_chars":200})
        result=p13.summarize(fake)
        self.assertEqual(len(result),5)
        self.assertTrue(all(result[a]["official_graded"]==11 for a in result))
        self.assertTrue(all(result[a]["official_correct"]==0 for a in result))
        self.assertTrue(all(result[a]["official_unscorable"]==5 for a in result))
    def test_missing_grade_denied(self):
        fake=[]
        for arm in p13.ARMS:
            for i in range(16):
                fake.append({"arm":arm,"case_digest":f"case{i:02}",
                    "official_score":None if i==0 or i>=11 else False,
                    "hit_output_cap":False,"boxed_nonempty":True,
                    "input_tokens":10,"output_tokens":10,
                    "inference_ms":20,"retrieval_cpu_ns":5,"context_chars":100})
        with self.assertRaisesRegex(RuntimeError,"DETERMINISTIC_GRADING_DENOMINATOR"):
            p13.summarize(fake)
    def test_no_scheduled_or_memory_writer(self):
        content=Path(p13.__file__).read_text(encoding="utf-8")
        for prohibited in ("openai.OpenAI(", "write_accepted_ice(",
                           "promote_candidate(", "Qwen2", "pip install"):
            self.assertNotIn(prohibited,content)
        self.assertIn("MPAI05_P13_SCIENTIFIC_ACCEPTANCE=FALSE",content)
        self.assertIn("MPAI05_P13_PRODUCTION_WRITES=0",content)

if __name__=="__main__":
    unittest.main()

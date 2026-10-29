"""P16 synthetic control tests; zero source download or model inference."""
import inspect
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
import mpai05_p16_capacity_vs_memory as p16

class P16Controls(unittest.TestCase):
    def test_model_set_and_exact_source(self):
        self.assertEqual(p16.MODELS,("smollm2_360m","smollm2_1p7b"))
        self.assertEqual(p16.WEIGHTS["smollm2_1p7b"][2],p16.p15.MODEL_SHA256)
        self.assertEqual(p16.WEIGHTS["smollm2_360m"][2],
           "2fa3f013dcdd7b99f9b237717fa0b12d75bbb89984cc1274be1471a465bac9c2")
        self.assertNotEqual(p16.WEIGHTS["smollm2_360m"][2],
                            p16.WEIGHTS["smollm2_1p7b"][2])
    def test_new_development_cohort_not_old(self):
        self.assertEqual(p16.COHORT,
           "81be63f61ee45231985c9341419a3abb1f42f40930a95be8337d16375ba1b696")
        self.assertNotEqual(p16.COHORT,p16.p15.PRIOR_COHORT_SHA)
    def test_same_generation_budget(self):
        self.assertEqual(p16.p10.MAX_OUTPUT_TOKENS,96)
        self.assertEqual(p16.p10.MAX_INPUT_TOKENS,2048)
        self.assertEqual(p16.p10.SEED,137)
        self.assertEqual(p16.p10.CONTEXT_CHARS,2300)
    def test_three_matched_arms(self):
        self.assertEqual(p16.ARMS,
           ("no_memory","lexical_memory","idf_diverse_memory"))
        self.assertEqual(list(inspect.signature(p16.make_context).parameters),
                         ["question","ids","memory"])
    def test_contexts_from_only_case_ids(self):
        memory={f"t{i:03d}":["Goal: customer address",
          "Action: edit shipping address","accessibility_tree: saved address"]
          for i in range(100)}
        memory["foreign"]=["Goal: secret other task"]
        ids=[f"t{i:03d}" for i in range(100)]
        contexts,cpu=p16.make_context("Where is shipping address?",ids,memory)
        self.assertEqual(contexts["no_memory"],"")
        self.assertNotIn("secret other task",str(contexts))
        self.assertTrue(all(len(v)<=2308 for v in contexts.values()))
        self.assertGreater(cpu["idf_diverse_memory"],0)
    def test_case_ids_missing_fail_closed(self):
        with self.assertRaisesRegex(RuntimeError,"CASE_HISTORY_ID_DRIFT"):
            p16.make_context("q",["noid"]*100,{})
    def test_aggregate_matched_grader(self):
        trials=[]
        for arm in p16.ARMS:
            for i in range(16):
                trials.append({"arm":arm,"case_sha256":str(i),
                  "official_grade":False if i<11 else None,
                  "input_tokens":20,"output_tokens":10,
                  "inference_ms":10,"retrieval_cpu_ns":4,
                  "output_cap_hit":False,"context_chars":5})
        x,ids=p16.aggregate(trials)
        self.assertEqual(len(ids),11)
        self.assertEqual(len(x),3)
        self.assertEqual(x["no_memory"]["correct"],0)
        self.assertEqual(x["lexical_memory"]["unscorable"],5)
    def test_aggregate_rejects_mismatched_grader(self):
        trials=[]
        for arm in p16.ARMS:
            for i in range(16):
                scorable=i<11
                if arm=="idf_diverse_memory":scorable=1<=i<=11
                trials.append({"arm":arm,"case_sha256":str(i),
                  "official_grade":False if scorable else None,
                  "input_tokens":20,"output_tokens":10,
                  "inference_ms":10,"retrieval_cpu_ns":4,
                  "output_cap_hit":False,"context_chars":5})
        with self.assertRaisesRegex(RuntimeError,"SCORABLE_SET_INCONSISTENT"):
            p16.aggregate(trials)
    def test_no_paid_api_or_writer(self):
        src=pathlib.Path(p16.__file__).read_text("utf-8")
        for bad in ("openai.OpenAI(", "write_accepted_ice(",
                    "promote_candidate(", "Qwen2", "pip install"):
            self.assertNotIn(bad,src)
        self.assertIn("MPAI05_P16_SCIENTIFIC_ACCEPTANCE=FALSE",src)
        self.assertIn("MPAI05_P16_PRODUCTION_WRITES=0",src)
if __name__=="__main__":unittest.main()

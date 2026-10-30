"""G67 immutable-source and negative-criteria tests; no GPU dependency."""
import importlib.util
from pathlib import Path
import copy
import unittest

FILE = Path(__file__).with_name("g67_fp32_head.py")
spec = importlib.util.spec_from_file_location("g67", FILE)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

def fixture():
    cases = []
    for i, (anchor, task, ctx) in enumerate(g.CASES):
        cases.append({"case_index":i,"anchor":anchor,"task":task,"context_tokens":ctx,
                      "variants":{
                          "fp16_control":{"median_seconds":{"baseline":1.0,"candidate":0.75},
                                          "peak_allocated_mib":{"candidate":2000}},
                          "fp16_backbone_fp32_head":{
                              "comparison":{"exact":True},
                              "median_seconds":{"baseline":1.10,"candidate":0.60},
                              "peak_allocated_mib":{"candidate":2100}}
                      }})
    forced = {mode:[{"greedy_argmax_id":29871,"exact_max_tie_count":1}
                    for _ in range(3)] for mode in g.MODES}
    return cases, forced

class Contract(unittest.TestCase):
    def test_pinned_immutable_parent(self):
        self.assertEqual(g.source_identity()["g65_source_blob"],
                         "6dd9bbed1793237fa5d4d34e7c9762aaec45471a")
    def test_five_cases_frozen(self):
        self.assertEqual(g.CASES, ((.73,"natural_continuation",1536),
            (.17,"natural_continuation",512),(.17,"source_question",512),
            (.45,"natural_continuation",1536),(.45,"source_question",1536)))
        self.assertEqual(g.WARMUPS,2)
        self.assertEqual(g.PAIRS,3)
    def test_true_exact_diff(self):
        a=list(range(64));b=a[:];b[48]=29871
        self.assertFalse(g.same_tokens(a,b)["exact"])
        self.assertEqual(g.same_tokens(a,b)["first_difference"],48)
        self.assertTrue(g.same_tokens(a,a)["exact"])
    def test_all_good_is_only_research_screen(self):
        c,f=fixture()
        out=g.classify(c,f)
        self.assertEqual(out["engineering_screen"],"TECHNICAL_SCREEN_PASS_ONLY")
        self.assertEqual(out["scientific_acceptance"],"NOT_GRANTED")
        self.assertEqual(out["prior_g63_generalization"],"FAIL_NO_GO_UNCHANGED")
    def test_num_tie_rejected(self):
        c,f=fixture()
        f["cached_one_by_one"][0]["exact_max_tie_count"]=2
        self.assertEqual(g.classify(c,f)["numerical_localized_fix"],
                         "NUMERICAL_HYPOTHESIS_REJECTED")
        self.assertEqual(g.classify(c,f)["engineering_screen"],"NO_GO_ENGINEERING")
    def test_wrong_argmax_rejected(self):
        c,f=fixture()
        f["full_no_cache"][2]["greedy_argmax_id"]=7866
        self.assertEqual(g.classify(c,f)["engineering_screen"],"NO_GO_ENGINEERING")
    def test_exact_parity_rejected(self):
        c,f=fixture()
        c[4]["variants"]["fp16_backbone_fp32_head"]["comparison"]["exact"]=False
        self.assertEqual(g.classify(c,f)["engineering_screen"],"NO_GO_ENGINEERING")
    def test_memory_excess_rejected(self):
        c,f=fixture()
        c[2]["variants"]["fp16_backbone_fp32_head"]["peak_allocated_mib"]["candidate"]=2450
        self.assertEqual(g.classify(c,f)["engineering_screen"],"NO_GO_ENGINEERING")
    def test_latency_excess_rejected(self):
        c,f=fixture()
        c[3]["variants"]["fp16_backbone_fp32_head"]["median_seconds"]["baseline"]=1.30
        self.assertEqual(g.classify(c,f)["engineering_screen"],"NO_GO_ENGINEERING")
    def test_speed_floor_rejected(self):
        c,f=fixture()
        for x in c[1:]:
            x["variants"]["fp16_backbone_fp32_head"]["median_seconds"]["candidate"]=1.08
        self.assertEqual(g.classify(c,f)["engineering_screen"],"NO_GO_ENGINEERING")
    def test_missing_repeats_blocked(self):
        c,f=fixture()
        f["full_no_cache"].pop()
        with self.assertRaises(ValueError):
            g.classify(c,f)
    def test_no_promotion_or_fp32_whole_model(self):
        text=FILE.read_text(encoding="utf-8")
        self.assertIn('"scientific_acceptance": "NOT_GRANTED"',text)
        self.assertIn('"g63_generalization": "FAIL_NO_GO_UNCHANGED"',text)
        self.assertIn('model.set_output_embeddings(FP32OutputHead(head))',text)
        self.assertIn('F.linear(hidden.float(), self.weight, self.bias)',text)
        self.assertIn('torch.backends.cuda.matmul.allow_tf32 = False',text)

if __name__ == "__main__":
    unittest.main()

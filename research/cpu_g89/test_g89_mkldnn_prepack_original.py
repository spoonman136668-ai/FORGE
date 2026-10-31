"""G89 deterministic contract tests; no model download or benchmark."""
import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).with_name("g89_mkldnn_prepack_original.py")
S=importlib.util.spec_from_file_location("g89_mkldnn_prepack",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class G89PrepackAdmission(unittest.TestCase):
    def test_frozen_contract(self):
        g.contract()
        self.assertEqual(g.PREREG,"09a5849d63fab89f187a31501335b29886c92f26")
        self.assertEqual((g.OFFSET,g.CASES,g.REPEATS,g.TOKENS,g.CPU_BUDGET,g.HORIZON),(192,12,4,8,3,1000))
        self.assertEqual(g.ARMS,("original_conv1d2","mkldnn_prepacked_linear2"))

    def test_model_dataset_identity(self):
        self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_REV,"3101c7d5072418e28b9008a6636bde82a006892c")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")

    def trial(self,i,r,eager=100_000_000,candidate=70_000_000):
        m={
          "original_conv1d2":{"wall_ns":eager,"process_cpu_ns":80_000_000,"rss_sampled":9000,"output_sha256":"same"},
          "mkldnn_prepacked_linear2":{"wall_ns":candidate,"process_cpu_ns":80_000_000,"rss_sampled":9000,"output_sha256":"same"}}
        return {"sample_index":i,"rep":r+1,"order":g.schedule(i,r),"measure":m}

    def trials(self,eager=100_000_000,candidate=70_000_000):
        return [self.trial(i,r,eager,candidate) for i in range(g.CASES) for r in range(g.REPEATS)]

    def test_positive_fixture_only_and_prepack_amortization(self):
        _,s,d=g.decide(self.trials(),.001)
        self.assertEqual(d,"MKLDNN_PREPACK_PASS")
        self.assertEqual(s["timed_authentic_responses"],96)
        self.assertEqual(s["timed_authentic_generated_tokens"],768)
        self.assertLessEqual(s["break_even_full_responses"],1000)
        self.assertLessEqual(s["amortized_total_wall_ratio_at_1000_responses"],.95)

    def test_negative_fixture_only(self):
        self.assertEqual(g.decide(self.trials(100_000_000,95_000_000),.001)[2],"MKLDNN_PREPACK_NO_GO")

    def test_conversion_cost_not_hidden(self):
        self.assertEqual(g.decide(self.trials(),100.0)[2],"MKLDNN_PREPACK_NO_GO")

    def test_exactness_mismatch_fails_closed(self):
        xs=self.trials();xs[0]["measure"]["mkldnn_prepacked_linear2"]["output_sha256"]="different"
        with self.assertRaisesRegex(RuntimeError,"G89_ORIGINAL_TOKEN_PARITY_ERROR"):
            g.decide(xs,.001)

    def test_actual_backend_dispatch_is_required_in_source(self):
        src=P.read_text(encoding="utf-8")
        for item in ("torch.utils.mkldnn import to_mkldnn","to_mkldnn(candidate,dtype=torch.float32)",
                     'x["key"]=="aten::mkldnn_linear"',
                     "G89_CANDIDATE_MKLDNN_LINEAR_NOT_DISPATCHED",
                     "G89_BASELINE_MKLDNN_LINEAR_DISPATCHED",
                     '"scientific_acceptance":"NOT_GRANTED"',
                     '"promotion_allowed":False'):
            self.assertIn(item,src)
        self.assertNotIn("model.train(",src)
        self.assertNotIn("model.cuda(",src)

if __name__=="__main__":unittest.main()

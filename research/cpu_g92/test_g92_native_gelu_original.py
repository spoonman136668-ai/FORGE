"""G92 deterministic contract and fail-closed native GELU tests; no model downloads."""
import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).with_name("g92_native_gelu_original.py")
S=importlib.util.spec_from_file_location("g92_native_gelu",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class G92NativeGELUAdmission(unittest.TestCase):
    def test_frozen_identity_and_thresholds(self):
        g.contract()
        self.assertEqual(g.PREREG,"bdacb37f4614f4de646092089016a452acf06d9e")
        self.assertEqual((g.OFFSET,g.CASES,g.REPEATS,g.TOKENS,g.CPU_BUDGET),(228,12,4,8,3))
        self.assertEqual(g.ARMS,("original_newgelu2","native_gelu_tanh2"))
        self.assertEqual(g.THRESHOLDS,{"prefill_speedup_min":1.15,"full_speedup_min":1.10,
            "min_paired":.90,"p95_max":1.10,"rss_max":1.10,"cpu_max":1.10})

    def test_model_dataset_identity(self):
        self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_REV,"3101c7d5072418e28b9008a6636bde82a006892c")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")

    def make_trial(self,i,r,fast=True):
        base={"prefill_ns":100_000_000,"cached_forward_ns":50_000_000,"token_selection_ns":1000,
              "full_ns":160_000_000,"cpu_ns":140_000_000,"rss_bytes":10000,"output_sha256":"same"}
        cand={"prefill_ns":70_000_000 if fast else 95_000_000,"cached_forward_ns":50_000_000,
              "token_selection_ns":1000,"full_ns":130_000_000 if fast else 155_000_000,
              "cpu_ns":130_000_000,"rss_bytes":10000,"output_sha256":"same"}
        return {"original_newgelu2":base,"native_gelu_tanh2":cand}

    def dispatch(self):
        return {"baseline_gelu_events":0,"baseline_tanh_events":12,"baseline_pow_events":12,
          "candidate_gelu_events":12,"candidate_tanh_events":0,"candidate_pow_events":0}

    def test_positive_fixture_only(self):
        rows=[self.make_trial(i,r,True) for i in range(g.CASES) for r in range(g.REPEATS)]
        summaries,metrics,decision=g.decide(rows,self.dispatch())
        self.assertEqual(decision,"NATIVE_GELU_PASS")
        self.assertEqual(metrics["timed_authentic_responses"],96)
        self.assertEqual(metrics["timed_authentic_generated_tokens"],768)

    def test_negative_fixture_only(self):
        rows=[self.make_trial(i,r,False) for i in range(g.CASES) for r in range(g.REPEATS)]
        self.assertEqual(g.decide(rows,self.dispatch())[2],"NATIVE_GELU_NO_GO")

    def test_dispatch_absence_blocks_not_no_go(self):
        rows=[self.make_trial(i,r,True) for i in range(g.CASES) for r in range(g.REPEATS)]
        bad=self.dispatch();bad["candidate_gelu_events"]=0
        with self.assertRaisesRegex(RuntimeError,"G92_NATIVE_GELU_DISPATCH_NOT_PROVEN"):
            g.decide(rows,bad)

    def test_exactness_mismatch_fails_closed(self):
        rows=[self.make_trial(i,r,True) for i in range(g.CASES) for r in range(g.REPEATS)]
        rows[0]["native_gelu_tanh2"]["output_sha256"]="changed"
        with self.assertRaisesRegex(RuntimeError,"G92_ORIGINAL_TOKEN_PARITY_ERROR"):
            g.decide(rows,self.dispatch())

    def test_no_model_mutation_or_promotion(self):
        source=P.read_text(encoding="utf-8")
        for token in ('"scientific_acceptance": "NOT_GRANTED"',
          '"promotion_allowed": False','torch.nn.functional.gelu(x, approximate="tanh")',
          'G92_NATIVE_GELU_DISPATCH_MISSING','G92_EXACT_TOKEN_MISMATCH'):
            self.assertIn(token,source)
        self.assertNotIn("model.train(",source)
        self.assertNotIn("model.cuda(",source)

if __name__=="__main__":unittest.main()

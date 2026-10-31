"""G88 deterministic preregistration and fail-closed backend admission tests."""
import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).with_name("g88_mkldnn_original.py")
S=importlib.util.spec_from_file_location("g88_mkldnn",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class G88MKLDNNAdmission(unittest.TestCase):
    def test_frozen_identity_budget(self):
        g.contract()
        self.assertEqual(g.PREREG,"c5247d658eaf2c0e226025660bbe8cb62b0f7b57")
        self.assertEqual((g.OFFSET,g.CASES,g.REPEATS,g.TOKENS,g.CPU_BUDGET),(180,12,4,8,3))
        self.assertEqual(g.ARMS,("mkldnn_enabled2","mkldnn_disabled2"))

    def test_original_source_identity(self):
        self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_REV,"3101c7d5072418e28b9008a6636bde82a006892c")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")

    def trial(self,i,rep,on=70,off=100):
        m={
          "mkldnn_enabled2":{"wall_ns":on,"process_cpu_ns":80,"rss_sampled":9000,"output_sha256":"same"},
          "mkldnn_disabled2":{"wall_ns":off,"process_cpu_ns":80,"rss_sampled":9000,"output_sha256":"same"}}
        return {"sample_index":i,"rep":rep+1,"order":g.schedule(i,rep),"measure":m}

    def trials(self,on=70,off=100):
        return [self.trial(i,r,on,off) for i in range(g.CASES) for r in range(g.REPEATS)]

    def test_frozen_positive_fixture_only(self):
        arms,summary,decision=g.decide(self.trials())
        self.assertEqual(decision,"MKLDNN_PASS")
        self.assertEqual(summary["timed_authentic_responses"],96)
        self.assertEqual(summary["timed_authentic_generated_tokens"],768)

    def test_frozen_negative_fixture_only(self):
        self.assertEqual(g.decide(self.trials(95,100))[2],"MKLDNN_NO_GO")

    def test_exactness_mismatch_fails_closed(self):
        x=self.trials();x[0]["measure"]["mkldnn_enabled2"]["output_sha256"]="wrong"
        with self.assertRaisesRegex(RuntimeError,"G88_ORIGINAL_TOKEN_PARITY_ERROR"):
            g.decide(x)

    def test_no_promotion_or_weight_change(self):
        src=P.read_text(encoding="utf-8")
        for token in ('"scientific_acceptance":"NOT_GRANTED"','"promotion_allowed":False',
                      'torch.backends.mkldnn.enabled=enabled',
                      'torch.backends.mkldnn.verbose(torch.backends.mkldnn.VERBOSE_ON)',
                      'G88_ENABLED_ARM_DID_NOT_DISPATCH_ONEDNN',
                      'G88_DISABLED_ARM_STILL_DISPATCHED_ONEDNN'):
            self.assertIn(token,src)
        self.assertNotIn("model.train(",src)
        self.assertNotIn("model.cuda(",src)

if __name__=="__main__":unittest.main()

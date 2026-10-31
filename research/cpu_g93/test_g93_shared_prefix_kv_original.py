"""G93 frozen shared-prefix KV reuse admission and aggregation tests."""
import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).with_name("g93_shared_prefix_kv_original.py")
S=importlib.util.spec_from_file_location("g93_shared_prefix",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class G93SharedPrefixAdmission(unittest.TestCase):
    def test_frozen_contract(self):
        g.contract()
        self.assertEqual(g.PREREG,"047ec14a2e27eedc0bb1e47e050fd4a071b94a6f")
        self.assertEqual((g.OFFSET,g.CASES,g.REPEATS,g.TOKENS,g.CPU_BUDGET),(240,12,4,8,3))
        self.assertEqual(g.ARMS,("full_prompt_prefill2","shared_prefix_kv_reuse2"))
        self.assertEqual(g.THRESHOLDS,{"cohort_speedup_min":1.15,"min_paired":.90,
          "p95_amortized_max":1.10,"cpu_max":1.10,"rss_max":1.10})

    def test_model_and_dataset_identity(self):
        self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_REV,"3101c7d5072418e28b9008a6636bde82a006892c")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")

    def row(self,i,fast=True):
        return {"source_row":100+i,"request_wall_ns":90_000_000 if fast else 100_000_000,
          "prefix_setup_share_ns":2_000_000 if fast else 20_000_000,"output_sha256":"h"+str(i)}

    def arm(self,kind,fast=True):
        baseline=(kind=="baseline")
        rows=[]
        for i in range(12):
            row=self.row(i,fast and not baseline)
            if baseline:
                row["request_wall_ns"]=100_000_000
                row["prefix_setup_share_ns"]=0
            elif not fast:
                row["request_wall_ns"]=105_000_000
                row["prefix_setup_share_ns"]=20_000_000
            rows.append(row)
        hashes={str(x["source_row"]):x["output_sha256"] for x in rows}
        return {"cohort_wall_ns":1_200_000_000 if baseline else (800_000_000 if fast else 1_500_000_000),
          "cohort_cpu_ns":1_100_000_000 if baseline else (900_000_000 if fast else 1_400_000_000),
          "prefix_setup_ns":0 if baseline else (24_000_000 if fast else 240_000_000),
          "request_rows":rows,"output_hashes":hashes,"responses":12,"generated_tokens":96,
          "max_sampled_rss_bytes":100_000_000 if fast or baseline else 120_000_000}

    def trials(self,fast=True):
        return [{"rep":i+1,"arms":{"full_prompt_prefill2":self.arm("baseline",True),
          "shared_prefix_kv_reuse2":self.arm("candidate",fast)}} for i in range(g.REPEATS)]

    def test_positive_fixture_only(self):
        metrics,decision=g.decide(self.trials(True))
        self.assertEqual(decision,"SHARED_PREFIX_KV_PASS")
        self.assertEqual(metrics["timed_authentic_responses"],96)
        self.assertEqual(metrics["timed_authentic_generated_tokens"],768)

    def test_negative_fixture_only(self):
        self.assertEqual(g.decide(self.trials(False))[1],"SHARED_PREFIX_KV_NO_GO")

    def test_exact_output_mismatch_fails_closed(self):
        rows=self.trials(True)
        rows[0]["arms"]["shared_prefix_kv_reuse2"]["output_hashes"]["100"]="wrong"
        with self.assertRaisesRegex(RuntimeError,"G93_ORIGINAL_TOKEN_PARITY_ERROR"):
            g.decide(rows)

    def test_missing_request_fails_closed(self):
        rows=self.trials(True)
        rows[0]["arms"]["shared_prefix_kv_reuse2"]["responses"]=11
        with self.assertRaisesRegex(RuntimeError,"G93_INCOMPLETE_REQUEST_COHORT"):
            g.decide(rows)

    def test_cache_copy_and_prefix_cost_are_charged(self):
        source=P.read_text(encoding="utf-8")
        for token in ('copy.deepcopy(prefix_cache)','prefix_setup_ns//CASES',
          'SHARED_PREFIX_KV_PASS','SHARED_PREFIX_KV_NO_GO',
          '"scientific_acceptance":"NOT_GRANTED"','"promotion_allowed":False'):
            self.assertIn(token,source)

if __name__=="__main__":unittest.main()

"""G90 deterministic batching contract and aggregation tests; no model download."""
import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).with_name("g90_batching_original.py")
S=importlib.util.spec_from_file_location("g90_batching",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class G90BatchingAdmission(unittest.TestCase):
    def test_frozen_identity_and_arm_design(self):
        g.contract()
        self.assertEqual(g.PREREG,"76410a228cae6eb8f1afdd6462bb83ab6f4ec168")
        self.assertEqual((g.OFFSET,g.CASES,g.REPEATS,g.TOKENS,g.CPU_BUDGET),(204,12,4,8,3))
        self.assertEqual(g.BATCH_SIZES,(1,2,4,8,12))
        self.assertEqual(g.THRESHOLDS,{"throughput_speedup_min":1.20,
          "p95_group_latency_ratio_max":2.0,"rss_ratio_max":1.5,"cpu_per_token_ratio_max":1.5})

    def test_original_model_and_dataset_identity(self):
        self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_REV,"3101c7d5072418e28b9008a6636bde82a006892c")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")

    def test_group_schedule_covers_each_request_once(self):
        for n in g.BATCH_SIZES:
            for rep in range(g.REPEATS):
                groups=g.group_schedule(n,rep)
                flat=[i for batch in groups for i in batch]
                self.assertEqual(sorted(flat),list(range(g.CASES)))
                self.assertEqual(len(flat),len(set(flat)))
                self.assertTrue(all(0<len(batch)<=n for batch in groups))

    def make_run(self,arm,rep,wall,group_latency,hashes=None):
        groups=[]
        for i in range(0,g.CASES,arm):
            groups.append({"indices":list(range(i,min(g.CASES,i+arm))),"wall_ns":group_latency,
              "process_cpu_ns":100,"rss_sampled":1000})
        out=hashes or {str(i):"hash"+str(i) for i in range(g.CASES)}
        return {"wall_ns":wall,"process_cpu_ns":g.CASES*g.TOKENS*100,
          "max_sampled_rss_bytes":1000,"groups":groups,"output_hashes":out,
          "responses":g.CASES,"generated_tokens":g.CASES*g.TOKENS}

    def cohort(self,fast=True):
        trials=[]
        for rep in range(g.REPEATS):
            arms={}
            for n in g.BATCH_SIZES:
                # Fixture-only: baseline 100ms; batch candidates 70ms with bounded group completion.
                wall=100_000_000 if n==1 else (70_000_000 if fast else 105_000_000)
                glat=10_000_000 if n==1 else (15_000_000 if fast else 50_000_000)
                arms["batch"+str(n)]=self.make_run(n,rep,wall,glat)
            trials.append({"rep":rep+1,"arms":arms})
        return trials

    def test_positive_aggregation_fixture_only(self):
        summary,decision=g.decide(self.cohort(True))
        self.assertEqual(decision,"BATCHING_PASS")
        self.assertEqual(summary["timed_authentic_responses"],240)
        self.assertEqual(summary["timed_authentic_generated_tokens"],1920)
        self.assertIsNotNone(summary["selected_batch_size"])

    def test_negative_aggregation_fixture_only(self):
        self.assertEqual(g.decide(self.cohort(False))[1],"BATCHING_NO_GO")

    def test_cross_arm_exactness_mismatch_fails_closed(self):
        rows=self.cohort(True)
        rows[0]["arms"]["batch4"]["output_hashes"]["0"]="wrong"
        with self.assertRaisesRegex(RuntimeError,"G90_CROSS_ARM_OR_REPETITION_OUTPUT_MISMATCH"):
            g.decide(rows)

    def test_missing_request_group_fails_closed(self):
        rows=self.cohort(True)
        rows[0]["arms"]["batch8"]["responses"]=11
        with self.assertRaisesRegex(RuntimeError,"G90_INCOMPLETE_REQUEST_COHORT"):
            g.decide(rows)

    def test_no_promotion_or_altered_weights(self):
        src=P.read_text(encoding="utf-8")
        for item in ('"scientific_acceptance":"NOT_GRANTED"','"promotion_allowed":False',
          "position_ids=positions","next_positions=mask.sum(dim=-1,keepdim=True)",
          "BATCHING_PASS","BATCHING_NO_GO"):
            self.assertIn(item,src)
        self.assertNotIn("model.train(",src)
        self.assertNotIn("model.cuda(",src)

if __name__=="__main__":unittest.main()

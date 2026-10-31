"""CPU G91 deterministic bucketing and threshold admission tests; no model download."""
import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).with_name("g91_length_bucket_original.py")
S=importlib.util.spec_from_file_location("g91_length_bucket",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class G91LengthBucketAdmission(unittest.TestCase):
    def test_frozen_contract_and_disjoint_interval(self):
        g.contract()
        self.assertEqual(g.PREREG,"e04dfa901e36892ce6c2eea48bdb2e30ec26918a")
        self.assertEqual((g.OFFSET,g.CASES,g.REPEATS,g.TOKENS,g.CPU_BUDGET),(216,12,4,8,3))
        self.assertEqual(g.ARMS,("batch1","batch2_random","batch2_length","batch4_random","batch4_length"))
        self.assertEqual(g.THRESHOLDS,{"throughput_speedup_min":1.20,
          "p95_group_latency_ratio_max":2.0,"rss_ratio_max":1.5,"cpu_per_token_ratio_max":1.5})

    def test_source_and_model_identity(self):
        self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_REV,"3101c7d5072418e28b9008a6636bde82a006892c")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")

    def test_length_groups_are_sorted_and_cover_once(self):
        lengths=[11,4,9,3,8,6,7,5,10,2,12,1]
        for n in (1,2,4):
            groups=g.group_schedule(n,0,lengths,"length")
            flat=[i for group in groups for i in group]
            self.assertEqual(len(flat),12)
            self.assertEqual(sorted(flat),list(range(12)))
            self.assertEqual(flat,sorted(flat,key=lambda i:(lengths[i],i)))

    def test_random_groups_cover_once_and_are_distinct_from_length(self):
        lengths=[11,4,9,3,8,6,7,5,10,2,12,1]
        rand=g.group_schedule(2,0,lengths,"random")
        buck=g.group_schedule(2,0,lengths,"length")
        self.assertEqual(sorted(i for q in rand for i in q),list(range(12)))
        self.assertNotEqual(rand,buck)

    def make_arm(self,n,strategy,wall,group,pad=100):
        groups=[]
        indices=list(range(12))
        if strategy=="length":indices=sorted(indices,key=lambda i:(i, i))
        for i in range(0,12,n):
            chunk=indices[i:i+n]
            groups.append({"indices":chunk,"input_lengths":[10]*len(chunk),
              "padding_tokens":0,"wall_ns":group,"process_cpu_ns":100,
              "rss_sampled":1000})
        return {"wall_ns":wall,"process_cpu_ns":12*8*100,"max_sampled_rss_bytes":1000,
          "groups":groups,"output_hashes":{str(i):"hash"+str(i) for i in range(12)},
          "responses":12,"generated_tokens":96,"strategy":strategy}

    def fixture(self,length_beats=True):
        rows=[]
        for rep in range(g.REPEATS):
            arms={
             "batch1":self.make_arm(1,"random",100_000_000,10_000_000),
             "batch2_random":self.make_arm(2,"random",95_000_000,18_000_000),
             "batch2_length":self.make_arm(2,"length",70_000_000 if length_beats else 95_000_000,15_000_000),
             "batch4_random":self.make_arm(4,"random",105_000_000,35_000_000),
             "batch4_length":self.make_arm(4,"length",75_000_000 if length_beats else 105_000_000,16_000_000)}
            rows.append({"rep":rep+1,"arms":arms})
        return rows

    def test_positive_fixture_only(self):
        summary,decision=g.decide(self.fixture(True))
        self.assertEqual(decision,"LENGTH_BUCKET_PASS")
        self.assertEqual(summary["timed_authentic_responses"],240)
        self.assertEqual(summary["timed_authentic_generated_tokens"],1920)
        self.assertIn(summary["selected_arm"],("batch2_length","batch4_length"))

    def test_same_size_random_control_required(self):
        self.assertEqual(g.decide(self.fixture(False))[1],"LENGTH_BUCKET_NO_GO")

    def test_exactness_and_complete_cohort_fail_closed(self):
        rows=self.fixture(True)
        rows[0]["arms"]["batch2_length"]["output_hashes"]["0"]="changed"
        with self.assertRaisesRegex(RuntimeError,"G91_CROSS_ARM_OR_REPETITION_OUTPUT_MISMATCH"):
            g.decide(rows)
        rows=self.fixture(True)
        rows[0]["arms"]["batch4_random"]["responses"]=11
        with self.assertRaisesRegex(RuntimeError,"G91_INCOMPLETE_REQUEST_COHORT"):
            g.decide(rows)

    def test_no_model_mutation_or_promotion(self):
        source=P.read_text(encoding="utf-8")
        for token in ('"scientific_acceptance": "NOT_GRANTED"','"promotion_allowed": False',
          'strategy=="length"','input_lengths','padding_tokens','LENGTH_BUCKET_PASS','LENGTH_BUCKET_NO_GO'):
            self.assertIn(token,source)
        self.assertNotIn("model.train(",source)
        self.assertNotIn("model.cuda(",source)

if __name__=="__main__":unittest.main()

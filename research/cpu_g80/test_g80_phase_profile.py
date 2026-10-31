"""Frozen G80 source-only negative and phase accounting tests, no model or network."""
import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).with_name("g80_phase_profile.py")
S=importlib.util.spec_from_file_location("g80_phase_profile",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class G80OriginalDiagnosticGuards(unittest.TestCase):
    def test_original_prereg_and_custody(self):
        g.contract()
        self.assertEqual(g.PREREG,"b2d8b285b004cb2e496f7541a4c8edd5d545e329")
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
    def test_original_rank_disjoint_and_duplicates(self):
        rows=[{"instruction":"Independent public source item "+str(i),"category":"math"} for i in range(145)]
        selected=g.rank_original(rows,132)
        self.assertEqual(len(selected),132)
        self.assertEqual(len({x["source_row"] for x in selected}),132)
        self.assertTrue({x["source_row"] for x in selected[120:132]}.isdisjoint(
                        {x["source_row"] for x in selected[:120]))
        with self.assertRaisesRegex(RuntimeError,"G80_INSUFFICIENT_ORIGINAL_HELDOUT"):
            g.rank_original([{"instruction":"same","category":"math"}]*140,132)
    def test_frozen_count_and_priority(self):
        self.assertEqual((g.CASES,g.REPEATS,g.TOKENS,g.PROFILE_CASES),(12,6,8,3))
        self.assertEqual(g.PHASES,("prefill","cached_forward","token_selection"))
        self.assertEqual(g.PRIORITY["cached"],{"median":.60,"per_row":.50,"rows":9})
        self.assertEqual(g.nearest_p95(list(range(20))),18)
    def record(self,sample,rep,pre,cache,tok):
        return {"sample":sample,"source_row":sample+500,"rep":rep,
             "tokens_sha256":"hash_"+str(sample),
             "phases_ns":{"prefill":pre,"cached_forward":cache,"token_selection":tok},
             "cpu_phases_ns":{"prefill":pre,"cached_forward":cache,"token_selection":tok},
             "full_request_wall_ns":pre+cache+tok+1,
             "full_request_cpu_ns":pre+cache+tok}
    def test_cached_bottleneck(self):
        rows=[self.record(i,j,15,80,5) for i in range(12) for j in range(1,7)]
        summary=g.phase_stats(rows)
        self.assertEqual(summary["priority"],"TARGET_CACHED_FORWARD")
        self.assertEqual(summary["rows_above_frozen_cutoffs"]["cached_forward"],12)
        self.assertEqual(len(summary["per_row"]),12)
    def test_prefill_priority(self):
        rows=[self.record(i,j,70,25,5) for i in range(12) for j in range(1,7)]
        self.assertEqual(g.phase_stats(rows)["priority"],"TARGET_PREFILL")
    def test_no_dominant(self):
        rows=[self.record(i,j,40,45,15) for i in range(12) for j in range(1,7)]
        self.assertEqual(g.phase_stats(rows)["priority"],"NO_SINGLE_DOMINANT_PHASE")
    def test_fail_closed_negative_phase(self):
        rows=[self.record(i,j,30,60,10) for i in range(12) for j in range(1,7)]
        rows[0]["phases_ns"]["prefill"]=-1
        with self.assertRaisesRegex(RuntimeError,"G80_NEGATIVE_OR_NONINTEGER_PHASE"):
            g.phase_stats(rows)
    def test_fail_closed_output_drift_and_missing(self):
        rows=[self.record(i,j,30,60,10) for i in range(12) for j in range(1,7)]
        rows[0]["tokens_sha256"]="wrong"
        with self.assertRaisesRegex(RuntimeError,"G80_ORIGINAL_OUTPUT_INCONSISTENT"):
            g.phase_stats(rows)
        with self.assertRaisesRegex(RuntimeError,"G80_INCOMPLETE_PAIRED_PHASE_RECORDS"):
            g.phase_stats(rows[:-1])
    def test_original_nonpromotion_and_profile_separation(self):
        src=P.read_text(encoding="utf-8")
        for needle in ['"performance":"NOT_EVALUATED"','"scientific_acceptance":"NOT_GRANTED"',
                 '"promotion_allowed":False','torch.set_num_threads(1)','record_shapes=False',
                 'profile_memory=False','G80_PROFILER_CHANGES_ORIGINAL_OUTPUT',
                 'if len(profiles)!=PROFILE_CASES','original_decode(full)']:
            self.assertIn(needle,src)
        self.assertNotIn("model.train(",src)
        self.assertNotIn("model.cuda(",src)

if __name__=="__main__":unittest.main()

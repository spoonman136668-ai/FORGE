"""F124-W frozen-source and exact forward equivalence tests (no DEV scoring)."""
import math
import unittest
from collections import Counter

import f124w_hop_trace_indexed as candidate
import f124w_frozen_development as evidence
import f124v_collision_centered as original_v
import f124q_independent_binding as original_t
import f124q_fresh_source as source


class FrozenF124WTests(unittest.TestCase):
    def test_source_immutable_prereg_and_separation(self):
        spec=candidate.frozen()
        self.assertEqual(candidate.blob(candidate.FREEZE),candidate.FREEZE_BLOB)
        self.assertEqual(candidate.blob(original_v.__file__),
                         candidate.OLD_MODEL_BLOB)
        self.assertEqual(spec["lineage"]["parent_run"],39084350355)
        self.assertTrue(spec["qualification"]["negative_results_retained"])
        self.assertFalse(spec["qualification"]["compute_matched_superiority"])
        self.assertFalse(spec["qualification"]["protected_cases"])

    def test_full_FIT_cohort_and_no_previous_seed_reuse(self):
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(candidate.COHORTS[lane]["FIT"]).isdisjoint(
                            candidate.COHORTS[lane]["DEV"]))
            self.assertTrue(set(candidate.COHORTS[lane]["FIT"]).isdisjoint(
                            original_v.COHORTS[lane]["FIT"]))
            count=Counter()
            for _,_,a,b in candidate.pairs(lane,"FIT"):
                self.assertTrue(source.paired_admit(a,b))
                self.assertEqual(set(a),{"start","target","roles","edges"})
                count[len(a["roles"])]+=1
            self.assertEqual(count,Counter({7:16,8:16,9:16}))
            with self.assertRaises(source.Quarantined):
                candidate.build(lane,180100,(2,1,1),"DEV")
            with self.assertRaises(source.Quarantined):
                candidate.build(lane,980000,(2,1,1),"DEV")

    def test_indexed_checksum_bitwise_identical_and_cache_accounted(self):
        base=[0.7,0.6,0.9,0.5,0.8,0.12,-0.55]
        delta=[0.1,-0.03,0.07,-0.02]
        for _,_,positive,negative in candidate.pairs("Wingless","FIT")[:5]:
            for graph in (positive,negative):
                value,old=original_v.wingless_collision_reassignment(
                    graph,base,delta)
                cached,work=candidate.indexed_wingless(
                    graph,base,delta,candidate.PRIMARY)
                self.assertEqual(value,cached)
                self.assertLessEqual(work["max_active"],192)
                self.assertEqual(work["compression_levels"],5)
                self.assertEqual(work["compressed_bit_reads"],
                                 32*len(graph["edges"]))
                self.assertLess(work["public_edge_inspections"],
                                old["public_edge_scans"]+
                                (work["lookahead_cache_hits"]+
                                 work["lookahead_cache_misses"])*len(graph["edges"]))
                self.assertGreater(work["max_encoded_entries"],0)
                alternate,_=candidate.indexed_wingless(
                    graph,base,delta,candidate.ALTERNATE)
                self.assertTrue(math.isfinite(alternate))

    def test_Ygg_two_observers_exact_original_forward_not_heuristic(self):
        base=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
        delta=[1.3,0.2]
        for _,_,positive,negative in candidate.pairs("Yggdrasil","FIT")[:3]:
            for graph in (positive,negative):
                for mode in ("T_rank_only","V_centered"):
                    value,work,trace=candidate.ygg_hop_trace(
                        graph,base,delta,mode)
                    if mode=="T_rank_only":
                        original,origin_work=original_t.forward(
                            "Yggdrasil",graph,base,delta)
                    else:
                        original,origin_work=original_v.yggdrasil_centered_evidence(
                            graph,base,delta)
                    self.assertEqual(original,value)
                    self.assertTrue(all(work[k]==origin_work[k] for k in origin_work))
                    self.assertEqual(len(trace),len(graph["roles"]))
                    self.assertTrue(all(len(row["active"])<=7 and
                                        len(row["retained"])<=9 for row in trace))
                path=evidence.exact_reference_path(positive)
                joined=evidence.witness_join(trace,path)
                self.assertEqual(len(joined["hops"]),len(graph["roles"]))

    def test_no_oracle_in_inference_and_full_comparator_list(self):
        import inspect
        for method in (candidate.indexed_wingless,candidate.ygg_hop_trace):
            script=inspect.getsource(method)
            self.assertNotIn("public_routes(",script)
            self.assertNotIn("exact_reference_path(",script)
            self.assertNotIn("protected(",script)
        self.assertEqual(len(evidence.WING_ARMS),7)
        self.assertEqual(len(evidence.YGG_ARMS),4)
        self.assertIn("V_centered",evidence.YGG_ARMS)


if __name__=="__main__":
    unittest.main()

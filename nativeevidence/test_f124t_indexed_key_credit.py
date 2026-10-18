"""F124-T strict identity, new-source, bit-exact indexed replay and cell credit."""
import math
import unittest
import f124t_diagnostic_evidence as e
import f124t_fresh_source as t
import f124t_variants as v
import f124s_native_mechanisms as s
import f124o_native_learners as o
import f124r_fresh_source as r


class F124TFocused(unittest.TestCase):
    def test_protocol_freeze_immutable_and_parent_authentic(self):
        p=e.contract()
        self.assertEqual(p["parent"]["qualified_run_id"],39082745397)
        self.assertEqual(p["parent"]["s_model_blob"],e.S_MODEL_BLOB)
        self.assertEqual(e.blob(s),e.S_MODEL_BLOB)
        self.assertEqual(t.PROTOCOL_BLOB,e.CONTRACT_BLOB)
        self.assertTrue(p["protocol"]["no_new_learning_or_new_parameters"])
        self.assertFalse(p["authority"]["scientific_acceptance"])

    def test_complete_fresh_cohort_and_denominators(self):
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(t.COHORTS[lane]["FIT"]).isdisjoint(
                t.COHORTS[lane]["DEV"]))
            for phase in ("FIT","DEV"):
                self.assertTrue(set(t.COHORTS[lane][phase]).isdisjoint(
                    r.COHORTS[lane]["FIT"]))
                self.assertTrue(set(t.COHORTS[lane][phase]).isdisjoint(
                    r.COHORTS[lane]["DEV"]))
                depths={7:0,8:0,9:0}
                for vector in t.VECTORS:
                    for seed in t.COHORTS[lane][phase]:
                        pos,neg=t.build(lane,seed,vector,phase)
                        self.assertTrue(t.paired_admit(pos,neg))
                        depths[len(pos["roles"])]+=1
                self.assertEqual(depths,{7:16,8:16,9:16})
        with self.assertRaises(t.Quarantined):
            t.protected()
        with self.assertRaises(t.Quarantined):
            t.build("Yggdrasil",190100,[2,1,1],"DEV")

    def test_packed_optimization_bit_exact_logits_and_scratch_report(self):
        base=list(o.WINGLESS_INIT)
        d=[.24,-.1]
        for vector in t.VECTORS:
            for seed in [780000,780001,780002]:
                pos,neg=t.build("Wingless",seed,vector,"FIT")
                for graph in (pos,neg):
                    original,oldcost=s.wingless_packed(graph,base,d)
                    fast,cost=v.wingless_indexed(graph,base,d)
                    self.assertEqual(fast.hex(),original.hex())
                    self.assertEqual(cost["serialized_state_payload_bytes"],10)
                    self.assertEqual(cost["reference_serialized_state_payload_bytes"],40)
                    self.assertLessEqual(cost["max_active"],192)
                    self.assertGreater(cost["index_entries"],0)
                    self.assertGreater(cost["index_lookup_count"],0)
                    self.assertGreater(cost["max_key_cache_entries"],0)
                    self.assertTrue(cost["extra_scratch_memory_present"])
                    self.assertLess(cost["public_edge_scans"],
                                    oldcost["public_edge_scans"])
                    self.assertTrue(math.isfinite(fast))

    def test_ygg_credit_ablations_all_keep_7_plus_9(self):
        base=list(o.YGGDRASIL_INIT)
        d=[.3,-.12]
        for vector in t.VECTORS:
            pos,neg=t.build("Yggdrasil",790000,vector,"FIT")
            for g in (pos,neg):
                original,cost=s.yggdrasil_cell_credit(g,base,d)
                replay,newcost=v.yggdrasil_credit_ablation(
                    g,base,d,value_credit=True,rank_credit=True)
                self.assertEqual(original.hex(),replay.hex())
                self.assertLessEqual(cost["max_active"],7)
                self.assertLessEqual(cost["max_retained"],9)
                self.assertLessEqual(newcost["max_active"],7)
                self.assertLessEqual(newcost["max_retained"],9)
                for opts in (
                    dict(value_credit=True,rank_credit=False),
                    dict(value_credit=False,rank_credit=True)):
                    z,a=v.yggdrasil_credit_ablation(g,base,d,**opts)
                    self.assertTrue(math.isfinite(z))
                    self.assertLessEqual(a["max_active"],7)
                    self.assertLessEqual(a["max_retained"],9)

    def test_no_oracle_or_false_matched_cost_or_mutation(self):
        with self.assertRaises(ValueError):
            v.wingless_indexed({"oracle_truth":1},
                list(o.WINGLESS_INIT),[0,0])
        p=e.contract()
        self.assertFalse(p["protocol"]["Wingless"]
                         ["no_equal_total_memory_or_runtime_claim"] is False)
        self.assertTrue(p["protocol"]["Yggdrasil"]
                        ["no_mechanism_selection_on_dev"])


if __name__=="__main__":
    unittest.main()

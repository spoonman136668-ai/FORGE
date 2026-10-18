"""F124-U preregistration, strict bit replay and rank-only memory tests."""
import math
import unittest

import f124u_fresh_source as source
import f124u_microindex_causal_rank as model
import f124u_development_evidence as evidence
import f124o_native_learners as O
import f124s_native_mechanisms as S
import f124t_variants as T
import f124t_fresh_source as previous


class F124UTests(unittest.TestCase):
    def test_immutable_freeze_and_previous_model_identity(self):
        p=evidence.preregistration()
        self.assertEqual(p["qualified_parent"]["run_id"],39083960650)
        self.assertEqual(evidence.blob(S),evidence.S_BLOB)
        self.assertEqual(evidence.blob(T),evidence.T_BLOB)
        self.assertEqual(p["arms"]["Wingless"]["microindex_max_edge_entries"],8)
        self.assertEqual(p["arms"]["Wingless"]["microindex_max_candidate_keys"],4)
        self.assertEqual(p["arms"]["Wingless"]["key_cache_max_entries"],8)
        self.assertFalse(p["authority"]["scientific_acceptance"])

    def test_distinct_cohorts_48_balanced_and_protected_denied(self):
        for lane in ("Wingless","Yggdrasil"):
            for phase in ("FIT","DEV"):
                self.assertEqual(len(source.COHORTS[lane][phase]),24)
                self.assertTrue(set(source.COHORTS[lane][phase]).isdisjoint(
                    previous.COHORTS[lane]["FIT"]))
                self.assertTrue(set(source.COHORTS[lane][phase]).isdisjoint(
                    previous.COHORTS[lane]["DEV"]))
                depths={7:0,8:0,9:0}
                for v in source.VECTORS:
                    for seed in source.COHORTS[lane][phase]:
                        pos,neg=source.build(lane,seed,v,phase)
                        self.assertTrue(source.paired_admit(pos,neg))
                        depths[len(pos["roles"])]+=1
                self.assertEqual(depths,{7:16,8:16,9:16})
        with self.assertRaises(source.Quarantined):
            source.protected()

    def test_all_public_graph_prediction_replays_and_strict_cache_bound(self):
        base=list(O.WINGLESS_INIT)
        delta=[.11,-.02]
        for v in source.VECTORS:
            for seed in [880000,880001,880002]:
                pos,neg=source.build("Wingless",seed,v,"FIT")
                for g in (pos,neg):
                    a,ca=S.wingless_packed(g,base,delta)
                    b,cb=T.wingless_indexed(g,base,delta)
                    c,cc=model.wingless_microindex(g,base,delta)
                    self.assertEqual(a.hex(),b.hex())
                    self.assertEqual(a.hex(),c.hex())
                    self.assertEqual(cc["serialized_state_payload_bytes"],10)
                    self.assertLessEqual(cc["index_entries"],8)
                    self.assertLessEqual(cc["index_candidate_keys"],4)
                    self.assertLessEqual(cc["max_key_cache_entries"],8)
                    self.assertLessEqual(cc["max_active"],192)
                    self.assertGreater(cc["public_edge_scans"],0)
                    self.assertGreater(cc["index_lookups"],0)

    def test_new_yggdrasil_learned_rank_does_not_mutate_cell_values(self):
        base=list(O.YGGDRASIL_INIT)
        for vec in source.VECTORS:
            pos,neg=source.build("Yggdrasil",890000,vec,"FIT")
            for g in (pos,neg):
                original,cost=O.yggdrasil_forward(g,base)
                zero,work=model.ygg_rank(g,base,[0,0])
                self.assertEqual(original.hex(),zero.hex())
                changed,work2=model.ygg_rank(g,base,[.4,-.2])
                self.assertTrue(math.isfinite(changed))
                self.assertLessEqual(work["max_active"],7)
                self.assertLessEqual(work["max_retained"],9)
                self.assertLessEqual(work2["max_active"],7)
                self.assertLessEqual(work2["max_retained"],9)
                self.assertGreater(work2["lookahead_comparisons"],0)

    def test_smooth_surrogate_uses_public_causal_keys_not_truth(self):
        base=list(O.YGGDRASIL_INIT)
        pos,neg=source.build("Yggdrasil",890000,[2,1,1],"FIT")
        a=model.soft_routing(pos,[0.,0.])
        b=model.soft_routing(neg,[0.,0.])
        self.assertTrue(math.isfinite(a) and math.isfinite(b))
        self.assertNotEqual(model.soft_routing(pos,[.4,.2]),a)
        with self.assertRaises(ValueError):
            model.ygg_rank({"oracle_truth":True},base,[0,0])


if __name__=="__main__":
    unittest.main()

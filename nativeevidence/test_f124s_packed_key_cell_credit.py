"""F124-S source-frozen budget and cell-credit qualification tests."""
import inspect
import math
import unittest

import f124s_fresh_source as source
import f124s_native_mechanisms as m
import f124s_development_evidence as evidence
import f124o_native_learners as original
import f124r_fresh_source as prev


class F124STests(unittest.TestCase):
    def test_frozen_contract_and_all_original_models_immutable(self):
        p=evidence.protocol()
        self.assertEqual(p["models"]["Wingless"]["candidate_serialized_state_bytes"],10)
        self.assertEqual(p["models"]["Wingless"]["reference_serialized_state_bytes"],40)
        self.assertEqual(p["models"]["Yggdrasil"]["active_limit"],7)
        self.assertEqual(p["models"]["Yggdrasil"]["retained_limit"],9)
        self.assertEqual(evidence.blob(original),evidence.O_BLOB)
        self.assertEqual(evidence.blob(evidence.r_model),evidence.R_BLOB)
        self.assertTrue(p["training"]["no_post_DEV_changes"])
        self.assertFalse(p["authority"]["protected_first_use"])

    def test_new_source_48_balanced_per_lane_and_phase(self):
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(source.COHORTS[lane]["FIT"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))
            for phase in ("FIT","DEV"):
                self.assertTrue(set(source.COHORTS[lane][phase]).isdisjoint(
                                prev.COHORTS[lane]["FIT"]))
                self.assertTrue(set(source.COHORTS[lane][phase]).isdisjoint(
                                prev.COHORTS[lane]["DEV"]))
                strata={7:0,8:0,9:0}
                for vector in source.VECTORS:
                    for seed in source.COHORTS[lane][phase]:
                        p,n=source.build(lane,seed,vector,phase)
                        self.assertTrue(source.paired_admit(p,n))
                        strata[len(p["roles"])]+=1
                self.assertEqual(strata,{7:16,8:16,9:16})
        with self.assertRaises(source.Quarantined):
            source.protected()
        with self.assertRaises(source.Quarantined):
            source.build("Wingless",180100,[2,1,1],"DEV")

    def test_real_wingless_serialized_packed_key_replaces_latent(self):
        self.assertEqual(m.STATE.size,10)
        self.assertEqual(m.STATE.unpack(m.STATE.pack(1.25,65535)),(1.25,65535))
        for seed in (680000,680001,680002):
            p,n=source.build("Wingless",seed,[2,1,1],"FIT")
            for g in (p,n):
                z,w=m.wingless_packed(g,list(original.WINGLESS_INIT),[.2,-.1])
                self.assertTrue(math.isfinite(z))
                self.assertEqual(w["serialized_state_payload_bytes"],10)
                self.assertEqual(w["reference_serialized_state_payload_bytes"],40)
                self.assertEqual(w["state_limit"],3)
                self.assertLessEqual(w["max_active"],192)
                self.assertGreater(w["causal_key_comparisons"],0)
                self.assertGreater(w["raw_bit_ops"],0)

    def test_yggdrasil_continuous_cell_credit_preserves_original_zero_case(self):
        p,n=source.build("Yggdrasil",690000,[2,1,1],"FIT")
        base=list(original.YGGDRASIL_INIT)
        for g in (p,n):
            old,ow=original.yggdrasil_forward(g,base)
            z,w=m.yggdrasil_cell_credit(g,base,[0,0])
            self.assertAlmostEqual(old,z,places=12)
            self.assertEqual(w["active_cell_limit"],7)
            self.assertEqual(w["retained_cell_limit"],9)
            self.assertLessEqual(w["max_active"],7)
            self.assertLessEqual(w["max_retained"],9)
            modified,_=m.yggdrasil_cell_credit(g,base,[.3,.2])
            self.assertTrue(math.isfinite(modified))

    def test_model_functions_no_oracle_and_no_DEV_training(self):
        b=inspect.getsource(m.wingless_packed)+inspect.getsource(
            m.yggdrasil_cell_credit)
        for forbidden in ("public_routes(", "protected(", "true_path",
                          "symbolic_routes(", "oracle_truth"):
            self.assertNotIn(forbidden,b)
        tr=inspect.getsource(m.fit_pairs)+inspect.getsource(m.train)
        self.assertNotIn('["DEV"]',tr)
        with self.assertRaises(ValueError):
            m.wingless_packed({"oracle":True},list(original.WINGLESS_INIT),[0,0])


if __name__=="__main__":
    unittest.main()

"""F124-V independent preregistration, real RAM provider, and trace fidelity."""
import math
import sys
import unittest

import f124v_fresh_source as source
import f124v_wingless_hardware as hw
import f124v_yggdrasil_causal_trace as trace
import f124o_native_learners as O
import f124s_native_mechanisms as S
import f124t_variants as T
import f124u_microindex_causal_rank as U


class F124VFocused(unittest.TestCase):
    def test_two_preimplementation_frozen_science_sources(self):
        a,b=source.frozen()
        self.assertTrue(len(a)==64 and len(b)==64)
        w=__import__("json").loads(source.PROTOCOL.read_text())
        y=trace.contract()
        self.assertEqual(w["qualified_parent"]["head"],
                         "7d8df58e3fd7363e5c91b39a426ff3430fedf20d")
        self.assertEqual(y["experiment"]["trace_per_positive_case"][0],
                         "causal_prefix_candidate_generated_at_hop")
        self.assertNotEqual(w["source"]["salt_domain"],
                            y["source"]["salt_domain"])
        self.assertTrue(all(v is False for v in w["authority"].values()))
        self.assertTrue(all(v is False for v in y["authority"].values()))

    def test_fresh_cohorts_disjoint_complete_and_protected_inert(self):
        for lane in ("Wingless","Yggdrasil"):
            self.assertEqual(len(source.COHORTS[lane]["FIT"]),24)
            self.assertTrue(set(source.COHORTS[lane]["FIT"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))
            for phase in ("FIT","DEV"):
                depths={7:0,8:0,9:0}
                for vector in source.VECTORS:
                    for seed in source.COHORTS[lane][phase]:
                        p,n=source.build(lane,seed,vector,phase)
                        self.assertTrue(source.paired_admit(p,n))
                        depths[len(p["roles"])]+=1
                self.assertEqual(depths,{7:16,8:16,9:16})
        with self.assertRaises(source.Quarantined):
            source.protected()
        with self.assertRaises(source.Quarantined):
            source.build("Wingless",180100,[2,1,1],"DEV")

    def test_hardware_peak_memory_provider_is_real_not_synthetic(self):
        self.assertIn(sys.platform,("linux","win32"))
        self.assertGreater(hw.hwm_bytes(),0)
        self.assertEqual(len(hw.ARMS),5)
        self.assertTrue(hw.SCHEMA.endswith("hardware-measurement.v1"))

    def test_original_S_T_U_exact_logits_with_new_hardware_source(self):
        p,n=source.build("Wingless",1080000,[2,1,1],"FIT")
        base=list(O.WINGLESS_INIT);d=[.15,-.05]
        for g in (p,n):
            a,_=S.wingless_packed(g,base,d)
            b,_=T.wingless_indexed(g,base,d)
            c,info=U.wingless_microindex(g,base,d)
            self.assertEqual(a.hex(),b.hex())
            self.assertEqual(b.hex(),c.hex())
            self.assertLessEqual(info["index_entries"],8)
            self.assertLessEqual(info["max_key_cache_entries"],8)
            self.assertEqual(info["serialized_state_payload_bytes"],10)

    def test_public_oracle_is_only_evaluator_and_trace_matches_model(self):
        base=list(O.YGGDRASIL_INIT)
        weights={"base":base,"R":[.17,-.05],
                 "S":[.09,.2],"U":[.1,-.04]}
        p,n=source.build("Yggdrasil",1090000,[2,1,1],"FIT")
        route=trace.exact_positive_prefix(p)
        self.assertEqual(len(route),len(p["roles"]))
        for arm in trace.ARMS:
            for g in (p,n):
                score,_=trace.original_forward(arm,g,weights)
                result=trace.trace_model(arm,g,weights)
                self.assertEqual(result["logit_hex"],score.hex())
            detailed=trace.trace_model(arm,p,weights,positive_prefix=route)
            self.assertEqual(len(detailed["hops"]),len(p["roles"]))
            self.assertTrue(all(x["number_active"]<=7 and
                                x["number_retained"]<=9
                                for x in detailed["hops"]))
            self.assertEqual(detailed["hops"][0]["hop"],1)


if __name__=="__main__":
    unittest.main()

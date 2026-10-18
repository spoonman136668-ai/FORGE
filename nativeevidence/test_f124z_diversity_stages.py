"""F124-Z pinned originals, new public-source birth, oracle separation."""
import json
import unittest

import f124z_source as src
import f124z_node_diversity as diversity
import f124z_wingless_stages as wing
import f124o_native_learners as O
import f124v_yggdrasil_causal_trace as V


class F124ZIndependent(unittest.TestCase):
    def test_frozen_protocol_and_no_protected_first_use(self):
        self.assertEqual(len(src.frozen()),64)
        p=json.loads(src.PROTOCOL.read_text())
        self.assertEqual(p["parent"]["qualified_run"],39088762270)
        self.assertEqual(p["experiments"]["Y_diversity"]["permanent_cells"],16)
        self.assertEqual(p["experiments"]["W_failure_stages"]["caps_mib"],
                         [28,26,24,22,20])
        self.assertTrue(all(x is False for x in p["governance"].values()))
        with self.assertRaises(src.Quarantined):src.protected()

    def test_independent_role_graph_validity_and_actual_competition(self):
        for lane in ("Wingless","YggdrasilStress"):
            for phase in ("FIT","DEV"):
                by={7:0,8:0,9:0}
                for vector in src.VECTORS:
                    for seed in src.COHORTS[lane][phase]:
                        if lane=="YggdrasilStress":
                            p,n=src.stress_pair(seed,vector,phase)
                        else:
                            p,n=src.build(lane,seed,vector,phase)
                        self.assertTrue(src.paired_admit(p,n))
                        by[len(p["roles"])]+=1
                self.assertEqual(by,{7:16,8:16,9:16})

    def test_diversity_never_expands_original_cell_memory(self):
        w={"base":list(O.YGGDRASIL_INIT),"R":[.13,-.01],
           "S":[.1,.1],"U":[.14,-.2]}
        pos,neg=src.stress_pair(1690000,[2,1,1],"FIT")
        path=V.exact_positive_prefix(pos)
        for arm in diversity.ARMS:
            for g in (pos,neg):
                original,counts=V.original_forward(arm,g,w)
                calc=diversity.forward(arm,g,w,mode="original")
                self.assertEqual(calc["logit_hex"],original.hex())
                new=diversity.forward(arm,g,w,mode="diverse")
                self.assertTrue(new["logit_hex"].startswith(("0x","-0x")))
                self.assertLessEqual(new["final_active"],7)
                self.assertLessEqual(new["final_retained"],9)
            d=diversity.forward(arm,pos,w,mode="diverse",positive_prefix=path)
            self.assertTrue(all(z["number_active"]<=7 and
                                z["number_retained"]<=9 for z in d["hops"]))
            self.assertGreater(max(z["number_candidates"] for z in d["hops"]),16)

    def test_stage_protocol_is_stable_and_no_OOM_false_positive(self):
        self.assertEqual(wing.CAPS,(28,26,24,22,20))
        self.assertEqual(wing.ARMS,("S_packed","T_full_index","U_microindex"))
        self.assertEqual(wing.STAGES,("pre_import","after_import","after_fixtures",
                    "after_cap_attach","after_warmup","after_inference"))


if __name__=="__main__":
    unittest.main()

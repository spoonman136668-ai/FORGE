"""F124-W frozen source, exact replay and strict process-memory checks."""
import json
import math
import os
import subprocess
import sys
import unittest

import f124w_fresh_source as source
import f124w_wingless_hardcap as wing
import f124w_yggdrasil_score_drift as ygg
import f124o_native_learners as O
import f124s_native_mechanisms as S
import f124t_variants as T
import f124u_microindex_causal_rank as U


class F124WTests(unittest.TestCase):
    def test_preregistration_and_original_policy_scope(self):
        p=json.loads(source.PROTOCOL.read_text())
        self.assertEqual(source.frozen().__class__,str)
        self.assertEqual(p["parent"]["qualified_actions_run"],39085631962)
        self.assertEqual(p["Wingless"]["fixed_memory_budget_bytes"],100663296)
        self.assertEqual(p["Wingless"]["repetitions_per_arm"],3)
        self.assertTrue(ygg.frozen()["Yggdrasil"]["science_guard"].startswith(
            "Unique reference causal path"))
        self.assertTrue(all(v is False for v in p["authority"].values()))

    def test_distinct_source_and_balanced_hop_denominator(self):
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(source.COHORTS[lane]["FIT"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))
            for phase in ("FIT","DEV"):
                strata={7:0,8:0,9:0}
                for v in source.VECTORS:
                    for seed in source.COHORTS[lane][phase]:
                        pos,neg=source.build(lane,seed,v,phase)
                        self.assertTrue(source.paired_admit(pos,neg))
                        strata[len(pos["roles"])]+=1
                self.assertEqual(strata,{7:16,8:16,9:16})
        with self.assertRaises(source.Quarantined):
            source.protected()

    def test_all_wingless_index_logit_hex_remain_identical(self):
        base=list(O.WINGLESS_INIT); delta=[.1,-.05]
        for v in source.VECTORS:
            for seed in (1180000,1180001):
                pos,neg=source.build("Wingless",seed,v,"FIT")
                for graph in (pos,neg):
                    a,_=S.wingless_packed(graph,base,delta)
                    b,_=T.wingless_indexed(graph,base,delta)
                    c,cost=U.wingless_microindex(graph,base,delta)
                    self.assertEqual(a.hex(),b.hex())
                    self.assertEqual(a.hex(),c.hex())
                    self.assertLessEqual(cost["index_entries"],8)

    def test_yggdrasil_exact_model_score_and_path_faithfulness(self):
        w={"base":list(O.YGGDRASIL_INIT),"R":[.1,-.03],
           "S":[.16,.02],"U":[.11,-.2]}
        pos,neg=source.build("Yggdrasil",1190000,[2,1,1],"FIT")
        for arm in ygg.ARMS:
            for graph in (pos,neg):
                trace=ygg.shadow(arm,graph,w)
                o,_=ygg.V.original_forward(arm,graph,w)
                self.assertEqual(trace["margin_hex"],o.hex())
            path=ygg.V.exact_positive_prefix(pos)
            details=ygg.shadow(arm,pos,w,path)
            self.assertEqual(len(details["hops"]),len(pos["roles"]))
            self.assertTrue(all(r["active_count"]<=7 and
                                r["retained_count"]<=9
                                for r in details["hops"]))

    def test_operating_system_hard_cap_provider_in_child_process(self):
        code=("import sys; import f124w_wingless_hardcap as w;"
              "provider,job=w.enforce_process_memory_cap(100663296);"
              "assert provider.startswith(('linux_','windows_'));"
              "assert w.hwm_bytes()>0;print(provider)")
        env=dict(os.environ)
        env["PYTHONPATH"]=os.path.dirname(__file__)
        process=subprocess.run([sys.executable,"-B","-c",code],
                               capture_output=True,text=True,env=env,
                               timeout=20)
        self.assertEqual(process.returncode,0,
                         msg=process.stderr+"\n"+process.stdout)


if __name__=="__main__":
    unittest.main()

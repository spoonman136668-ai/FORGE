"""F124-X separate frozen development experiments: source, workload and safety."""
import json
import os
import subprocess
import sys
import unittest

import f124x_source as src
import f124x_ygg_intervention as intervention
import f124x_ygg_capacity_stress as stress
import f124x_wingless_multicap as capped
import f124o_native_learners as O
import f124v_yggdrasil_causal_trace as V
import f124s_native_mechanisms as S
import f124t_variants as T
import f124u_microindex_causal_rank as U


class F124XSourceTests(unittest.TestCase):
    def test_preregistration_exact_commit_and_three_independent_cohorts(self):
        self.assertEqual(len(src.frozen()),64)
        p=json.loads(src.PROTOCOL.read_text())
        self.assertEqual(p["parent"]["qualified_run"],39086792211)
        self.assertEqual(p["experiments"]["W_low_memory"]["caps_mib"],[64,48,40])
        self.assertEqual(
            p["experiments"]["Y_calibration"]["fit_only_selection"]["candidate_logit_thresholds"],
            [-8,-6,-4,-3,-2,-1,0,1,2,3,4,6,8])
        self.assertTrue(all(not v for k,v in p["governance"].items()
                            if k!="draft_unmerged"))
        self.assertEqual(len(set(src.SALTS.values())),3)

    def test_each_source_has_fresh_48_pair_denominator_and_stress_admission(self):
        for lane in src.COHORTS:
            self.assertTrue(set(src.COHORTS[lane]["FIT"]).isdisjoint(
                            src.COHORTS[lane]["DEV"]))
            depths={7:0,8:0,9:0}
            for v in src.VECTORS:
                for seed in src.COHORTS[lane]["FIT"]:
                    if lane=="YggdrasilStress":
                        p,n=src.stress_pair(seed,v,"FIT")
                    else:p,n=src.build(lane,seed,v,"FIT")
                    self.assertTrue(src.paired_admit(p,n))
                    depths[len(p["roles"])]+=1
            self.assertEqual(depths,{7:16,8:16,9:16})
        with self.assertRaises(src.Quarantined):
            src.protected()

    def test_stress_actual_candidate_pressure_and_exact_trace_budget(self):
        weights={"base":list(O.YGGDRASIL_INIT),"R":[.1,-.05],
                 "S":[.1,.05],"U":[.1,-.1]}
        p,n=src.stress_pair(1390000,[2,1,1],"FIT")
        blind=V.original_forward("O",p,weights)[0]
        prefix=V.exact_positive_prefix(p)
        row=V.trace_model("O",p,weights,positive_prefix=prefix)
        self.assertEqual(row["logit_hex"],blind.hex())
        self.assertTrue(all(x["number_active"]<=7 and x["number_retained"]<=9
                            for x in row["hops"]))
        self.assertGreater(max(x["number_candidates"] for x in row["hops"]),16)

    def test_wingless_logit_identity_on_new_cohort(self):
        p,n=src.build("Wingless",1280000,[2,1,1],"FIT")
        w=list(O.WINGLESS_INIT);d=[.08,-.03]
        for g in (p,n):
            a,_=S.wingless_packed(g,w,d)
            b,_=T.wingless_indexed(g,w,d)
            c,_=U.wingless_microindex(g,w,d)
            self.assertEqual(a.hex(),b.hex())
            self.assertEqual(a.hex(),c.hex())

    def test_calibration_is_FIT_only_and_hard_cap_provider_is_real(self):
        self.assertEqual(intervention.THRESHOLDS,(-8,-6,-4,-3,-2,-1,0,1,2,3,4,6,8))
        self.assertNotIn('"DEV"',__import__("inspect").getsource(
                         intervention.fit_thresholds))
        script=("import f124x_wingless_multicap as m;"
                "provider,handle=m.enforce_process_memory_cap(67108864);"
                "assert provider in ('linux_RLIMIT_AS','windows_JOB_OBJECT_PROCESS_MEMORY')")
        env=dict(os.environ)
        env["PYTHONPATH"]=os.path.dirname(__file__)
        p=subprocess.run([sys.executable,"-B","-c",script],env=env,
                         capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,0,msg=p.stderr)


if __name__=="__main__":
    unittest.main()

"""F124-Y source identity and three independently frozen science protocols."""
import json
import os
import subprocess
import sys
import unittest

import f124y_source as src
import f124y_value_transfer as value
import f124y_equal_cells as cells
import f124y_wing_memory_boundary as wing
import f124o_native_learners as O
import f124v_yggdrasil_causal_trace as V
import f124s_native_mechanisms as S
import f124t_variants as T
import f124u_microindex_causal_rank as U


class F124YFrozen(unittest.TestCase):
    def test_frozen_contract_and_disjoint_source_births(self):
        digest=src.frozen()
        self.assertEqual(len(digest),64)
        p=json.loads(src.PROTOCOL.read_text())
        self.assertEqual(p["parent"]["exact_qualified_head"],
                         "1fe33a5c1acebcfa8759fae8d229f4c47a904fa8")
        self.assertEqual(p["parent"]["run_id"],39087821110)
        self.assertEqual(p["experiments"]["wingless_memory_edge"]["caps_mib"],
                         [36,32,28,24,20])
        self.assertEqual(p["experiments"]["equal_sixteen_cells"]["cell_allocations"],
                         [[6,10],[7,9],[8,8],[9,7],[10,6]])
        self.assertEqual(len(set(src.SALTS.values())),3)
        self.assertTrue(all(v is False for k,v in p["governance"].items()
                            if k!="draft_unmerged"))
        with self.assertRaises(src.Quarantined):src.protected()

    def test_new_independent_denominators_and_no_original_data(self):
        for lane in src.COHORTS:
            self.assertTrue(set(src.COHORTS[lane]["FIT"]).isdisjoint(
                            src.COHORTS[lane]["DEV"]))
            depth={7:0,8:0,9:0}
            for vector in src.VECTORS:
                for seed in src.COHORTS[lane]["FIT"]:
                    if lane=="YggdrasilStress":
                        a,b=src.stress_pair(seed,vector,"FIT")
                    else:
                        a,b=src.build(lane,seed,vector,"FIT")
                    self.assertTrue(src.paired_admit(a,b))
                    depth[len(a["roles"])]+=1
            self.assertEqual(depth,{7:16,8:16,9:16})

    def test_new_value_intervention_does_not_retrain_or_look_at_DEV(self):
        self.assertEqual(value.THRESHOLDS,(-8,-6,-4,-3,-2,-1,0,1,2,3,4,6,8))
        p=json.loads(src.PROTOCOL.read_text())
        self.assertTrue(p["experiments"]["value_transfer"]
                        ["no_new_calibration_fit_or_DEV_selection"])
        self.assertFalse(p["experiments"]["value_transfer"]["protected_first_use"])
        self.assertEqual(len(value.ARMS),8)

    def test_identical_original_logits_at_7_plus_9_with_other_allocations(self):
        weights={"base":list(O.YGGDRASIL_INIT),"R":[.07,-.03],
                 "S":[.1,.05],"U":[.13,-.05]}
        a,b=src.stress_pair(1590000,[2,1,1],"FIT")
        for g in (a,b):
            for arm in ("O","U"):
                reference,_=V.original_forward(arm,g,weights)
                exact=cells.partition_forward(arm,g,weights,7)
                self.assertEqual(exact["logit_hex"],reference.hex())
                for active in (6,8,9,10):
                    row=cells.partition_forward(arm,g,weights,active)
                    self.assertTrue(row["logit_hex"].startswith(("0x","-0x")))
        path=V.exact_positive_prefix(a)
        detailed=cells.partition_forward("O",a,weights,7,positive_prefix=path)
        self.assertEqual(len(detailed["hops"]),len(a["roles"]))
        self.assertGreater(max(x["number_candidates"] for x in detailed["hops"]),16)
        self.assertTrue(all(x["number_active"]<=7 and
                            x["number_retained"]<=9
                            for x in detailed["hops"]))

    def test_original_wingless_packed_full_and_micro_logit_identity(self):
        pos,neg=src.build("Wingless",1480000,[2,1,1],"FIT")
        base=list(O.WINGLESS_INIT);delta=[.1,-.05]
        for g in (pos,neg):
            aa,_=S.wingless_packed(g,base,delta)
            bb,_=T.wingless_indexed(g,base,delta)
            cc,cost=U.wingless_microindex(g,base,delta)
            self.assertEqual(aa.hex(),bb.hex())
            self.assertEqual(aa.hex(),cc.hex())
            self.assertLessEqual(cost["index_entries"],8)

    def test_actual_hard_cap_os_kernel_not_just_declared(self):
        script=("import f124y_wing_memory_boundary as m;"
                "provider,handle=m.enforce_process_memory_cap(37748736);"
                "assert provider in ('linux_RLIMIT_AS','windows_JOB_OBJECT_PROCESS_MEMORY')")
        env=dict(os.environ);env["PYTHONPATH"]=os.path.dirname(__file__)
        p=subprocess.run([sys.executable,"-B","-c",script],env=env,
                         capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,0,msg=p.stderr)


if __name__=="__main__":unittest.main()

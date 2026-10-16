import copy
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import f101_public_mechanisms as f101

SHA="8"*40

class F101PublicDevelopmentOnly(unittest.TestCase):
    def test_all_preregistered_mechanisms_and_frozen_budget(self):
        d=f101.plan()
        self.assertEqual(d["candidate_order"],["W100-C1","W100-C2","Y100-C1","Y100-C2"])
        self.assertEqual(d["optimization"]["max_steps"],100)
        self.assertEqual([d["model"][x]["parameter_count"] for x in d["candidate_order"]],
                         [9,9,11,19])
        self.assertFalse(d["authorization"]["protected_first_use"])
        self.assertFalse(d["authorization"]["autonomous_gpt_executor"])
    def test_public_counterfactuals_and_all_coded_controls(self):
        frozen=json.loads(f101.F100.read_text(encoding="utf-8"))
        for lane in frozen["lanes"]:
            seeds=[x for a,b in lane["public_development_seed_blocks"] for x in range(a,b+1)]
            self.assertEqual(len(seeds),48)
            for seed in seeds:
                cases=f101.pair(lane["lane"],seed)
                self.assertEqual(len(cases),2)
                self.assertEqual(sum(x["truth"] for x in cases),1)
                self.assertEqual(cases[0]["edges"],cases[1]["edges"])
                self.assertEqual([f101.source_controls(x) for x in cases],
                                 [x["truth"] for x in cases])
                self.assertGreaterEqual(seed,63000)
    def test_learned_candidate_never_consults_oracle_or_truth(self):
        for lane,cid in (("Wingless","W100-C1"),("Wingless","W100-C2"),
                         ("Yggdrasil","Y100-C1"),("Yggdrasil","Y100-C2")):
            example=f101.pair(lane,63100 if lane=="Wingless" else 63400)[0]
            params=f101.initial(cid,f101.plan()["model"][cid]["parameter_count"])
            val=f101.forward(example,params,cid)
            self.assertGreaterEqual(val,0)
            self.assertLessEqual(val,1)
            changed=copy.deepcopy(example)
            changed["truth"]=1-example["truth"]
            self.assertEqual(val,f101.forward(changed,params,cid))
            masked=f101.masked_query(example,"permuted")
            mutated=f101.masked_query(changed,"permuted")
            self.assertEqual(masked["edges"],mutated["edges"])
            if lane=="Wingless":
                self.assertEqual(masked["depth"],mutated["depth"])
            else:
                self.assertEqual(masked["roles"],mutated["roles"])
    def test_relation_binding_invariant_to_variable_id_renaming(self):
        for cid in ("Y100-C1","Y100-C2"):
            case=f101.pair("Yggdrasil",63403)[0]
            params=f101.initial(cid,f101.plan()["model"][cid]["parameter_count"])
            value=f101.forward(case,params,cid)
            renamed=copy.deepcopy(case)
            names={0:0,7:7,1:6,6:1,2:5,5:2,3:4,4:3}
            renamed["edges"]=tuple((names[u],names[v],r) for u,v,r in case["edges"])
            self.assertAlmostEqual(f101.forward(renamed,params,cid),value)
    def test_trainable_public_dev_is_deterministic_and_all_losses_recomputed(self):
        with patch.dict(os.environ,{"GITHUB_SHA":SHA}):
            report=f101.run(SHA)
            repeat=f101.run(SHA)
        self.assertEqual(report,repeat)
        self.assertEqual(report["schema"],f101.SCHEMA)
        self.assertEqual(report["public_development_candidate_tests"],4)
        self.assertEqual(report["public_development_control_training_runs"],8)
        self.assertEqual(report["protected_scientific_originals"],0)
        self.assertEqual(report["accepted_scientific_results"],0)
        self.assertFalse(report["scientific_first_use_authorized"])
        self.assertFalse(report["autonomous_gpt_executor_active"])
        self.assertEqual([z["candidate_id"] for z in report["candidate_results"]],
                         ["W100-C1","W100-C2","Y100-C1","Y100-C2"])
        for rec in report["candidate_results"]:
            self.assertEqual(rec["train_public_pairs"],32)
            self.assertEqual(rec["dev_public_pairs"],16)
            self.assertEqual(rec["optimizer_steps"],100)
            self.assertEqual(rec["coded_oracle_paired_accuracy"],1)
            self.assertEqual(rec["historical_blind_paired_accuracy"],0)
            self.assertEqual(rec["always_yes_paired_accuracy"],0)
            self.assertFalse(rec["scientific_first_use_authorized"])
            self.assertEqual(set(rec["learned_public_dev"]),{"full","missing","permuted"})
            for dev in rec["learned_public_dev"].values():
                self.assertEqual(dev["pairs"],16)
                self.assertGreaterEqual(dev["paired_correct"],0)
                self.assertLessEqual(dev["paired_correct"],16)
                self.assertEqual(dev["paired_accuracy"],dev["paired_correct"]/16)
                self.assertEqual(len(dev["weights_sha256"]),64)
    def test_source_and_plan_tampering_denied(self):
        with patch.dict(os.environ,{"GITHUB_SHA":"f"*40}):
            with self.assertRaises(f101.Quarantine):f101.run(SHA)
        frozen=f101.plan()
        frozen["authorization"]["protected_first_use"]=True
        with tempfile.TemporaryDirectory() as root:
            p=pathlib.Path(root)/"f101.json"
            p.write_text(json.dumps(frozen),encoding="utf-8")
            with patch.object(f101,"PLAN",p):
                with self.assertRaises(f101.Quarantine):f101.plan()
if __name__=="__main__":
    unittest.main()

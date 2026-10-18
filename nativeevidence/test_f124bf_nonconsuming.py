"""F124-BF nonconsuming source, graded causal margin and hard-panel tests."""
from __future__ import annotations
import ast,copy,unittest
from pathlib import Path
from unittest.mock import patch
import f124bf_source_only as source
import f124bf_public_causal_margin as margin
import f124bf_original_fit as science

class FrozenPublicMargin(unittest.TestCase):
    def test_immutable_preimplementation_birth_and_protected_dev(self):
        d=source.frozen()
        self.assertEqual(d["sources"]["FIT"],[5400000,5400011])
        self.assertEqual(d["sources"]["SCREEN"],[5400012,5400023])
        self.assertEqual(d["sources"]["protected_DEV"],[5400100,5400123])
        self.assertEqual(d["hard_panel"]["panel_size"],4)
        self.assertEqual(d["public"]["per_task_responses"],48)
        self.assertEqual(len(d["policies"]),6)
        self.assertTrue(all(v is False for v in d["safety"].values()))
        with self.assertRaises(Exception):source.build(5400100,source.VECTORS[0])
        with self.assertRaises(Exception):source.rows("DEV")

    def test_source_only_first_four_oracle_negatives_without_model(self):
        z=[0]*16
        p={"start":"n0","target":"n7","roles":["r0"],
           "demos":[],"edges":[{"from":"n0","to":"n1","role":"r0",
                                "src_bits":z[:],"dst_bits":z[:]}]}
        n=copy.deepcopy(p);n["edges"][0]["src_bits"][0]=1
        with patch.object(source,"plain",lambda graph,op,nonce:graph),patch.object(
            source,"ORACLE",lambda graph,relaxed:int(
                not any(any(e[field]) for e in graph["edges"]
                        for field in ("src_bits","dst_bits")))):
            hard,meta=source.four_hard(p,n,"synthetic","nonce","xor16_permuted")
        self.assertEqual(len(hard),4)
        self.assertEqual(meta["true_hard"],4)
        self.assertEqual(meta["oracle_probes"],6)
        self.assertEqual(meta["source_fallbacks"],0)
        self.assertFalse(meta["model_based_source_selection"])
        self.assertEqual([e["bit"] for e in meta["edits"]],[0,1,2,3])
        self.assertEqual(p["edges"][0]["src_bits"],z)

    def graph(self):
        z=[0]*16
        edges=[{"from":str(i),"to":str(i+1),"role":"r"+str(i),
                "src_bits":z[:],"dst_bits":z[:]} for i in range(7)]
        for j in range(5):
            edges.append({"from":"d"+str(j),"to":"d"+str(j+1),"role":"decoy",
                          "src_bits":z[:],"dst_bits":z[:]})
        return {"start":"0","target":"7",
                "roles":["r"+str(i) for i in range(7)],"edges":edges}

    def test_numeric_counterfactual_margin_is_not_missing_peer_veto(self):
        g=self.graph()
        x=margin.route_margin(g)
        self.assertEqual(x["best_causal_bit_cost"],0)
        self.assertEqual(x["public_path_count"],1)
        self.assertEqual(x["second_distinct_path_bit_cost"],256)
        g["edges"][3]["src_bits"][0]=1
        rival=copy.deepcopy(g["edges"][3])
        rival["src_bits"][1]=1
        g["edges"].append(rival)
        x=margin.route_margin(g)
        self.assertEqual(x["best_causal_bit_cost"],1)
        self.assertEqual(x["second_distinct_path_bit_cost"],2)
        self.assertEqual(x["public_competitor_gap"],1)
        self.assertEqual(x["public_path_count"],2)
        self.assertEqual(margin.POLICIES,(1,2,4))

    def test_hard_FP_elimination_cannot_lose_a_Feistel_positive(self):
        def rec(ids,hard,feistel):
            return {"accepted_positive_case_ids":ids,
                    "accepted_Feistel_positive_case_ids":feistel,
                    "positive":len(ids),"original_FP":0,"hard_FP":hard}
        model="margin_balanced_gap1"
        cards={"joint_balanced48":rec(["a","f"],3,["f"]),
               model:rec(["a"],0,[])}
        self.assertFalse(science.eligibility(cards,model,24)["eligible"])
        cards[model]=rec(["a","f"],0,["f"])
        self.assertTrue(science.eligibility(cards,model,24)["eligible"])
        cards["joint_balanced48"]["hard_FP"]=0
        self.assertFalse(science.eligibility(cards,model,24)["eligible"])

    def test_candidate_no_reference_oracle_import(self):
        p=(Path(__file__).resolve().parent/"f124bf_public_causal_margin.py").read_text()
        tree=ast.parse(p);imported=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):imported.extend(a.name for a in n.names)
            elif isinstance(n,ast.ImportFrom):imported.append(n.module or "")
        self.assertFalse(any("f124bf_source_only" in s or "f124bc_hard_negative_source" in s
                         or "f124ao_frozen_source" in s for s in imported))
        self.assertEqual(len(science.ARMS),10)
if __name__=="__main__":unittest.main()

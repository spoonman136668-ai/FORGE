"""F124-BE independent nonconsuming tests, synthetic graph only."""
import ast,copy,unittest
from pathlib import Path
import f124be_source_only as source
import f124be_public_peer_contrast as contrast
import f124be_original_fit as science

class BENonconsuming(unittest.TestCase):
    def test_exact_before_implementation_source(self):
        d=source.frozen()
        self.assertEqual(d["source"]["FIT"],[5300000,5300011])
        self.assertEqual(d["source"]["held_SCREEN"],[5300012,5300023])
        self.assertEqual(d["source"]["reserved_DEV"],[5300100,5300123])
        self.assertEqual(len(d["arms"]["candidates"]),6)
        self.assertEqual(d["public"]["fit_examples"],40)
        self.assertEqual(d["public"]["check_examples"],8)
        self.assertTrue(all(x is False for x in d["authority"].values()))
        with self.assertRaises(Exception):source.build(5300100,source.VECTORS[0])
        with self.assertRaises(Exception):source.rows("DEV")

    @staticmethod
    def graph():
        zero=[0]*16
        e=[{"from":"n"+str(i),"to":"n"+str(i+1),"role":"r"+str(i),
            "src_bits":zero[:],"dst_bits":zero[:]} for i in range(7)]
        e += [{"from":"dead"+str(i),"to":"dead"+str(i+1),"role":"decoy",
               "src_bits":zero[:],"dst_bits":zero[:]} for i in range(5)]
        return {"start":"n0","target":"n7",
                "roles":["r"+str(i) for i in range(7)],"edges":e}

    def test_exact_positive_and_public_one_bit_unbacked_contrast(self):
        p=self.graph()
        x=contrast.public_peer_decisions(p)
        self.assertEqual(x["witness_paths"],1)
        self.assertFalse(x["veto_contradicted"])
        self.assertFalse(x["veto_unbacked"])
        h=copy.deepcopy(p)
        h["edges"][3]["src_bits"][5]^=1
        x=contrast.public_peer_decisions(h)
        self.assertEqual(x["witness_paths"],1)
        self.assertFalse(x["veto_contradicted"])
        self.assertTrue(x["veto_unbacked"])
        self.assertFalse(x["veto_both"])

    def test_counterfactual_independent_public_peer_evidence(self):
        h=self.graph()
        h["edges"][3]["src_bits"][5]^=1
        h["edges"].append({"from":"n3","to":"discard",
            "role":"r3","src_bits":[0]*16,"dst_bits":[1]*16})
        x=contrast.public_peer_decisions(h)
        self.assertTrue(x["veto_contradicted"])
        self.assertFalse(x["veto_unbacked"])
        self.assertFalse(x["veto_both"])
        self.assertGreater(x["public_bit_compares"],0)

    def test_hard_fp_gate_cannot_trade_away_feistel_positive(self):
        def rec(positives,hardfp,feistel):
            return {"accepted_positive_case_ids":positives,
                    "accepted_Feistel_positive_case_ids":feistel,
                    "hard_FP":hardfp,"original_FP":0,"positive":len(positives)}
        name="contrast_balanced_unbacked"
        cards={"joint_balanced48":rec(["a","f"],2,["f"]),
               name:rec(["a"],0,[])}
        self.assertFalse(science.eligibility(cards,name,24)["eligible"])
        cards[name]=rec(["a","f"],0,["f"])
        self.assertTrue(science.eligibility(cards,name,24)["eligible"])
        cards["joint_balanced48"]["hard_FP"]=0
        self.assertFalse(science.eligibility(cards,name,24)["eligible"])

    def test_candidate_does_not_import_source_or_oracle(self):
        p=(Path(__file__).resolve().parent/"f124be_public_peer_contrast.py").read_text()
        tree=ast.parse(p)
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
        self.assertFalse(any("f124be_source_only" in s or "f124bc_hard_negative_source" in s
                             or "f124ao_frozen_source" in s for s in imports))
        calls=[n.func.attr for n in ast.walk(tree)
               if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertNotIn("routes15",calls)
        self.assertNotIn("routes",calls)
        self.assertEqual(len(science.ARMS),10)

if __name__=="__main__":unittest.main()

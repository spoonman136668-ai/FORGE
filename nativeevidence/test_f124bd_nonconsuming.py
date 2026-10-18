"""F124-BD non-consuming source/frozen public witness synthetic tests."""
from __future__ import annotations
import ast,copy,unittest
from pathlib import Path
import f124bd_source_only as source
import f124bd_public_path_witness as public
import f124bd_original_fit as science

ROOT=Path(__file__).resolve().parents[0]
class BDNonconsuming(unittest.TestCase):
    def test_frozen_source_sealed_dev(self):
        d=source.frozen()
        self.assertEqual(d["source"]["FIT"],[5200000,5200011])
        self.assertEqual(d["source"]["held_SCREEN"],[5200012,5200023])
        self.assertEqual(d["source"]["reserved_DEV"],[5200100,5200123])
        self.assertEqual(len(d["new_arms"]),6)
        self.assertEqual(d["public"]["total_responses_per_case"],48)
        self.assertTrue(all(x is False for x in d["authority"].values()))
        with self.assertRaises(Exception):
            source.build(5200100,source.VECTORS[0])
        with self.assertRaises(Exception):
            source.rows("DEV")

    def test_independent_public_exact_chain_and_one_bit_nearmiss(self):
        zero=[0]*16
        g={"start":"s0","target":"s7",
           "roles":["r"+str(j) for j in range(7)],"edges":[]}
        for i in range(7):
            e={"from":"s"+str(i),"to":"s"+str(i+1),
               "role":"r"+str(i),"src_bits":list(zero),"dst_bits":list(zero)}
            g["edges"].append(e)
        for i in range(5):
            g["edges"].append({"from":"fake"+str(i),"to":"fake"+str(i+1),
                "role":"not-a-role","src_bits":list(zero),"dst_bits":list(zero)})
        self.assertTrue(public.search_public_path(g,0)["certificate_found"])
        near=copy.deepcopy(g)
        near["edges"][3]["src_bits"][5]^=1
        self.assertFalse(public.search_public_path(near,0)["certificate_found"])
        self.assertTrue(public.search_public_path(near,1)["certificate_found"])
        near["edges"][3]["src_bits"][8]^=1
        self.assertFalse(public.search_public_path(near,1)["certificate_found"])

    def test_public_only_adaptive_rule(self):
        self.assertEqual(public.policy_radius("exact0",{"choice":"feistel"}),0)
        self.assertEqual(public.policy_radius("tolerant1",{"choice":"feistel"}),1)
        self.assertEqual(public.policy_radius("public_adaptive",
            {"choice":"feistel","feistel_check":122}),0)
        self.assertEqual(public.policy_radius("public_adaptive",
            {"choice":"affine","affine_check":112}),1)

    def test_hard_fp_reduction_does_not_permit_positive_loss_or_fp_tie(self):
        def data(ids,fp,feistel):
            return {"accepted_positive_case_ids":ids,
              "accepted_Feistel_positive_case_ids":feistel,
              "positive":len(ids),"original_FP":0,"hard_FP":fp}
        name="witness_balanced_exact"
        pairs={"joint_balanced48":data(["a","f"],2,["f"]),
               name:data(["a"],0,[])}
        self.assertFalse(science.eligibility(pairs,name,24)["eligible"])
        pairs[name]=data(["a","f"],0,["f"])
        self.assertTrue(science.eligibility(pairs,name,24)["eligible"])
        pairs["joint_balanced48"]["hard_FP"]=0
        self.assertFalse(science.eligibility(pairs,name,24)["eligible"])

    def test_model_must_not_import_source_or_original_oracle(self):
        sourcecode=(ROOT/"f124bd_public_path_witness.py").read_text()
        parsed=ast.parse(sourcecode)
        imports=[]
        for n in ast.walk(parsed):
            if isinstance(n,ast.Import):imports.extend(a.name for a in n.names)
            if isinstance(n,ast.ImportFrom):imports.append(n.module or "")
        self.assertFalse(any("f124bd_source_only" in s or "f124bc_hard_negative_source" in s or
                             "f124aa_frozen_source" in s for s in imports))
        self.assertNotIn("routes15(",sourcecode)
        self.assertNotIn("source.relation",sourcecode)
        self.assertEqual(len(science.ARMS),10)
if __name__=="__main__":unittest.main()

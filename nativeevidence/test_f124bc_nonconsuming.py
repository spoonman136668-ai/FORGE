"""F124-BC pre-first-use tests; no real new TRAIN, SCREEN or DEV birth."""
from __future__ import annotations
import ast,copy,unittest
from pathlib import Path
from unittest.mock import patch
import f124bc_hard_negative_source as source
import f124bc_original_hard_negative as experiment
ROOT=Path(__file__).resolve().parents[0]

class BCNonconsuming(unittest.TestCase):
    def test_source_freeze_and_budget(self):
        d=source.frozen()
        self.assertEqual(d["lineage"]["source_parent_exact"],source.PARENT)
        self.assertEqual(d["challenge"]["source_probe_max"],1024)
        self.assertEqual(d["challenge"]["hard_negative_near_miss_bit_edits"],1)
        self.assertEqual(d["public"]["total_responses_per_task"],48)
        self.assertEqual(d["prospective_rules"]["if_hard_coverage_below_18_then_no_held_SCREEN"],True)
        self.assertTrue(all(v is False for v in d["governance"].values()))
        with self.assertRaises(Exception):
            source.build(5100100,source.VECTORS[0])
        with self.assertRaises(Exception):
            source.rows("DEV")

    def test_oracle_negative_first_model_blind_single_bit(self):
        p={"start":0,"target":1,"roles":["publicrole"],"demos":[],
           "edges":[{"src_bits":[0]*16,"dst_bits":[0]*16,"from":0,"to":1,"role":"publicrole"}]}
        n=copy.deepcopy(p);n["edges"][0]["src_bits"][0]=1
        fake_oracle=lambda g,relaxed: int(g["edges"][0]["src_bits"][0]==0)
        with patch.object(source,"plain",lambda graph,op,nonce:graph),patch.object(source,"TRUE_ORACLE",fake_oracle):
            hard,meta=source.model_blind_one_bit_near_miss(p,n,"synthetic","nonce","xor16_permuted")
        self.assertTrue(meta["hard"])
        self.assertEqual(meta["source_oracle_probes"],1)
        self.assertEqual((meta["edit_edge_index"],meta["edit_field"],meta["edit_bit"]),(0,"src_bits",0))
        self.assertFalse(meta["selection_used_model_predictions"])
        self.assertEqual(hard,n)
        self.assertEqual(p["edges"][0]["src_bits"],[0]*16)

    def test_fallback_is_not_hard_negative(self):
        p={"start":0,"target":1,"roles":[],"demos":[],
           "edges":[{"src_bits":[0]*16,"dst_bits":[0]*16,"from":0,"to":1,"role":"r"}]}
        n=copy.deepcopy(p);n["edges"][0]["src_bits"][0]=1
        def always_positive_except_original(graph,relaxed):
            return 0 if graph["edges"][0]["src_bits"][0]==1 else 1
        # A synthetic oracle whose only one-bit negative is disabled by only
        # scoring destination field? More robust: mark original via special
        # separate identity marker that all deep-copy variations of p retain.
        p["oracle_tag"]="positive";n["oracle_tag"]="negative"
        with patch.object(source,"plain",lambda graph,op,nonce:graph),patch.object(source,"TRUE_ORACLE",
             lambda graph,relaxed:int(graph["oracle_tag"]=="positive")):
            selected,meta=source.model_blind_one_bit_near_miss(p,n,"syn","nonce","xor16_permuted")
        self.assertFalse(meta["hard"])
        self.assertEqual(meta["source_oracle_probes"],32)
        self.assertEqual(selected,n)
        self.assertIsNone(meta["edit_hamming_bits"])

    def test_model_imports_and_scientific_scope(self):
        src=(ROOT/"f124bc_original_hard_negative.py").read_text()
        tree=ast.parse(src)
        self.assertNotIn("scientific_protected_acceptance":True",src)
        self.assertIn("if open_screen:",src)
        self.assertIn("if_hard_coverage",str(source.frozen()["prospective_rules"]))
        self.assertEqual(len(experiment.ARMS),4)

if __name__=="__main__":unittest.main()

"""F124-AY pre-first-use source/cost assertions. No actual TRAIN case is born."""
from __future__ import annotations
import ast
import random
import unittest
from pathlib import Path
import f124ay_source_only as source
import f124ay_structural_diagnostics as d

ROOT=Path(__file__).resolve().parents[1]
class TestAYNonconsuming(unittest.TestCase):
    def test_exact_source_contract(self):
        contract=source.frozen()
        self.assertEqual(contract["lineage"]["qualified_parent"],source.PARENT)
        self.assertEqual(contract["cohort"]["FIT_cases"],24)
        self.assertEqual(contract["cohort"]["SCREEN_cases_constructed"],0)
        self.assertEqual(contract["cohort"]["DEV_cases_constructed"],0)
        self.assertEqual(contract["cohort"]["public_48"]["corruptions"],6)
        self.assertEqual(contract["cohort"]["public_96_diagnostic_only"]["corruptions"],12)
        self.assertEqual(contract["cohort"]["structural_witness"]["base_outputs"],[0,23130,45975])
        self.assertEqual(len(contract["cohort"]["structural_witness"]["triple_bit_sets"]),8)

    def test_no_reserved_source_birth(self):
        for seed in (source.SCREEN.start,source.RESERVED_DEV.start):
            with self.assertRaises(Exception):
                source.build_fit(seed,source.VECTORS[0])

    def test_fit_diagnosis_synthetic_invertible(self):
        rng=random.Random("F124AY_NONSCIENCE_IDENTITY")
        samples=rng.sample(range(65536),48)
        public=[{"input_bits":d.asbits(x),"output_bits":d.asbits(x)}
                for x in samples]
        result=d.probe(public,"synthetic-identity")
        self.assertEqual(result["attempts"],256)
        self.assertGreater(result["rank_valid_fits"],0)
        self.assertEqual(result["first_hard_blocker"],"ADMITTED")
        self.assertTrue(result["original_AX_admitted"])
        self.assertFalse(result["oracle_or_operator_seen_by_model"])

    def test_no_evaluator_import_in_diagnostic_probe(self):
        tree=ast.parse((ROOT/"nativeevidence/f124ay_structural_diagnostics.py").read_text())
        funcs={node.name:node for node in tree.body
               if isinstance(node,ast.FunctionDef)}
        probe_text=ast.unparse(funcs["probe"])
        self.assertNotIn("source.relation",probe_text)
        self.assertNotIn("source.plain",probe_text)
        self.assertIn("source.relation",ast.unparse(funcs["witness"]))
if __name__=="__main__":unittest.main()

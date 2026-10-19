"""F124-CX source-free BPTT capacity×optimizer exact engineering qualification.

Uses only prior SOURCE-FREE CW toy episodes, never consumed scientific
first-use source artifacts or any source-birth generator. No model promotion.
"""
from __future__ import annotations
import ast
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124ct_sequence_protocol as p
import f124cx_factorial_cell as cell
import f124cw_feasibility_audit as cw
import f124cx_readonly_factorial as audit

class FrozenHeadroomEngineering(unittest.TestCase):
    def test_8dim_original_training_receipt_is_unchanged(self):
        p.HIDDEN=8
        p.EPOCHS=45
        _,fit,check,_=cw.fixture("dense",0)
        for arm in cell.ARMS:
            model=cell.load_frozen(arm)
            _,trained=model.train(fit,check)
            _,receipt=cell.fit_model(model,fit,check,45)
            self.assertAlmostEqual(
               receipt["initial_FIT_BCE"],
               trained["initial_FIT_bit_cross_entropy"],places=11)
            self.assertAlmostEqual(
               receipt["final_FIT_BCE"],
               trained["final_FIT_bit_cross_entropy"],places=11)
            self.assertEqual(receipt["FIT_bit_errors"],trained["FIT_bit_errors"])
            self.assertEqual(receipt["CHECK_bit_errors"],trained["CHECK_bit_errors"])
            self.assertEqual(receipt["natural_admitted_by_frozen_CHECK_veto"],
                             trained["natural_model_admission"])
    def test_sourcefree_large_capacity_trains_same_strong_peer_and_candidate(self):
        for arm in cell.ARMS:
            z=cell.run_cell("dense",0,16,45,arm)
            self.assertEqual(z["hidden"],16)
            self.assertEqual(z["epochs"],45)
            self.assertTrue(z["full_BPTT"])
            self.assertFalse(z["scientific_acceptance"])
            self.assertEqual(z["scientific_firstuse_consumed"],0)
            self.assertTrue(0<=z["diagnostic_heldout_exact_episodes_of_8"]<=8)
            self.assertGreater(z["trainable_parameters"],0)
    def test_attention_scaling_recomputed_for_hidden_16(self):
        p.HIDDEN=16
        m=cell.load_frozen("attentive")
        self.assertEqual(m.ATTENTION_DIVISOR,4.0)
        p.HIDDEN=8
        m=cell.load_frozen("attentive")
        self.assertAlmostEqual(m.ATTENTION_DIVISOR,2**1.5)
    def test_no_prior_scientific_birth_modules_or_case_inputs(self):
        for name in ("f124cx_factorial_cell.py",
                     "f124cx_whole_os_shard.py",
                     "f124cx_readonly_factorial.py"):
            tree=ast.parse((HERE/name).read_text())
            imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    imports.extend(a.name for a in node.names)
                elif isinstance(node,ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any(x.startswith(("f124cu_","f124cr_",
                "f124co_","f124cn_","f124cm_")) for x in imports),name)
        self.assertEqual(cell.HIDDENS,(8,16))
        self.assertEqual(cell.EPOCHS,(45,135))
        self.assertEqual(cell.ARMS,("attentive","gated"))
    def test_readonly_review_requires_all_64_unselected_cells(self):
        with __import__("tempfile").TemporaryDirectory() as folder:
            with self.assertRaises(RuntimeError):
                audit.validate_shards(Path(folder))
    def test_causal_model_heldout_outcome_is_diagnostic_only(self):
        p.HIDDEN=8
        c=cell.run_cell("sparse",1,8,45,"gated")
        self.assertEqual(c["public_training_FIT_SHA256"],
                         p.digest(cw.fixture("sparse",1)[1]))
        self.assertTrue(c["diagnostic_heldout_not_scientific_model_admission"])
        self.assertFalse(c["original_source_or_oracle_imported"])
        self.assertEqual(c["fit_episodes"],24)
        self.assertEqual(c["check_veto_episodes"],8)

if __name__=="__main__":
    unittest.main()

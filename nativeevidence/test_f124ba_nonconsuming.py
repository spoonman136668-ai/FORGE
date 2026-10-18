"""F124-BA non-consuming preflight: synthetic public evidence only."""
from __future__ import annotations
import ast
import random
import unittest
from pathlib import Path
import f124ba_train_source as source
import f124ba_public_confidence as model
import f124ba_fit_screen as experiment
import f124ay_learned_composition as nonlinear

ROOT=Path(__file__).resolve().parents[1]
def bits(n):return [(n>>i)&1 for i in range(16)]
class ConfidenceTests(unittest.TestCase):
    def test_sealed_source(self):
        doc=source.frozen()
        self.assertEqual(doc["lineage"]["parent_qualified_head"],source.PARENT_SHA)
        self.assertEqual(doc["public_budget"]["total_per_task"],48)
        self.assertEqual(len(doc["candidates"]["confidence_new"]["threshold_grid"]),6)
        self.assertFalse(any(doc["authority"].values()))
        with self.assertRaises(Exception):
            source.build_train(4900100,source.VECTORS[0])
        with self.assertRaises(Exception):
            source.rows("DEV")

    def test_key_confidence_all_public_synthetic(self):
        rnd=random.Random("F124BA_SYNTHETIC_PUBLIC_ONLY")
        values=rnd.sample(range(65536),48)
        rows=[{"input_bits":bits(x),"output_bits":nonlinear.forward_bits(bits(x),23)}
              for x in values]
        fitted=nonlinear.train(rows,"learned_two_round_keyed")
        self.assertEqual(fitted["learned_key"],23)
        allowed,diag=model.gate_public_feistel(fitted,rows,112,12,0)
        self.assertTrue(allowed)
        self.assertEqual(diag["public_CHECK_total"],128)
        self.assertGreaterEqual(diag["sourceblind_FIT_runnerup_gap"],0)
        corrupted=[dict(x) for x in rows]
        corrupted[40]={"input_bits":list(rows[40]["input_bits"]),
                       "output_bits":bits(0xFFFF^nonlinear.int16(rows[40]["output_bits"]))}
        allowed,diag=model.gate_public_feistel(fitted,corrupted,112,12,0)
        self.assertFalse(allowed)
        self.assertLess(diag["min_CHECK_each"],12)

    def test_affine_route_is_unmodified(self):
        rnd=random.Random("F124BA_PUBLIC_ONLY_AFFINE")
        values=rnd.sample(range(65536),48)
        rows=[{"input_bits":bits(x),"output_bits":bits(x)} for x in values]
        new=model.train(rows,"syn-identity","balanced_basis48",112,12,0)
        self.assertEqual(new["choice"],"affine")
        self.assertTrue(new["f124ba_confidence"]["affine_route_untouched"])
        self.assertEqual(new["f124ba_confidence"]["extra_key_search_candidates"],0)

    def test_FIT_admission_rejects_any_false_positive_or_loss(self):
        names=[k[0] for k in experiment.SPECS]
        def rec(correct,fp,feistel,ids):
            return {"paired":correct,"FP":fp,"FN":24-correct,
                "by_operator":{"feistel":{"paired":feistel}},
                "accepted_positive_case_ids":ids}
        d={names[0]:rec(9,0,0,["a","b"]),names[1]:rec(10,0,0,["a","b"])}
        candidate=experiment.NEW[0][0]
        d[candidate]=rec(20,1,11,["a","b","c"])
        ok,_=experiment.eligible(d,candidate)
        self.assertFalse(ok)
        d[candidate]["FP"]=0
        d[candidate]["accepted_positive_case_ids"]=["a","c"]
        ok,_=experiment.eligible(d,candidate)
        self.assertFalse(ok)
        d[candidate]["accepted_positive_case_ids"]=["a","b","c"]
        ok,_=experiment.eligible(d,candidate)
        self.assertTrue(ok)

    def test_prohibit_direct_source_import_in_public_model(self):
        text=(ROOT/"nativeevidence/f124ba_public_confidence.py").read_text()
        root=ast.parse(text)
        names=[]
        for node in ast.walk(root):
            if isinstance(node,ast.Import):names.extend(x.name for x in node.names)
            elif isinstance(node,ast.ImportFrom):names.append(node.module or "")
        self.assertFalse(any("f124ba_train_source" in name or
                   "f124az_train_source" in name for name in names))
        self.assertNotIn("operator_name",text.split("def train(")[-1])

if __name__=="__main__":
    unittest.main()

"""F124-CH source-only tests: no prospective family IDs or seeds consumed."""
from __future__ import annotations
import ast
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"f124ch_internal_source.py"
spec=importlib.util.spec_from_file_location("internal_EF_source_only",SOURCE)
src=importlib.util.module_from_spec(spec)
spec.loader.exec_module(src)

class EFFrozenSourceMath(unittest.TestCase):
    def test_novel_conditional_intervention_is_reversible(self):
        for param in [(1,7,9,2),(9,2,15,8),(15,1,4,0)]:
            for value in range(65536):
                y=src.E_forward(value,param)
                self.assertEqual(src.E_inverse(y,param),value)

    def test_nonlinear_branch_feedback_is_reversible(self):
        for param in [(71,17,229,62),(15,67,234,41),(1,2,3,4)]:
            for value in range(65536):
                y=src.F_forward(value,param)
                self.assertEqual(src.F_inverse(y,param),value)

    def test_different_grammars_not_fixed_nibble_affine(self):
        pE=(1,7,9,2)
        pF=(71,17,229,62)
        self.assertNotEqual(
            [src.E_forward(x,pE) for x in (0,1,2,3,16,256,4096)],
            [src.F_forward(x,pF) for x in (0,1,2,3,16,256,4096)]
        )
        a=src.E_forward(0x1234,pE)
        b=src.E_forward(0x9234,pE)
        self.assertNotEqual(a&0xfff,b&0xfff)

    def test_source_never_imports_model_native_or_evaluator(self):
        tree=ast.parse(SOURCE.read_text())
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imports.extend(a.name for a in node.names)
            if isinstance(node,ast.ImportFrom):
                imports.append(node.module or "")
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
                self.assertNotIn(node.func.id,("eval","exec","__import__","compile"))
        self.assertFalse(any("f124c" in s.lower() or
                             "nativeevidence" in s.lower() or
                             "forge" in s.lower() or
                             "optimizer" in s.lower()
                             for s in imports))
        self.assertEqual(src.FAMILIES,{"E":928000,"F":929000})
        self.assertEqual(src.CORRUPTED_FIT,{1,5,12,19,24,35})

    def test_no_old_or_protected_firstuse_exposed_by_module(self):
        self.assertEqual(src.DEV_COUNT,12)
        self.assertFalse(hasattr(src,"learn"))
        self.assertFalse(hasattr(src,"score"))
        self.assertTrue(all(928000<=v<=929000 for v in src.FAMILIES.values()))

if __name__=="__main__":
    unittest.main()

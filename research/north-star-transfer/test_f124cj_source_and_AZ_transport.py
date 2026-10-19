"""F124-CJ SOURCE-ONLY pre-firstuse qualification with native public parser.

NEVER generate E2/F2 prospective task source seeds/IDs or fit any model.
Only use static arbitrary synthetic public graph, parse its transport grammar.
"""
import ast
import importlib.util
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"f124cj_internal_source.py"
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location("F124CJ_source_grammar_only",SOURCE)
src=importlib.util.module_from_spec(spec)
spec.loader.exec_module(src)
sys.path.insert(0,str(ROOT/"nativeevidence"))
from f124aj_example_operator_learner import public_task

def dummy():
    nonce="deadbeefcafe"
    roles=[f"rel_task_{nonce}:binding_{i}" for i in range(8)]
    graph={
      "start":"node0","target":"node8","roles":roles,
      "edges":[{"from":f"node{i}","to":f"node{i+1}",
                "role":roles[i],
                "src_bits":[0]*16,"dst_bits":[0]*16} for i in range(8)],
      "demos":[{"input_bits":[0]*16,"output_bits":[0]*16} for _ in range(24)]
    }
    return graph

class PrebirthPublicTransport(unittest.TestCase):
    def test_original_AZ_unmodified_parser_accepts_new_opaque_role_envelope(self):
        graph=dummy()
        clean,demos,nonce=public_task(graph)
        self.assertEqual(nonce,"deadbeefcafe")
        self.assertEqual(len(clean["edges"]),8)
        self.assertEqual(len(demos),24)
        self.assertEqual(clean["roles"],[f"binding_{i}" for i in range(8)])

    def test_source_math_invertible_before_source_case_birth(self):
        for p in ((1,7,9,2),(9,2,15,8)):
            for x in range(65536):
                self.assertEqual(src.E_inverse(src.E_forward(x,p),p),x)
        for p in ((71,17,229,62),(15,67,234,41)):
            for x in range(65536):
                self.assertEqual(src.F_inverse(src.F_forward(x,p),p),x)

    def test_original_causal_laws_not_retuned_or_evaluator_imported(self):
        self.assertEqual(src.FAMILIES,{"E2":930000,"F2":931000})
        self.assertEqual(src.CORRUPTED_FIT,{1,5,12,19,24,35})
        tree=ast.parse(SOURCE.read_text())
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imports.extend(x.name for x in node.names)
            if isinstance(node,ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("nativeevidence" in s or "f124c" in s
                             or "forge" in s.lower() or "optimizer" in s
                             for s in imports))
        self.assertIn('rel_task_{tag}:binding_{j}',SOURCE.read_text())
        self.assertNotIn('causal_{tag}_step_',SOURCE.read_text())
        self.assertEqual(src.DEV_COUNT,12)

    def test_old_partial_source_case_IDs_unavailable(self):
        self.assertFalse({930000,931000}&{928000,929000})
        self.assertTrue(all(x not in range(928000,930000)
                            for x in src.FAMILIES.values()))

if __name__=="__main__":
    unittest.main()

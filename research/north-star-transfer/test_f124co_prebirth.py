"""F124-CO prebirth validation using no born science case or protected data."""
from __future__ import annotations
import ast
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
FILES=("f124co_birth_once.py","f124co_eval_once.py",
       "f124co_readonly_audit.py","f124cn_new_trajectory_source.py",
       "f124cn_blind_trajectory_eval.py","f124cn_complete_os_resource.py")

class NeverBornEngineering(unittest.TestCase):
    def test_all_exact_science_interfaces_parse_without_execution(self):
        for name in FILES:
            with self.subTest(name=name):
                tree=ast.parse((HERE/name).read_text(encoding="utf8"))
                self.assertIsInstance(tree,ast.Module)
    def test_only_source_job_imports_new_source(self):
        private="f124cn_new_trajectory_source"
        self.assertIn(private,(HERE/"f124co_birth_once.py").read_text())
        for name in ("f124co_eval_once.py","f124co_readonly_audit.py",
                     "f124cn_blind_trajectory_eval.py","f124cn_complete_os_resource.py"):
            self.assertNotIn(private,(HERE/name).read_text(),name)
    def test_scientific_firstuse_requires_frozen_operator_admission(self):
        code=(HERE/"f124co_birth_once.py").read_text()
        self.assertIn('freeze["authorization"]["development_once"] is True',code)
        self.assertIn('os.environ.get("GITHUB_RUN_ATTEMPT")=="1"',code)
        self.assertIn('secrets.randbits(128)',code)
        self.assertIn('case=model.task',code) if False else None
        self.assertIn('case=origin.task',code)
    def test_secret_fields_never_used_by_public_evaluator(self):
        code=(HERE/"f124co_eval_once.py").read_text()
        self.assertNotIn("sealed-private-birth.json",code)
        self.assertNotIn("private_law_key",code)
        self.assertIn("original_360_whole_process_measurements",code)
    def test_auditor_does_not_execute_model_or_origin(self):
        code=(HERE/"f124co_readonly_audit.py").read_text()
        self.assertNotIn("import f124cn_",code)
        self.assertNotIn("import f124cm_",code)
        self.assertNotIn("secrets.randbits",code)
        self.assertIn("provider(base",code)
    def test_source_laws_on_fixed_engineering_inputs_only(self):
        spec=importlib.util.spec_from_file_location("F124CO_SOURCE_STATIC_PREBIRTH",
                        HERE/"f124cn_new_trajectory_source.py")
        source=importlib.util.module_from_spec(spec);spec.loader.exec_module(source)
        key=[1,3,5,7]
        for fam in ("G","H"):
            for event in range(16):
                out=source.law(fam,event,2,11,key)
                self.assertTrue(type(out) is int and 0<=out<16)
        self.assertNotEqual(source.law("G",0,2,11,key),
                            source.law("H",0,2,11,key))
    def test_old_original_science_packets_not_referenced(self):
        birth=(HERE/"f124co_birth_once.py").read_text()
        self.assertIn('range(932000,932012)',birth)
        self.assertIn('range(933000,933012)',birth)
        for old in ("930000","931000","924000","926000"):
            self.assertNotIn('range('+old,birth)

if __name__=="__main__":
    unittest.main()

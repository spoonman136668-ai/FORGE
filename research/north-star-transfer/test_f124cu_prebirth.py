"""F124-CU prebirth source-free engineering: never call scientific task().

Uses the previously qualified deterministic 3-role synthetic full-episode
learning fixture with synthetic case_id=-1, never 936/937 origination.
"""
from __future__ import annotations
import ast
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import test_f124ct_sequence_memory as toy
import f124cu_blind_sequence_eval as evaluator
import f124cu_whole_os_cost as observer
import f124cu_private_source_only as unknown

HERE=Path(__file__).resolve().parent

def fixture():
    fit,check=toy.toy_episodes()
    positive=copy.deepcopy(check[0])
    negative=copy.deepcopy(positive)
    ev=positive["events"]
    pair=next((i,j) for i in range(8) for j in range(i+1,8)
              if ev[i]["target"]!=ev[j]["target"] and
              ev[i]["observed"]!=ev[j]["observed"])
    i,j=pair
    negative["events"][i]["observed"],negative["events"][j]["observed"]=(
        negative["events"][j]["observed"],negative["events"][i]["observed"])
    return {"case_id":-1,"FIT":fit,"CHECK":check,
            "positive":positive,"hard_negative":negative}

class OriginalBeforeBirth(unittest.TestCase):
    def test_independent_source_math_is_bounded_no_case_birth(self):
        key=[3,5,9,2]
        for family in ("L","M"):
            for event in range(16):
                value=unknown.law(family,event,6,2,5,4,key)
                self.assertTrue(type(value) is int and 0<=value<16)
        self.assertNotEqual([unknown.law("L",x,6,2,5,4,key) for x in range(16)],
                            [unknown.law("M",x,6,2,5,4,key) for x in range(16)])
    def test_no_candidate_or_oracle_import_in_source_generator(self):
        t=ast.parse((HERE/"f124cu_private_source_only.py").read_text())
        names=[]
        for n in ast.walk(t):
            if isinstance(n,ast.Import):names.extend(a.name for a in n.names)
            if isinstance(n,ast.ImportFrom):names.append(n.module or "")
        self.assertFalse(any("f124ct" in x or "eval" in x or "torch" in x
                             for x in names))
        self.assertEqual(unknown.BASE,{"L":936000,"M":937000})
    def test_both_fully_trained_models_natural_native_route(self):
        f=fixture()
        candidate=evaluator.evaluate(f,"CANDIDATE",synthetic=True)
        peer=evaluator.evaluate(f,"TRAINED_CONTROL",synthetic=True)
        self.assertTrue(candidate["natural_trained_admission"],candidate["full_training_and_CHECK_receipt"])
        self.assertTrue(peer["natural_trained_admission"],peer["full_training_and_CHECK_receipt"])
        for field in ("public_case_sha256","identical_native_public_graph_hashes",
                      "identical_train_FIT_sha256","identical_veto_CHECK_sha256"):
            self.assertEqual(candidate[field],peer[field])
        self.assertEqual(candidate["native_event_count"],peer["native_event_count"])
        self.assertEqual(candidate["native_event_count"],16)
        self.assertFalse(candidate["science_accepted"])
        self.assertFalse(peer["science_accepted"])
    def test_no_leakage_of_private_seed_or_old_case_id(self):
        f=fixture();f["private_law_key"]="illegal"
        with self.assertRaises(ValueError):
            evaluator.evaluate(f,"CANDIDATE",synthetic=True)
        f=fixture();f["case_id"]=934000
        with self.assertRaises(ValueError):
            evaluator.evaluate(f,"CANDIDATE",synthetic=True)
        f=fixture();f["case_id"]=932000
        with self.assertRaises(ValueError):
            evaluator.evaluate(f,"TRAINED_CONTROL")
    def test_original_scripts_parse_without_executing_scientific_birth(self):
        for file in ("f124cu_birth_once.py","f124cu_eval_once.py",
                     "f124cu_independent_audit.py","f124cu_whole_os_cost.py"):
            self.assertIsInstance(ast.parse((HERE/file).read_text()),ast.Module)
    def test_five_original_case_costs_cannot_be_inferred_from_synthetic(self):
        with self.assertRaises(RuntimeError):observer.review([],[])
    @unittest.skipUnless(sys.platform=="linux","Linux complete wait4 measurements only")
    def test_linux_full_model_training_CPU_and_RSS_synthetic_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"synthetic.json";path.write_text(json.dumps(fixture()))
            a=observer.observe(path,"CANDIDATE",synthetic=True)
            b=observer.observe(path,"TRAINED_CONTROL",synthetic=True)
            self.assertEqual(a["public_case_sha256"],b["public_case_sha256"])
            self.assertTrue(a["OS_measurement_includes_Python_start_NumPy_import_full_BPTT_and_scoring"])
            self.assertGreater(a["full_OS_CPU_ns"],0)
            self.assertGreater(b["full_OS_peak_RSS_bytes"],0)
            observer.append(Path(folder)/"append.jsonl",{"preflight":True,"reading":a})
            self.assertEqual(len((Path(folder)/"append.jsonl").read_text().splitlines()),1)

if __name__=="__main__":unittest.main()

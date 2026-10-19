"""F124-CR strict prebirth engineering with synthetic -1 fixture ONLY.

Never invoke original source task() or create 934/935 cases. Tests use
deliberately synthetic CQ toy rule and static SOURCE-ONLY math sanity.
"""
from __future__ import annotations
import ast
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import sys

HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

baseline=load("CQ_frozen_static_eng_fixture","test_f124cq_learned_relational.py")
source=load("CR_only_static_law_math","f124cr_source_only.py")
scorer=load("CR_only_blinded_route","f124cr_blind_native.py")
resource=load("CR_only_OS_observer","f124cr_complete_os.py")

def synthetic():
    fit,check=baseline.fixture()
    p,n=baseline.public_graphs()
    replace={"a":"north","b":"south"}
    def graph(g):
        return {"initial":{replace[k]:v for k,v in g["initial"].items()},
                "events":[{"role":replace[x["role"]],"event":x["event"],
                           "observed":x["observed"]} for x in g["events"]]}
    return {"case_id":-1,"FIT":fit,"CHECK":check,
            "positive":graph(p),"hard_negative":graph(n)}

class CRPrebirthOnly(unittest.TestCase):
    def test_all_new_runners_parse_without_original_experiment(self):
        for file in ("f124cr_source_only.py","f124cr_blind_native.py",
                     "f124cr_complete_os.py","f124cr_birth_once.py",
                     "f124cr_eval_once.py","f124cr_independent_readonly_audit.py"):
            self.assertIsInstance(ast.parse((HERE/file).read_text()),ast.Module)
    def test_original_source_import_boundary_no_candidate_or_competitor(self):
        tree=ast.parse((HERE/"f124cr_source_only.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                names=[x.name for x in node.names]
            elif isinstance(node,ast.ImportFrom):
                names=[node.module or ""]
            else:
                continue
            self.assertFalse(any("f124cq" in name or "f124cr_blind" in name
                                 or "native" in name for name in names))
        self.assertEqual(source.BASE,{"J":934000,"K":935000})
    def test_new_laws_are_bounded_and_distinct_on_static_engineering_values(self):
        p=(5,3,7,1)
        for family in ("J","K"):
            results=[source.law(family,e,4,9,p) for e in range(16)]
            self.assertTrue(all(type(x) is int and 0<=x<16 for x in results))
        self.assertNotEqual([source.law("J",e,4,9,p) for e in range(16)],
                            [source.law("K",e,4,9,p) for e in range(16)])
    def test_trained_arms_natural_native_same_synthetic_inputs(self):
        task=synthetic()
        one=scorer.evaluate(task,"CANDIDATE",synthetic=True)
        peer=scorer.evaluate(task,"TRAINED_CONTROL",synthetic=True)
        self.assertEqual(one["public_task_sha256"],peer["public_task_sha256"])
        self.assertEqual(one["native_public_input_sha256"],
                         peer["native_public_input_sha256"])
        self.assertTrue(one["natural_model_admission"],one["trained_model_receipt"])
        self.assertTrue(peer["natural_model_admission"],peer["trained_model_receipt"])
        self.assertEqual(one["native_graph_calls"],peer["native_graph_calls"])
        self.assertEqual(one["native_event_transition_calls"],
                         peer["native_event_transition_calls"])
        self.assertEqual(one["native_event_transition_calls"],20)
        self.assertTrue(one["correct_paired_causal_task"])
        self.assertFalse(one["hard_false_positive"])
        self.assertFalse(one["science_accepted"])
    def test_private_seed_and_consumed_ids_fail_before_scoring(self):
        task=synthetic();task["private_seed"]="illegal"
        with self.assertRaises(ValueError):
            scorer.evaluate(task,"CANDIDATE",synthetic=True)
        t=synthetic();t["case_id"]=932000
        with self.assertRaises(ValueError):scorer.evaluate(t,"TRAINED_CONTROL")
        t=synthetic();t["case_id"]=935500
        with self.assertRaises(ValueError):scorer.evaluate(t,"CANDIDATE")
    def test_check_veto_causes_natural_zero_native_calls(self):
        task=synthetic()
        task["CHECK"][0][3]^=1
        for arm in ("CANDIDATE","TRAINED_CONTROL"):
            x=scorer.evaluate(task,arm,synthetic=True)
            self.assertFalse(x["natural_model_admission"])
            self.assertEqual(x["native_graph_calls"],0)
            self.assertEqual(x["native_event_transition_calls"],0)
            self.assertFalse(x["correct_paired_causal_task"])
    def test_unqualified_resource_roster_never_passes(self):
        with self.assertRaises(RuntimeError):resource.summarize([],[])
    @unittest.skipUnless(sys.platform=="linux","Actual wait4 whole OS Linux only")
    def test_real_whole_process_CPU_RSS_without_scientific_birth(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            path=root/"synthetic-only.json"
            path.write_text(json.dumps(synthetic()))
            a=resource.measure_case(path,"CANDIDATE",synthetic=True)
            b=resource.measure_case(path,"TRAINED_CONTROL",synthetic=True)
            self.assertTrue(a["OS_measurement_includes_boot_import_fit_native_scoring"])
            self.assertGreater(a["complete_OS_CPU_ns"],0)
            self.assertGreater(b["complete_OS_peak_RSS_bytes"],0)
            self.assertEqual(a["native_public_input_sha256"],b["native_public_input_sha256"])
            resource.durable_append(root/"append.jsonl",{"preflight":True,"reading":a})
            resource.durable_append(root/"append.jsonl",{"preflight":True,"reading":b})
            self.assertEqual(len((root/"append.jsonl").read_text().splitlines()),2)

if __name__=="__main__":unittest.main()

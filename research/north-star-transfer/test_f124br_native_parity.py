"""F124-BR source-neutral parity: new low-allocation view == frozen AJ+AG.

No prospective science or previously consumed data. The whole original
graph remains byte-for-byte unmodified across native execution.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[1]/"nativeevidence"
sys.path.insert(0,str(NATIVE))
import f124ag_transition_models as native
import f124aj_example_operator_learner as parser


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


model=load("br_original_BQ_learned","f124bq_program_learner.py")
view=load("br_low_allocation_native_view","f124br_native_view.py")
original=load("br_prior_synthetic_source_neutral","f124bq_resource_prebirth.py")
BASE=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
DELTA=[0.,0.]


class NativePathConformance(unittest.TestCase):
    def test_original_source_unchanged_and_exact_native_score_parity(self):
        support,pos,neg,task=original.graph_and_public()
        raw=json.dumps([pos,neg],sort_keys=True,separators=(",",":"))
        prog,receipt,plausible=model.learn(support[:40],support[40:])
        self.assertIsNotNone(prog)
        self.assertTrue(receipt["learned_from_FIT_only"])
        for graph in (pos,neg):
            legacy,demos,nonce=parser.public_task(graph)
            compact,demos2,nonce2=view.public_native_view(graph)
            self.assertEqual(compact,legacy)
            self.assertEqual(demos,demos2)
            self.assertEqual(nonce,nonce2)
            old,_,_=view.decoded_native(
                graph,model,prog,native,legacy_parser=parser)
            new,_,_=view.decoded_native(graph,model,prog,native)
            self.assertEqual(old,new)
            old_result=native.ygg_transition(old,list(BASE),list(DELTA),.1)
            new_result=native.ygg_transition(new,list(BASE),list(DELTA),.1)
            self.assertEqual(old_result,new_result)
        old=view.score_exact_native_pair(
            (pos,neg),model,prog,native,BASE,DELTA,legacy_parser=parser)
        new=view.score_exact_native_pair((pos,neg),model,prog,native,BASE,DELTA)
        self.assertEqual(old,new)
        self.assertEqual(json.dumps([pos,neg],sort_keys=True,separators=(",",":")),raw)
        self.assertEqual(model.causal_consensus(pos,prog,plausible)[0],True)
        self.assertEqual(model.causal_consensus(neg,prog,plausible)[0],False)

    def test_reject_all_invalid_public_role_and_support_shapes(self):
        _,graph,_,_=original.graph_and_public()
        corruptions=[]
        g=copy.deepcopy(graph);g["roles"][0]="rel_task_invalid:broken";corruptions.append(g)
        g=copy.deepcopy(graph);g["roles"]=g["roles"][:6];corruptions.append(g)
        g=copy.deepcopy(graph);g["demos"]=g["demos"][:23];corruptions.append(g)
        g=copy.deepcopy(graph);g["demos"][0]["input_bits"]=[2]*16;corruptions.append(g)
        g=copy.deepcopy(graph);g["edges"][0]["role"]="rel_task_000000000000:wrong";corruptions.append(g)
        g=copy.deepcopy(graph);g["extra"]=0;corruptions.append(g)
        for item in corruptions:
            with self.subTest(label=str(item["roles"][0])):
                with self.assertRaises((ValueError,RuntimeError,TypeError)):
                    parser.public_task(item)
                with self.assertRaises((ValueError,RuntimeError,TypeError)):
                    view.public_native_view(item)

    def test_dst_bits_borrowed_readonly_and_src_copied_only_after_decoding(self):
        _,graph,_,_=original.graph_and_public()
        prog=(53,37,41,19,0,1)
        public,_,_=view.public_native_view(graph)
        for a,b in zip(graph["edges"],public["edges"]):
            self.assertIs(a["dst_bits"],b["dst_bits"])
            self.assertIs(a["src_bits"],b["src_bits"])
        actual,_,_=view.decoded_native(graph,model,prog,native)
        for source,decoded in zip(graph["edges"],actual["edges"]):
            self.assertIs(source["dst_bits"],decoded["dst_bits"])
            self.assertIsNot(source["src_bits"],decoded["src_bits"])


if __name__=="__main__":
    unittest.main()

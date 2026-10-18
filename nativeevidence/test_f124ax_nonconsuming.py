"""F124-AX non-consuming focused tests: never construct DEV, never run TRAIN-SCREEN."""
from __future__ import annotations
import ast
import json
import random
import unittest
from pathlib import Path

import f124ax_train_source as source
import f124ax_sparse_quadratic as quadratic

ROOT=Path(__file__).resolve().parents[1]

class FrozenAXTests(unittest.TestCase):
    def test_immutable_contract(self):
        document=source.frozen()
        self.assertEqual(document["lineage"]["parent_qualified_head"],
                         source.PARENT_HEAD)
        self.assertEqual([x["public_responses"] for x in document["candidate_grid"]],
                         [48,48,48,48])
        self.assertTrue(all(x["fit_rows"]==40 and x["check_rows"]==8
                            and x["fit_trials"]==256 for x in document["candidate_grid"]))
        self.assertFalse(any(document["authority"].values()))
        self.assertTrue(set(source.TRAIN).isdisjoint(source.RESERVED_DEV))

    def test_no_dev_source_path(self):
        with self.assertRaises(Exception):
            source.build_train(source.RESERVED_DEV.start,source.VECTORS[0])
        with self.assertRaises(Exception):
            source.train_rows("DEV")

    def test_public_query_equivalence(self):
        seed=source.TRAIN.start
        vector=source.VECTORS[0]
        family,op,nonce,p,n=source.build_train(seed,vector)
        self.assertEqual(p["demos"],n["demos"])
        active=source.public_48(seed,vector,op,"balanced_basis48",p["demos"])
        random_queries=source.public_48(seed,vector,op,"random48",p["demos"])
        self.assertEqual((len(active),len(random_queries)),(48,48))
        self.assertEqual(active[:24],random_queries[:24])
        self.assertEqual(sum(source.relation(x["input_bits"],op)!=x["output_bits"]
                             for x in active),6)
        self.assertEqual(sum(source.relation(x["input_bits"],op)!=x["output_bits"]
                             for x in random_queries),6)

    def test_sparse_model_identity_without_truth_access(self):
        rng=random.Random(124_450_001)
        numbers=rng.sample(range(65536),48)
        demo=[{"input_bits":[(n>>j)&1 for j in range(16)],
               "output_bits":[(n>>j)&1 for j in range(16)]} for n in numbers]
        fitted,meta=quadratic.fit(demo,"f124ax-synthetic-unit")
        self.assertIsNotNone(fitted)
        self.assertEqual(meta["fit_solver_trials"],256)
        self.assertTrue(meta["full_domain_bijection_proved"])
        self.assertFalse(meta["source_operator_known"])
        for sample in demo:
            self.assertEqual(quadratic.transform(sample["output_bits"],*fitted),
                             sum(k<<j for j,k in enumerate(sample["input_bits"])))

    def test_learned_module_no_source_import(self):
        tree=ast.parse((ROOT/"nativeevidence/f124ax_sparse_quadratic.py").read_text())
        modules=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                modules.extend(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):
                modules.append(node.module or "")
        self.assertFalse(any("f124ax_train_source" in m or
                             "f124ao_frozen_source" in m for m in modules))
        self.assertFalse(any("f124aw_original_first_dev_source" in m for m in modules))

    def test_frozen_fit_admission_is_strict(self):
        import f124ax_fit_screen_evidence as evidence
        sample={n:{"FP":0,"paired":0,"affine_paired":0,"feistel_paired":0,
                   "sum_cpu_ns":0} for n in evidence.NAMES}
        sample["AV_LOCKED_ACTIVE48"].update(paired=10,affine_paired=10)
        sample["AFFINE_RANDOM48"].update(paired=11,affine_paired=11)
        sample["SPARSE_QUADRATIC_ACTIVE48"].update(
            paired=11,affine_paired=10,feistel_paired=1)
        self.assertIsNone(evidence.admissible(sample))  # No total superiority.
        sample["SPARSE_QUADRATIC_ACTIVE48"].update(
            paired=12,affine_paired=11,feistel_paired=1,FP=1)
        self.assertIsNone(evidence.admissible(sample))  # Any FP rejects.
        sample["SPARSE_QUADRATIC_ACTIVE48"]["FP"]=0
        self.assertEqual(evidence.admissible(sample),
                         "SPARSE_QUADRATIC_ACTIVE48")

if __name__=="__main__":
    unittest.main()

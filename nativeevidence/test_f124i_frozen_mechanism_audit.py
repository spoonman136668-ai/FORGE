"""F124-I exact original TRAIN ablations, causal reference and resource guards."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))

import f124i_frozen_mechanism_audit as audit
import f124h_source as graph
import f124h_signed_evidence as learner
import f124h_train_receipt as receipt

class FrozenF124IQualification(unittest.TestCase):
    def pair(self):
        return graph.build(180000,[1,1,2],"Wingless","TRAIN")

    def test_frozen_source_and_original_weight_provenance(self):
        audit.prove_source()
        self.assertEqual(audit.F124H_HEAD,"409f9129442f3d47b3d9bc032342f48042f3127a")
        self.assertEqual(audit.F124H_TRAIN_SHA,
            "3ce0356ad9c19aeb4557ffe0b138908707c65ab3ce4b6af952adbf9899988254")
        self.assertEqual(audit.F123_TRAIN_SHA,
            "12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d")
        for lane in graph.TRAIN:
            self.assertFalse(set(graph.TRAIN[lane]) & set(graph.RESERVED_CONFIRM[lane]))

    def test_unique_public_causal_join_deletion_and_decoy(self):
        pos,neg=self.pair()
        self.assertEqual(graph.public_routes(pos),1)
        self.assertEqual(graph.public_routes(neg),0)
        self.assertEqual(len(audit.public_causal_path(pos)),len(pos["roles"]))
        with self.assertRaises(graph.Invalid):
            audit.public_causal_path(neg)
        for arm in ("A","B"):
            frozen=learner.initial(arm)
            preserved=list(frozen)
            result=audit.causal_and_distractor(pos,frozen,arm)
            self.assertTrue(result["causal_deleted_truth"]==0)
            self.assertTrue(result["distractor_deleted_truth"]==1)
            self.assertEqual(preserved,frozen)
            self.assertIsInstance(result["true_edge_drop"],float)

    def test_label_blind_topology_roles_and_token_inventory(self):
        for lane in graph.TRAIN:
            for seed in graph.TRAIN[lane]:
                pos,neg=graph.build(seed,[1,1,2],lane)
                self.assertEqual(audit.inventory(pos),audit.inventory(neg))
                self.assertTrue(graph.paired_admit(pos,neg))
                self.assertEqual(pos["roles"],neg["roles"])
                self.assertEqual(len(pos["edges"]),len(neg["edges"]))

    def test_original_work_cost_is_observed_not_declared_equal(self):
        pos,neg=self.pair()
        for arm in ("A","B"):
            fixed=learner.initial(arm)
            y,_,_,cost=learner.forward(pos,fixed,arm)
            work=dict.fromkeys(audit.COSTS,0)
            work.update(peak_key_records=0,peak_messages=0,evicted_records=0)
            audit.add_counts(work,cost)
            self.assertGreater(work["raw_bit_multiply_adds"],0)
            self.assertGreater(work["public_edge_scans"],0)
            self.assertGreater(work["peak_key_records"],0)
            self.assertLessEqual(work["peak_key_records"],128)
            self.assertLessEqual(work["peak_messages"],128)
            _,reference=receipt.fixed_comparator(pos)
            self.assertGreater(reference["bit_comparisons"],0)
            self.assertIsInstance(y,float)

    def test_edge_order_invariance_no_private_model_features(self):
        p,n=self.pair()
        for arm in ("A","B"):
            weights=learner.initial(arm)
            for g in (p,n):
                reverse=copy.deepcopy(g)
                reverse["edges"].reverse()
                self.assertAlmostEqual(learner.forward(g,weights,arm)[0],
                                       learner.forward(reverse,weights,arm)[0],places=12)
        with self.assertRaises(graph.Invalid):
            audit.public_causal_path(dict(p,selected_path=1))
        with self.assertRaises(graph.Invalid):
            graph.build(180100,[1,1,2],"Wingless","CONFIRM")

    def test_forged_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"forged.json"
            file.write_text("{}")
            with self.assertRaisesRegex(graph.Invalid,
                                        "IMMUTABLE_PARENT_WEIGHTS_DIGEST"):
                audit.read_frozen_parent(file)

if __name__=="__main__":
    unittest.main()

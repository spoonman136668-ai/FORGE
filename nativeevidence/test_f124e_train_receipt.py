"""F124-E TRAIN-only custody and independent comparator qualification."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124e_key_value_environment as src
import f124e_learned_associative_memory as model
import f124e_train_receipt as e

class ReceiptTests(unittest.TestCase):
    def test_frozen_model_and_generator_source_blobs(self):
        self.assertEqual(e.code_blob(src),e.GRAPH_BLOB)
        self.assertEqual(e.code_blob(model),e.MODEL_BLOB)
        self.assertTrue(model.contract())
        self.assertEqual(e.ORIGIN_SHA,
          "12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d")

    def test_public_fixed_comparator_separate_ceiling(self):
        pos,neg=src.build(140000,[1,1,2],"Wingless")
        pp,pwork=e.fixed_approx(pos)
        np,nwork=e.fixed_approx(neg)
        self.assertTrue(pp)
        self.assertFalse(np)
        self.assertGreater(pwork["edge_scans"],0)
        self.assertGreater(pwork["bit_comparisons"],0)
        self.assertGreater(nwork["bit_comparisons"],0)
        self.assertEqual(src.public_routes(pos),1)
        self.assertEqual(src.public_routes(neg),0)

    def test_frozen_train_controls_two_independent_lanes(self):
        for lane in src.TRAIN:
            controls=e.cohort_control(lane,[[1,1,2],[3,2,0]])
            self.assertEqual(controls["pairs"],48)
            self.assertEqual(controls["symbolic_ceiling_pairs"],48)
            self.assertEqual(controls["role_only_paired_correct"],0)
            self.assertTrue(0<=controls["paired_correct"]<=48)

    def test_identity_tampering_and_reserved_reads_fail_closed(self):
        with self.assertRaises(src.Invalid):
            e.evidence(".", "not-a-valid-source", 1)
        with self.assertRaises(src.Invalid):
            src.build(140100,[1,1,2],"Wingless","CONFIRM")
        with self.assertRaises(src.Invalid):
            src.build(150100,[1,1,2],"Yggdrasil","TRAIN")
        pos,_=src.build(140000,[1,1,2],"Wingless")
        forged=dict(pos,oracle_label=1)
        with self.assertRaises(src.Invalid):
            e.fixed_approx(forged)

if __name__=="__main__":
    unittest.main()

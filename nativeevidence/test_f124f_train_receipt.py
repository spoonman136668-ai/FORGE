"""F124-F source-pinned frozen training and fixed heuristic boundary tests."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124f_public_graph_source as source
import f124f_conditional_memory as learned
import f124f_train_receipt as receipt

class FrozenTRAINReceiptTests(unittest.TestCase):
    def test_exact_model_source_blob_contract(self):
        self.assertEqual(receipt.blob(source),receipt.SOURCE_BLOB)
        self.assertEqual(receipt.blob(learned),receipt.MODEL_BLOB)
        self.assertTrue(learned.contract())
        self.assertEqual(receipt.F123_SHA,
          "12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d")

    def test_public_raw_fixed_control_and_independent_ceiling(self):
        pos,neg=source.build(160000,[1,1,2],"Wingless")
        yes,a=receipt.fixed_hamming(pos)
        no,b=receipt.fixed_hamming(neg)
        self.assertTrue(yes)
        self.assertFalse(no)
        self.assertGreater(a["raw_bit_comparisons"],0)
        self.assertGreater(a["public_edge_scans"],0)
        self.assertGreater(b["raw_bit_comparisons"],0)
        self.assertEqual(source.public_routes(pos),1)
        self.assertEqual(source.public_routes(neg),0)

    def test_two_lanes_qualify_train_only_control(self):
        for lane in source.TRAIN:
            r=receipt.control_lane(lane,[[1,1,2],[3,2,0]])
            self.assertEqual(r["pairs"],48)
            self.assertTrue(0<=r["paired_correct"]<=48)
            self.assertEqual(r["exact_symbolic_ceiling_pairs"],48)

    def test_no_unverified_authority_or_holdout_access(self):
        with self.assertRaises(source.Invalid):
            receipt.evidence(".","fake",1)
        with self.assertRaises(source.Invalid):
            source.build(160100,[1,1,2],"Wingless","CONFIRM")
        p,_=source.build(160000,[1,1,2],"Wingless")
        with self.assertRaises(source.Invalid):
            receipt.fixed_hamming(dict(p,selected_path=1))
        self.assertEqual(receipt.canonical({"a":1}),b'{"a":1}\n')

if __name__=="__main__":
    unittest.main()

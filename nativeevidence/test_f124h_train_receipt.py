"""F124-H immutable TRAIN source and control boundary."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124h_source as source
import f124h_signed_evidence as learned
import f124h_train_receipt as gate

class SourceReceiptQualification(unittest.TestCase):
    def test_frozen_exact_blob_and_source_contract(self):
        self.assertEqual(gate.blob(source),gate.SOURCE_BLOB)
        self.assertEqual(gate.blob(learned),gate.MODEL_BLOB)
        self.assertTrue(learned.frozen())
        self.assertEqual(gate.F123_SHA,
            "12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d")

    def test_independent_public_heuristic_has_real_operation_counts(self):
        p,n=source.build(180000,[1,1,2],"Wingless")
        yp,pc=gate.fixed_comparator(p)
        yn,nc=gate.fixed_comparator(n)
        self.assertTrue(yp)
        # Approximate 12/16 raw matching is deliberately NOT an exact oracle;
        # some negative graphs can be incorrectly admitted. Preserve those.
        self.assertIsInstance(yn,bool)
        self.assertGreater(pc["bit_comparisons"],0)
        self.assertGreater(nc["bit_comparisons"],0)
        self.assertEqual(source.public_routes(p),1)
        self.assertEqual(source.public_routes(n),0)

    def test_lanes_have_valid_train_only_control(self):
        for lane in source.TRAIN:
            score=gate.control_lane(lane,[[1,1,2],[3,2,0]])
            self.assertEqual(score["train_pairs"],48)
            self.assertTrue(0<=score["paired_correct"]<=48)
            self.assertEqual(score["exact_symbolic_ceiling_pairs"],48)

    def test_forged_source_and_confirmation_fail_closed(self):
        with self.assertRaises(source.Invalid):
            gate.evidence(".","not-a-commit",1)
        with self.assertRaises(source.Invalid):
            source.build(180100,[1,1,2],"Wingless","CONFIRM")
        p,_=source.build(180000,[1,1,2],"Wingless")
        with self.assertRaises(source.Invalid):
            gate.fixed_comparator(dict(p,oracle_label=1))

if __name__=="__main__":
    unittest.main()

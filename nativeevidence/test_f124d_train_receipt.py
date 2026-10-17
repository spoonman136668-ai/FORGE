"""F124-D frozen two-lane TRAIN receipt control, no reserved confirm access."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124d_reconvergent_source as source
import f124d_train_receipt as gate
import f124d_competitive_states as network

class FrozenTrainingControl(unittest.TestCase):
    def pair(self):
        return source.build(120000,[1,1,2],"Wingless","TRAIN")

    def test_contract_binds_parent_and_new_sources(self):
        self.assertEqual(source.git_blob(Path(source.__file__).read_bytes().replace(
            b"\r\n",b"\n")),gate.GRAPH_BLOB)
        self.assertEqual(source.git_blob(Path(network.__file__).read_bytes().replace(
            b"\r\n",b"\n")),gate.MODEL_BLOB)
        self.assertTrue(network.contract())
        self.assertEqual(gate.F123_TRAIN_SHA,
             "12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d")

    def test_nonlearned_public_comparator_is_not_exact_oracle_feature(self):
        pos,neg=self.pair()
        yes,cost=gate.fixed_control(pos)
        no,ncost=gate.fixed_control(neg)
        self.assertTrue(yes)
        self.assertFalse(no)
        self.assertGreater(cost["public_edge_scans"],0)
        self.assertGreater(cost["raw_bit_comparisons"],0)
        self.assertGreater(ncost["raw_bit_comparisons"],0)
        self.assertEqual(source.routes(pos),1)
        self.assertEqual(source.routes(neg),0)

    def test_controls_each_lane_training_cohort_only(self):
        vectors=[[1,1,2],[3,2,0]]
        for lane in source.TRAIN:
            out=gate.comparator_cohort(lane,vectors)
            self.assertEqual(out["pairs"],48)
            self.assertEqual(out["exact_symbolic_ceiling_pairs"],48)
            self.assertEqual(out["role_only_pairs_correct"],0)
            self.assertGreaterEqual(out["paired_correct"],0)
            self.assertLessEqual(out["paired_correct"],48)

    def test_model_cannot_generate_reserved_confirm(self):
        with self.assertRaises(source.Invalid):
            source.build(120100,[1,1,2],"Wingless","CONFIRM")
        with self.assertRaises(source.Invalid):
            source.build(130100,[1,1,2],"Yggdrasil","TRAIN")
        pos,_=self.pair()
        altered=dict(pos,oracle=True)
        with self.assertRaises(source.Invalid):
            gate.fixed_control(altered)

    def test_source_identity_guard_and_exact_canonical_bytes(self):
        with self.assertRaises(source.Invalid):
            gate.evidence(".", "not-a-git-sha", 12)
        sample={"a":[1,2],"b":"z"}
        self.assertEqual(gate.canonical(sample),b'{"a":[1,2],"b":"z"}\n')

if __name__=="__main__":
    unittest.main()

"""F124-F freeze and TRAIN-only raw associative key-value source qualification."""
import copy
from collections import Counter
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124f_public_graph_source as f

VECTORS=([1,1,2],[3,2,0])

class F124FKeyValueAdmission(unittest.TestCase):
    def test_original_preimplementation_freeze_and_reserved_exclusion(self):
        self.assertEqual(f.FREEZE_BLOB,"256e5a1c1a9dd1a31372e6abc0d20f6a42f89214")
        self.assertEqual(len(f.frozen()),64)
        for lane in f.TRAIN:
            self.assertEqual(len(f.TRAIN[lane]),24)
            self.assertEqual(len(f.RESERVED_CONFIRM[lane]),48)
            self.assertFalse(set(f.TRAIN[lane]) & set(f.RESERVED_CONFIRM[lane]))
        self.assertEqual(len(f.STRATA),5)

    def test_all_48_train_pairs_per_lane_for_two_distinct_vectors(self):
        for lane in f.TRAIN:
            for seed in f.TRAIN[lane]:
                for v in VECTORS:
                    with self.subTest(lane=lane,seed=seed,vector=v):
                        pos,neg=f.build(seed,list(v),lane,"TRAIN")
                        self.assertTrue(f.paired_admit(pos,neg))
                        self.assertEqual(f.public_routes(pos),1)
                        self.assertEqual(f.public_routes(neg),0)
                        self.assertGreaterEqual(f.public_routes(pos,True),5)
                        self.assertEqual(len(pos["roles"]),4+(seed%2))
                        self.assertEqual(set(pos),f.GRAPH_KEYS)
                        self.assertEqual(set(pos["edges"][0]),f.EDGE_KEYS)

    def test_edge_order_and_independent_source_identity(self):
        pos,neg=f.build(160000,[1,1,2],"Wingless")
        self.assertEqual((pos,neg),f.build(160000,[1,1,2],"Wingless"))
        for graph,truth in ((pos,1),(neg,0)):
            other=copy.deepcopy(graph)
            other["edges"].reverse()
            self.assertEqual(f.public_routes(other),truth)
        another,_=f.build(160000,[3,2,0],"Wingless")
        self.assertNotEqual(pos["start"],another["start"])

    def test_matched_label_blind_role_topology_token_histogram(self):
        for lane in f.TRAIN:
            for seed in f.TRAIN[lane]:
                pos,neg=f.build(seed,[3,2,0],lane)
                self.assertEqual(pos["start"],neg["start"])
                self.assertEqual(pos["target"],neg["target"])
                self.assertEqual(pos["roles"],neg["roles"])
                def inventory(x):
                    return Counter((e["from"],e["to"],e["role"]) for e in x["edges"]),Counter(
                        tuple(e[k]) for e in x["edges"] for k in ("src_bits","dst_bits"))
                self.assertEqual(inventory(pos),inventory(neg))
                self.assertEqual(f.public_routes(pos,True),f.public_routes(neg,True))

    def test_source_authentication_and_no_private_fields(self):
        for lane,seed,phase in (("Wingless",160100,"TRAIN"),
                                ("Wingless",160000,"CONFIRM"),
                                ("Yggdrasil",170100,"CONFIRM"),
                                ("Wingless",160024,"TRAIN")):
            with self.subTest(lane=lane,seed=seed,phase=phase):
                with self.assertRaises(f.Invalid):
                    f.build(seed,[1,1,2],lane,phase)
        pos,_=f.build(160000,[1,1,2],"Wingless")
        for field in ("truth","oracle","correct_path","pair_label","key_equal"):
            changed=copy.deepcopy(pos)
            changed[field]=1
            with self.assertRaises(f.Invalid):
                f.validate(changed)
        bad=copy.deepcopy(pos)
        bad["edges"][0]["src_bits"]=[True]*16
        with self.assertRaises(f.Invalid):
            f.validate(bad)
        with self.assertRaises(f.Invalid):
            f.paired_admit(pos,pos)

if __name__=="__main__":
    unittest.main()

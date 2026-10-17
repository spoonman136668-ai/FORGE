"""F124-C preregistered TRAIN-only adversarial graph admission tests."""
from collections import Counter
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124c_reconvergent_graph as m

class CausalCompositionSourceAdmission(unittest.TestCase):
    def test_frozen_before_implementation_and_reserved_split(self):
        self.assertEqual(len(m.frozen()),64)
        self.assertEqual(m.FREEZE_BLOB,"18d1c037d74224905a59c72f7e9fa2fcdbe73505")
        self.assertEqual(set(m.TRAIN),set(m.RESERVED_CONFIRM))
        for lane in m.TRAIN:
            self.assertTrue(set(m.TRAIN[lane]).isdisjoint(m.RESERVED_CONFIRM[lane]))

    def test_all_registered_training_pairs_and_vectors(self):
        for lane in m.TRAIN:
            for seed in m.TRAIN[lane]:
                for vector in ([1,1,2],[3,2,0]):
                    with self.subTest(lane=lane,seed=seed,v=vector):
                        p,n=m.build(seed,vector,lane)
                        self.assertTrue(m.pair_parity(p,n))
                        self.assertEqual(m.oracle(p),1)
                        self.assertEqual(m.oracle(n),0)
                        self.assertEqual(len(p["roles"]),3+(seed%2))
                        self.assertGreaterEqual(m.oracle(n,True),3)
                        self.assertEqual(set(p),m.FIELDS)
                        self.assertEqual(set(p["edges"][0]),m.EDGE_FIELDS)

    def test_deterministic_and_label_blind_edge_reordering(self):
        pos,neg=m.build(100000,[1,1,2],"Wingless")
        self.assertEqual((pos,neg),m.build(100000,[1,1,2],"Wingless"))
        for original,count in ((pos,1),(neg,0)):
            reverse=copy.deepcopy(original)
            reverse["edges"].reverse()
            self.assertEqual(m.oracle(reverse),count)
            self.assertEqual(m.oracle(reverse,True),m.oracle(original,True))

    def test_source_and_raw_feature_borders_fail_closed(self):
        for lane,seed,phase in (("Wingless",100100,"CONFIRM"),
                                ("Yggdrasil",110100,"TRAIN"),
                                ("Wingless",100024,"TRAIN")):
            with self.subTest(lane=lane,seed=seed):
                with self.assertRaises(m.Quarantined):
                    m.build(seed,[1,1,2],lane,phase)
        pos,neg=m.build(100001,[1,1,2],"Wingless")
        for marker in ("truth","changed_junction","selected_path","seed","equality"):
            copy_g=copy.deepcopy(pos)
            copy_g[marker]=1
            with self.subTest(marker=marker),self.assertRaises(m.Quarantined):
                m.validate(copy_g)
        changed=copy.deepcopy(pos)
        changed["edges"][0]["src_bits"]=[True]*16
        with self.assertRaises(m.Quarantined):m.validate(changed)
        with self.assertRaises(m.Quarantined):m.pair_parity(pos,pos)

    def test_pair_token_marginals_preserved_under_negative_intervention(self):
        p,n=m.build(110001,[3,2,0],"Yggdrasil")
        digest=lambda g: Counter(tuple(e[k]) for e in g["edges"]
                                 for k in ("src_bits","dst_bits"))
        self.assertEqual(digest(p),digest(n))
        role_counts=lambda g: Counter(e["role"] for e in g["edges"])
        self.assertEqual(role_counts(p),role_counts(n))

if __name__=="__main__":
    unittest.main()

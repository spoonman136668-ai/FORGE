"""F124-D preregistered source admission: TRAIN ONLY; no CONFIRM read."""
import copy
from collections import Counter
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124d_reconvergent_source as f

VECTORS=([1,1,2],[3,2,0])

class F124DAdmissibility(unittest.TestCase):
    def test_preimplementation_blob_and_seeds_reserved(self):
        self.assertEqual(len(f.frozen()),64)
        self.assertEqual(f.FREEZE_BLOB,"83dd63eb42e41c5583570d055b806b24f4ece5a6")
        for lane in f.TRAIN:
            self.assertEqual(len(f.TRAIN[lane]),24)
            self.assertEqual(len(f.RESERVED_CONFIRM[lane]),48)
            self.assertFalse(set(f.TRAIN[lane]) & set(f.RESERVED_CONFIRM[lane]))
        self.assertEqual(set(f.STRATA),{"early_rejoin","late_rejoin",
                         "alias_swap","near_collision","parallel_multiedge"})

    def test_all_frozen_train_candidates_both_lanes(self):
        for lane in f.TRAIN:
            for seed in f.TRAIN[lane]:
                for v in VECTORS:
                    with self.subTest(lane=lane,seed=seed,v=v):
                        positive,negative=f.build(seed,list(v),lane,"TRAIN")
                        self.assertTrue(f.parity(positive,negative))
                        self.assertEqual(f.routes(positive),1)
                        self.assertEqual(f.routes(negative),0)
                        self.assertGreaterEqual(f.routes(positive,True),6)
                        self.assertEqual(len(positive["roles"]),4+(seed%2))
                        self.assertEqual(set(positive),f.GRAPH_FIELDS)
                        self.assertEqual(set(negative["edges"][0]),f.EDGE_FIELDS)

    def test_reproducible_graphs_unordered_and_no_edge_marker(self):
        positive,negative=f.build(120000,list(VECTORS[0]),"Wingless")
        self.assertEqual((positive,negative),
                         f.build(120000,list(VECTORS[0]),"Wingless"))
        for o,expected in ((positive,1),(negative,0)):
            backwards=copy.deepcopy(o);backwards["edges"].reverse()
            self.assertEqual(f.routes(backwards),expected)
            self.assertEqual(f.routes(backwards,True),f.routes(o,True))
        self.assertEqual(len({tuple(e["src_bits"]) for e in positive["edges"]}) > 5,True)

    def test_no_privileged_signals_or_reserved_source_admission(self):
        for seed,lane,phase in ((120100,"Wingless","CONFIRM"),
                                (130100,"Yggdrasil","TRAIN"),
                                (120024,"Wingless","TRAIN"),
                                (120000,"Wingless","CONFIRM")):
            with self.subTest(seed=seed,lane=lane,phase=phase):
                with self.assertRaises(f.Invalid):
                    f.build(seed,list(VECTORS[0]),lane,phase)
        positive,negative=f.build(120002,list(VECTORS[1]),"Wingless")
        for marker in ("truth","selected_path","changed_junction",
                       "source_seed","candidate_vector","exact_equality"):
            corrupted=copy.deepcopy(positive)
            corrupted[marker]=1
            with self.subTest(marker=marker),self.assertRaises(f.Invalid):
                f.validate(corrupted)
        altered=copy.deepcopy(positive)
        altered["edges"][0]["dst_bits"]=[True]*16
        with self.assertRaises(f.Invalid):
            f.validate(altered)
        with self.assertRaises(f.Invalid):
            f.parity(positive,positive)

    def test_topology_token_role_depth_histograms_do_not_disclose_label(self):
        for lane in f.TRAIN:
            for seed in f.TRAIN[lane]:
                positive,negative=f.build(seed,list(VECTORS[0]),lane,"TRAIN")
                def inventory(g):
                    return Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),Counter(
                        tuple(e[k]) for e in g["edges"] for k in ("src_bits","dst_bits"))
                self.assertEqual(inventory(positive),inventory(negative))
                self.assertEqual(positive["roles"],negative["roles"])
                self.assertEqual(f.routes(positive,True),f.routes(negative,True))
                self.assertEqual(len(positive["edges"]),len(negative["edges"]))

if __name__=="__main__":
    unittest.main()

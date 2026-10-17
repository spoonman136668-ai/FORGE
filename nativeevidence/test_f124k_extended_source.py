"""F124-K independent long-horizon fixture admission without original first-use."""
import copy
from collections import Counter
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f124h_source as original
import f124k_extended_source as f

VECTORS=([1,1,2],[3,2,0])

class F124KSealedFixtureQualification(unittest.TestCase):
    def test_frozen_identities_and_protected_source_fail_closed(self):
        self.assertEqual(f.PROTOCOL_BLOB,"8065de6263f45cea465ec0bda622d985c5488ef8")
        self.assertEqual(len(f.frozen()),64)
        self.assertEqual(f.AUTHORITY_STATUS,
                         "BLOCKED_PENDING_INDEPENDENT_FIRST_USE_AND_MODEL_INTERFACE")
        for lane in ("Wingless","Yggdrasil"):
            self.assertEqual(len(f.FIXTURES[lane]),24)
            self.assertEqual(len(f.RESERVED[lane]),48)
            self.assertFalse(set(f.FIXTURES[lane]) & set(f.RESERVED[lane]))
        with self.assertRaisesRegex(f.Invalid,"FIRST_USE_BLOCKED"):
            f.build_protected()
        pre=f.first_use_preflight()
        self.assertTrue(pre["source_fixture_ready"])
        self.assertFalse(pre["independent_first_use_receipt_verified"])
        self.assertEqual(pre["reserved_examples_built"],0)
        self.assertFalse(pre["original_f124h_model_accepts_7_to_9_hops"])

    def test_fixture_cohorts_all_pairs_disjoint_long_depths(self):
        for lane in f.FIXTURES:
            counts={7:0,8:0,9:0}
            for seed in f.FIXTURES[lane]:
                for vector in VECTORS:
                    with self.subTest(lane=lane,seed=seed,vector=vector):
                        p,n=f.build_fixture(seed,list(vector),lane)
                        self.assertTrue(f.paired_admit(p,n))
                        self.assertEqual(f.symbolic_routes(p),1)
                        self.assertEqual(f.symbolic_routes(n),0)
                        self.assertGreaterEqual(f.symbolic_routes(p,role_only=True),5)
                        self.assertIn(len(p["roles"]),(7,8,9))
                        counts[len(p["roles"])]+=1
                        self.assertEqual(set(p),f.GRAPH_KEYS)
                        self.assertEqual(set(p["edges"][0]),f.EDGE_KEYS)
            self.assertEqual(counts,{7:16,8:16,9:16})

    def test_label_blind_role_topology_and_raw_histogram_exact(self):
        for lane in f.FIXTURES:
            for seed in f.FIXTURES[lane]:
                p,n=f.build_fixture(seed,[1,1,2],lane)
                self.assertEqual((p["start"],p["target"],p["roles"]),
                                 (n["start"],n["target"],n["roles"]))
                def inventory(g):
                    return (Counter((e["from"],e["to"],e["role"]) for e in g["edges"]),
                            Counter(tuple(e[x]) for e in g["edges"]
                                    for x in ("src_bits","dst_bits")))
                self.assertEqual(inventory(p),inventory(n))
                self.assertEqual(f.symbolic_routes(p,True),
                                 f.symbolic_routes(n,True))

    def test_replay_reorder_and_candidate_source_separation(self):
        p,n=f.build_fixture(280000,[1,1,2],"Wingless")
        self.assertEqual((p,n),f.build_fixture(280000,[1,1,2],"Wingless"))
        changed,_=f.build_fixture(280000,[3,2,0],"Wingless")
        self.assertNotEqual(p["start"],changed["start"])
        for g,count in ((p,1),(n,0)):
            reversed_graph=copy.deepcopy(g)
            reversed_graph["edges"].reverse()
            self.assertEqual(f.symbolic_routes(reversed_graph),count)
            self.assertEqual(f.symbolic_routes(g,True),
                             f.symbolic_routes(reversed_graph,True))

    def test_reject_privileged_input_invalid_bits_and_reserved_phase(self):
        p,n=f.build_fixture(280000,[1,1,2],"Wingless")
        for secret in ("truth","oracle","path_id","correct_path","source_seed","key_equal"):
            tampered=copy.deepcopy(p);tampered[secret]=1
            with self.subTest(secret=secret),self.assertRaises(f.Invalid):
                f.validate_public(tampered)
        altered=copy.deepcopy(p);altered["edges"][0]["src_bits"]=[True]*16
        with self.assertRaises(f.Invalid):f.validate_public(altered)
        with self.assertRaises(f.Invalid):f.paired_admit(p,p)
        with self.assertRaises(f.Invalid):
            f.build_fixture(280000,[1,1,2],"Wingless","PROTECTED_CONFIRM")
        with self.assertRaises(f.Invalid):
            f.build_fixture(280024,[1,1,2],"Wingless")
        with self.assertRaises(f.Invalid):
            f.build_fixture(280000,[4,1,2],"Wingless")
        with self.assertRaises(f.Invalid):
            f.build_fixture(280000,[True,1,2],"Wingless")

    def test_original_f124h_model_input_validator_rejects_fixture_depths(self):
        p,_=f.build_fixture(280000,[1,1,2],"Wingless")
        self.assertEqual(len(p["roles"]),8)
        with self.assertRaises(original.Invalid):
            original.validate(p)
        self.assertEqual(f.first_use_preflight()["protection"],
                         "BLOCKED_PENDING_INDEPENDENT_FIRST_USE_AND_MODEL_INTERFACE")

if __name__=="__main__":
    unittest.main()

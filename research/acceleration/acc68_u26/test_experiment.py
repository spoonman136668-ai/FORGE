"""ACC-68 U26 frozen tree geometry, finite capacity and retrieval checks."""
import importlib.util
from pathlib import Path
import math
import unittest

spec=importlib.util.spec_from_file_location("acc68_u26",Path(__file__).with_name("experiment.py"))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class U26Test(unittest.TestCase):
    def test_01_source_registry(self):
        self.assertEqual(m.source_custody()["registry_blob"],m.REGISTRY_BLOB)
    def test_02_prospective_prereg(self):
        self.assertEqual(m.source_custody()["prereg_commit"],"dc6119e0c80de7485014383014838ec20287bc1f")
    def test_03_geometry_only_scope(self):
        self.assertIn("SYNTHETIC_TREE",m.source_custody()["research_scope"])
    def test_04_frozen_scales(self):
        self.assertEqual(m.DEPTHS,(4,6,8))
        self.assertEqual(m.SEEDS,(26011,26013,26017))
        self.assertEqual(m.RADIAL_ALPHA,.24)
    def test_05_tree_sizes(self):
        for depth in m.DEPTHS:
            tree=m.nodes(depth,26011)
            self.assertEqual(len(tree),(1<<(depth+1))-1)
    def test_06_tree_parent_exact(self):
        for depth in m.DEPTHS:
            tree=m.nodes(depth,26011)
            names={x["path"] for x in tree}
            self.assertEqual(sum(x["parent"] is None for x in tree),1)
            self.assertTrue(all(x["parent"] in names for x in tree if x["parent"] is not None))
    def test_07_seed_label_distinction(self):
        self.assertNotEqual(m.label(26011,"101"),m.label(26013,"101"))
        self.assertEqual(m.label(26011,"101"),m.label(26011,"101"))
    def test_08_coordinate_open_disk(self):
        for depth in m.DEPTHS:
            tree=m.nodes(depth,26011)
            self.assertTrue(all(x["x"]**2+x["y"]**2<1 for x in tree))
    def test_09_identical_root_coordinate(self):
        for depth in m.DEPTHS:
            self.assertEqual(m.coord("",depth),(0.0,0.0))
    def test_10_radius_tanh_frozen(self):
        for depth in m.DEPTHS:
            self.assertAlmostEqual(math.hypot(*m.coord("1",depth)),math.tanh(.24),places=12)
    def test_11_bad_coordinate_path_rejected(self):
        with self.assertRaises(ValueError):m.coord("10102",8)
        with self.assertRaises(ValueError):m.coord("01",5)
    def test_12_bad_tree_identity_rejected(self):
        with self.assertRaises(ValueError):m.nodes(5,26011)
        with self.assertRaises(ValueError):m.nodes(4,123)
    def test_13_splits_disjoint_complete(self):
        for depth in m.DEPTHS:
            tree=m.nodes(depth,26011)
            groups={name:{x["path"] for x in tree if x["fold"]==name}
                    for name in ("fit","dev","check")}
            self.assertFalse(groups["fit"]&groups["dev"])
            self.assertFalse(groups["fit"]&groups["check"])
            self.assertFalse(groups["dev"]&groups["check"])
            self.assertEqual(set.union(*groups.values()),{x["path"] for x in tree})
    def test_14_splits_reproducible(self):
        for seed in m.SEEDS:
            self.assertEqual(m.split(seed,"101001"),m.split(seed,"101001"))
    def test_15_euclidean_symmetric_and_zero(self):
        x=(.1,.2);y=(-.3,.4)
        self.assertEqual(m.euclidean(x,x),0.0)
        self.assertAlmostEqual(m.euclidean(x,y),m.euclidean(y,x),places=14)
    def test_16_hyperbolic_symmetric_and_zero(self):
        x=(.1,.2);y=(-.3,.4)
        self.assertEqual(m.hyperbolic(x,x),0.0)
        self.assertAlmostEqual(m.hyperbolic(x,y),m.hyperbolic(y,x),places=14)
    def test_17_hyperbolic_boundary_rejected(self):
        with self.assertRaises(ValueError):m.hyperbolic((1,0),(0,0))
    def test_18_geometric_triangle_inequality_sample(self):
        pts=[(0,0),(.2,.3),(-.3,.4)]
        for dist in (m.hyperbolic,m.euclidean):
            self.assertLessEqual(dist(pts[0],pts[2]),dist(pts[0],pts[1])+dist(pts[1],pts[2])+1e-12)
    def test_19_nearest_excludes_self(self):
        tree=m.nodes(4,26011)
        self.assertNotEqual(m.nearest(tree[-1],tree,m.euclidean),tree[-1]["path"])
    def test_20_exact_parent_index_reference(self):
        for depth in m.DEPTHS:
            tree=m.nodes(depth,26011)
            index={x["path"]:x for x in tree}
            for x in tree:
                if x["parent"] is not None:
                    self.assertEqual(index[x["parent"]]["depth"],x["depth"]-1)
    def test_21_no_impossible_infinite_identifier_capacity(self):
        p=m.finite_witness()
        self.assertEqual(p["coordinate_bit_pattern_capacity_upper_bound"],"2^128")
        self.assertFalse(p["distinguishes_all_unbounded_ids"])
    def test_22_quantization_bounded(self):
        for v in (-.999,0,.999):
            self.assertLessEqual(abs(m.quantize(v)),32767)
        with self.assertRaises(ValueError):m.quantize(1.0)
    def test_23_coordinate_storage_exact_bytes(self):
        x=m.tree_report(4,26011)
        self.assertEqual(x["coord_payload_bytes"],16*x["nodes"])
        self.assertGreater(x["exact_parent_index_payload_json_bytes"],0)
    def test_24_full_tree_query_no_self_or_parent_omission(self):
        x=m.tree_report(4,26013)
        self.assertEqual(x["exact_parent_reference_correct"],x["checks"])
        self.assertEqual(len(x["euclidean"]["errors"])+x["euclidean"]["correct"],x["checks"])
        self.assertEqual(len(x["hyperbolic"]["errors"])+x["hyperbolic"]["correct"],x["checks"])
    def test_25_metric_errors_and_accuracy_bounded(self):
        x=m.tree_report(4,26017)
        for name in ("euclidean","hyperbolic"):
            self.assertGreater(x[name]["scan_ns"],0)
            self.assertGreaterEqual(x[name]["accuracy"],0)
            self.assertLessEqual(x[name]["accuracy"],1)
    def test_26_label_source_not_gold_in_geometric_search(self):
        tree=m.nodes(4,26011)
        renamed=[{**n,"label":"renamed"+str(i)} for i,n in enumerate(tree)]
        self.assertEqual(m.nearest(tree[-2],tree,m.hyperbolic),
                         m.nearest(renamed[-2],renamed,m.hyperbolic))
    def test_27_reproducible_whole_tree_identity(self):
        a=m.nodes(6,26011)
        self.assertEqual(a,m.nodes(6,26011))
    def test_28_nine_tree_matrix(self):
        self.assertEqual(len(m.DEPTHS)*len(m.SEEDS),9)
    def test_29_same_coordinates_both_metrics(self):
        a=m.nodes(4,26011)
        self.assertEqual(m.coord(a[4]["path"],4),(a[4]["x"],a[4]["y"]))
    def test_31_canonical_tie_break_independent_of_candidate_order(self):
        # Exact geometric symmetry across ±x, and the same query's gold
        # parent is not consulted when ranking.
        q={"path":"query","x":0.0,"y":0.0}
        a={"path":"a","x":-.25,"y":0.0}
        z={"path":"z","x":.25,"y":0.0}
        for metric in (m.euclidean,m.hyperbolic):
            self.assertEqual(m.nearest(q,[z,a],metric),"a")
            self.assertEqual(m.nearest(q,[a,z],metric),"a")
    def test_32_near_tie_libm_tolerance_does_not_use_gold(self):
        q={"path":"query","x":0.0,"y":0.0}
        a={"path":"a","x":-.25,"y":0.0}
        z={"path":"z","x":.25000000000000006,"y":0.0}
        for metric in (m.euclidean,m.hyperbolic):
            self.assertEqual(m.nearest(q,[z,a],metric),"a")
            self.assertEqual(m.nearest(q,[a,z],metric),"a")
    def test_30_readonly_model_scope(self):
        self.assertEqual(m.source_custody()["research_scope"],"SYNTHETIC_TREE_COORDINATE_RETRIEVAL_ONLY")

if __name__=="__main__":unittest.main()

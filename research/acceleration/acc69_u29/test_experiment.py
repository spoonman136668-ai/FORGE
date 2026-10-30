import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("u29",Path(__file__).with_name("experiment.py"))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class U29Tests(unittest.TestCase):
    def test_01_source(self):self.assertEqual(m.custody()["registry_blob"],m.BLOB)
    def test_02_frozen(self):self.assertEqual(m.custody()["prereg_commit"],m.PRE_SHA)
    def test_03_sizes(self):self.assertEqual(m.SIZES,(4,6,8))
    def test_04_ring_edges(self):
        for n in m.SIZES:self.assertEqual(len(m.edges(n)),n)
    def test_05_bad_graph(self):
        with self.assertRaises(ValueError):m.edges(5)
    def test_06_bad_assignment(self):
        with self.assertRaises(ValueError):m.labels(4,99)
    def test_07_repeatability(self):self.assertEqual(m.labels(8,9),m.labels(8,9))
    def test_08_assignment_diversity(self):self.assertNotEqual(m.labels(8,0),m.labels(8,1))
    def test_09_majority_ties_zero(self):self.assertEqual(m.majority([0,1]),0)
    def test_10_majority_positive(self):self.assertEqual(m.majority([1,1,0]),1)
    def test_11_majority_bad_empty(self):
        with self.assertRaises(ValueError):m.majority([])
    def test_12_matrix(self):self.assertEqual(len(m.study()["cases"]),48)
    def test_13_source_integrity(self):self.assertEqual(m.study()["identity"]["claim"],"U29")
    def test_14_contradictions_exist(self):self.assertGreater(len(m.study()["contradictions"]),0)
    def test_15_full_edge_coverage(self):self.assertEqual(m.study()["aggregate"]["tested_edges"],(4+6+8)*16)
    def test_16_accuracy_bounded(self):
        x=m.study()["aggregate"]
        self.assertTrue(0<=x["topology_only_accuracy"]<=1)
        self.assertTrue(0<=x["per_edge_control_accuracy"]<=1)
    def test_17_nll_positive(self):self.assertGreater(m.study()["aggregate"]["topology_only_mean_nll"],0)
    def test_18_no_promotion(self):self.assertEqual(m.study()["classification"]["scientific_acceptance"],"NOT_GRANTED")
    def test_19_no_model_claim(self):self.assertEqual(m.study()["classification"]["pretrained_LLM_speed"],"UNVERIFIED")
    def test_20_heldout_assignment_count(self):
        q=m.study()["cases"]
        for n in m.SIZES:self.assertEqual({x["withheld_assignment"] for x in q if x["n"]==n},set(range(16)))
if __name__=="__main__":unittest.main()

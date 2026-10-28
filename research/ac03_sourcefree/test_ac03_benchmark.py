import unittest
import ac03_benchmark as m
class AC03SourceFree(unittest.TestCase):
    def test_all_six_native_candidate_families(self):
        covered={key for ids in m.IDS.values() for key in ids}
        self.assertTrue({'AC-D%d'%n for n in range(1,7)}<=covered)
    def test_all_sampled_exact_mechanisms_have_parity(self):
        for case,(baseline,candidate) in m.CASES.items():
            if case=='sketch':continue
            with self.subTest(case=case):
                self.assertEqual(m.exercise(case,baseline),m.exercise(case,candidate))
    def test_count_min_sketch_never_undercounts_source_visible_stream(self):
        truth=m.sketch('exact');approx=m.sketch('cms')
        self.assertEqual(len(truth),len(approx))
        self.assertTrue(all(b>=a for a,b in zip(truth,approx)))
        self.assertGreater(sum(a!=b for a,b in zip(truth,approx)),0)
    def test_unlearned_dependency_caveat(self):
        # A known graph in the benchmark does not demonstrate learning.
        self.assertEqual(m.delta('full'),m.delta('delta'))
    def test_results_schema(self):
        self.assertEqual(m.REPEATS,3)
        self.assertEqual(len(m.CASES),11)
        self.assertTrue(all(len(v)==2 for v in m.CASES.values()))
if __name__=='__main__':unittest.main()

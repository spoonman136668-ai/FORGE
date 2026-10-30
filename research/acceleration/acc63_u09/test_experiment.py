"""ACC-63 U09 FIT-only selection, CHECK isolation, and falsifiers."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).with_name("experiment.py")
spec=importlib.util.spec_from_file_location("acc63_u09",p)
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

class U09SourceBound(unittest.TestCase):
    def test_01_identity(self):
        self.assertEqual(a.source_identity()["original_registry_git_blob"],a.REGISTRY_BLOB)
    def test_02_frozen_prereg(self):
        self.assertEqual(a.source_identity()["prereg_commit"],"6e4e4cb2c6b25e29997e583d5954912eb8cde529")
    def test_03_fixed_seed_dictionary(self):
        self.assertEqual(a.DICTIONARY,tuple(range(32)))
        self.assertEqual(a.IN_SEEDS,(3,11,23))
        self.assertEqual(a.OUT_SEEDS,(37,41,43))
    def test_04_split_is_disjoint_and_complete(self):
        for n in a.SIDES:
            fit=set(a.fit_index(n));check=set(a.check_index(n))
            self.assertFalse(fit&check)
            self.assertEqual(fit|check,set(range(n*n)))
            self.assertGreaterEqual(len(check)/n**2,.15)
            self.assertLessEqual(len(check)/n**2,.25)
    def test_05_split_is_reproducible(self):
        for n in a.SIDES:
            self.assertEqual(a.check_index(n),a.check_index(n))
    def test_06_values_in_int8_small_range(self):
        for n in a.SIDES:
            for seed in (3,11,23,37,41,43):
                self.assertTrue(all(-8<=x<=7 for x in a.matrix(seed,n)))
    def test_07_seed_generator_deterministic(self):
        self.assertEqual(a.matrix(3,32),a.matrix(3,32))
        self.assertNotEqual(a.matrix(3,32),a.matrix(11,32))
    def test_08_distinct_control_domain(self):
        for n in a.SIDES:
            self.assertNotEqual(a.control_matrix(101,n),a.control_matrix(103,n))
            self.assertEqual(len(a.control_matrix(101,n)),n*n)
    def test_09_in_dictionary_exact_on_both_sides(self):
        for n in a.SIDES:
            for seed in a.IN_SEEDS:
                row=a.case_report(n,"in_dict",seed)
                self.assertEqual(row["selected_seed"],seed)
                self.assertTrue(row["full_tensor_exact"])
                self.assertEqual(row["check_mae"],0)
                self.assertEqual(row["matvec_3_of_3_exact"],3)
    def test_10_out_of_dictionary_negative(self):
        for n in a.SIDES:
            for seed in a.OUT_SEEDS:
                row=a.case_report(n,"out_dict",seed)
                self.assertFalse(row["full_tensor_exact"])
                self.assertGreater(row["check_mae"],0)
    def test_11_hash_controls_negative(self):
        for n in a.SIDES:
            for seed in a.CONTROL_IDS:
                row=a.case_report(n,"hash_control",seed)
                self.assertFalse(row["full_tensor_exact"])
                self.assertGreater(row["check_mae"],0)
    def test_12_no_CHECK_leak_in_seed_selection(self):
        n=32;original=a.matrix(3,n)
        modified=list(original)
        for i in a.check_index(n):
            modified[i]=7 if original[i]!=7 else -8
        self.assertEqual(a.choose_seed(original,n),a.choose_seed(tuple(modified),n))
    def test_13_no_CHECK_leak_in_mean_controls(self):
        n=32;original=a.matrix(11,n)
        modified=list(original)
        for i in a.check_index(n):modified[i]=-8 if original[i]!=-8 else 7
        self.assertEqual(a.means(original,n),a.means(tuple(modified),n))
    def test_14_fitted_controls_present_and_bounded(self):
        for n in a.SIDES:
            z=a.means(a.control_matrix(101,n),n)
            self.assertEqual(set(z),{"global_mean","row_mean","column_mean"})
            self.assertTrue(all(len(v)==n*n and all(-8<=x<=7 for x in v) for v in z.values()))
    def test_15_exact_matvec_output(self):
        n=32;w=a.matrix(11,n)
        for k in (0,1,2):
            self.assertEqual(a.matvec(w,n,k),a.matvec(tuple(w),n,k))
    def test_16_full_matrix_source_hashes(self):
        for n in a.SIDES:
            for seed in a.IN_SEEDS:
                x=a.case_report(n,"in_dict",seed)
                self.assertEqual(x["tensor_sha256"],x["predicted_sha256"])
    def test_17_no_silent_missing_fit(self):
        with self.assertRaises(ValueError):a.choose_seed((0,)*9,32)
        with self.assertRaises(ValueError):a.matrix(3,12)
    def test_18_no_unfrozen_family(self):
        with self.assertRaises(ValueError):a.case_report(32,"science",3)
    def test_19_matvec_difference_detected(self):
        n=32
        self.assertNotEqual(a.matvec(a.matrix(3,n),n,0),a.matvec(a.matrix(37,n),n,0))
    def test_20_report_fail_closed_science(self):
        z=a.report()
        self.assertEqual(z["completeness"]["source_matrices"],18)
        self.assertEqual(len(z["cases"]),18)
        self.assertEqual(z["classification"]["in_dictionary_exact"],"U09_PASS_RESTRICTED_ONLY")
        self.assertEqual(z["classification"]["out_of_dictionary_general"],"U09_NO_GO_OUT_DICT")
        self.assertEqual(z["classification"]["original_pretrained_llm_speed_memory_accuracy"],"UNVERIFIED")
        self.assertEqual(z["classification"]["scientific_first_use"],"NOT_ESTABLISHED")
        self.assertEqual(z["classification"]["production_admission"],"NOT_GRANTED")

if __name__=="__main__":unittest.main()

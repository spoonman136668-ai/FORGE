"""ACC-62 U14 frozen falsification and restricted positive controls (stdlib only)."""
import importlib.util
from pathlib import Path
import struct
import unittest
import zlib

SRC=Path(__file__).with_name("experiment.py")
sp=importlib.util.spec_from_file_location("acc62_u14",SRC)
a=importlib.util.module_from_spec(sp)
sp.loader.exec_module(a)

class U14Falsification(unittest.TestCase):
    def test_01_original_git_blob(self):
        self.assertEqual(a.source_identity()["original_registry_git_blob"],a.REGISTRY_BLOB)
    def test_02_prereg_custody(self):
        self.assertEqual(a.source_identity()["prereg_commit"],"fbb6793b2e37e3493468c7ea7b2bf9810c39adda")
    def test_03_one_byte_cardinality(self):
        self.assertEqual(a.number_of_all_source_weights(1),256)
        self.assertEqual(a.number_of_shorter_bit_codes(1),255)
    def test_04_two_byte_cardinality(self):
        self.assertEqual(a.number_of_all_source_weights(2),65536)
        self.assertEqual(a.number_of_shorter_bit_codes(2),65535)
    def test_05_three_byte_cardinality(self):
        self.assertEqual(a.number_of_all_source_weights(3),16777216)
        self.assertEqual(a.number_of_shorter_bit_codes(3),16777215)
    def test_06_exhaustive_fixed_seed_bound(self):
        self.assertEqual(len({a.fixed_seed16(i) for i in range(256)}),256)
        self.assertEqual(65536-len({a.fixed_seed16(i) for i in range(256)}),65280)
    def test_07_invalid_seed_rejected(self):
        for val in (-1,256,1000):
            with self.assertRaises(ValueError):a.fixed_seed16(val)
    def test_08_invalid_length_rejected(self):
        with self.assertRaises(ValueError):a.number_of_shorter_bit_codes(0)
        with self.assertRaises(ValueError):a.number_of_all_source_weights(-1)
    def test_09_periodic_exact_all_12_frozen_vectors(self):
        for n in a.SIZES:
            for period in a.PERIODS:
                x=a.periodic_source(n,period)
                encoded=a.periodic_encode(x,period)
                self.assertEqual(a.periodic_decode(encoded),x)
                self.assertEqual(a.sha(x),a.sha(a.periodic_decode(encoded)))
    def test_10_metadata_accounted_in_all_12_vectors(self):
        for n in a.SIZES:
            for period in a.PERIODS:
                encoded=a.periodic_encode(a.periodic_source(n,period),period)
                self.assertEqual(len(encoded),period+5)
                self.assertLess(len(encoded),n)
    def test_11_invalid_descriptor_rejected(self):
        d=a.periodic_encode(a.periodic_source(256,8),8)
        for x in (d[:-1],d+b"x",struct.pack(">IB",257,8)+d[5:],
                  struct.pack(">IB",256,3)+d[5:],b""):
            with self.assertRaises(ValueError):a.periodic_decode(x)
    def test_12_frozen_structured_input_not_hidden_reference(self):
        for n in a.SIZES:
            for period in a.PERIODS:
                x=a.periodic_source(n,period)
                self.assertEqual(x,a.periodic_pattern(period)*(n//period))
    def test_13_all_9_control_inputs_not_periodic(self):
        for n in a.SIZES:
            for key in a.CONTROL_KEYS:
                x=a.control_source(n,key)
                self.assertIsNone(a.periodic_encode(x,64))
    def test_14_zlib_reference_roundtrip_all_21(self):
        for n in a.SIZES:
            for period in a.PERIODS:
                x=a.periodic_source(n,period)
                self.assertEqual(zlib.decompress(zlib.compress(x,6)),x)
            for key in a.CONTROL_KEYS:
                x=a.control_source(n,key)
                self.assertEqual(zlib.decompress(zlib.compress(x,6)),x)
    def test_15_controls_not_assumed_mathematically_random(self):
        self.assertEqual(a.control_source(4096,0),a.control_source(4096,0))
        self.assertNotEqual(a.control_source(4096,0),a.control_source(4096,1))
    def test_16_report_scope_and_nonpromotion(self):
        c=a.report()["classification"]
        self.assertEqual(c["universal_arbitrary_exact_shrinking"],"U14_NO_GO_PROVEN")
        self.assertEqual(c["restricted_structured_lossless"],"U14_PASS_RESTRICTED_ONLY")
        self.assertEqual(c["original_model_weight_speed_accuracy_rss"],"UNVERIFIED")
        self.assertEqual(c["scientific_first_use"],"NOT_ESTABLISHED")
        self.assertEqual(c["production_admission"],"NOT_GRANTED")
    def test_17_report_full_matrix_and_hashes(self):
        z=a.report()
        self.assertEqual(len(z["structured"]),12)
        self.assertEqual(len(z["controls"]),9)
        self.assertTrue(all(x["exact"] and x["source_sha256"]==x["decoded_sha256"] for x in z["structured"]))
        self.assertTrue(all(x["source_sha256"]==x["zlib6_recovered_sha256"] for x in z["controls"]))
    def test_18_control_not_encoded_as_short_periodic(self):
        for n in a.SIZES:
            for key in a.CONTROL_KEYS:
                self.assertIsNone(a.periodic_encode(a.control_source(n,key),64))

if __name__=="__main__":unittest.main()

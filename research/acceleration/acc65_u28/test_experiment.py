"""ACC65 U28: NTT exactness and semantic limitation controls."""
import importlib.util
import random
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("acc65_u28",Path(__file__).with_name("experiment.py"))
u=importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

class NTTResearch(unittest.TestCase):
    def test_01_original_claim_blob(self):
        self.assertEqual(u.source_check()["original_registry_blob"],u.REGISTRY_GIT_BLOB)
    def test_02_prereg_commit(self):
        self.assertEqual(u.source_check()["prereg_commit"],"7929942f1bfd97b663bd6c8444a07bce1f957cf4")
    def test_03_modulus_primitive_root(self):
        self.assertEqual(u.P,998244353)
        self.assertEqual(u.GENERATOR,3)
        self.assertEqual(pow(3,(u.P-1)//2,u.P),u.P-1)
    def test_04_size_divides_group(self):
        for n in u.SIZES:self.assertEqual((u.P-1)%n,0)
    def test_05_inverse_transform_all_sizes(self):
        for n in u.SIZES:
            x=tuple((i*i*23-50)%u.P for i in range(n))
            self.assertEqual(u.transform(u.transform(x),True),x)
    def test_06_zero_transform(self):
        for n in u.SIZES:self.assertEqual(u.transform((0,)*n),(0,)*n)
    def test_07_zero_convolution(self):
        for n in u.SIZES:
            x=tuple(i%u.P for i in range(n))
            self.assertEqual(u.ntt_convolution(x,(0,)*n),(0,)*n)
            self.assertEqual(u.naive_convolution(x,(0,)*n),(0,)*n)
    def test_08_impulse_identity(self):
        for n in u.SIZES:
            x=tuple((i*17-123)%u.P for i in range(n))
            delta=(1,)+(0,)*(n-1)
            self.assertEqual(u.ntt_convolution(x,delta),x)
    def test_09_shift_convolution(self):
        n=32
        x=tuple(i%u.P for i in range(n))
        delta=(0,1)+(0,)*(n-2)
        self.assertEqual(u.ntt_convolution(x,delta),u.shift(x))
    def test_10_negative_coefficient_modulus(self):
        a=(-1,1)+(0,)*30
        b=(2,-3)+(0,)*30
        self.assertEqual(u.ntt_convolution(a,b),u.naive_convolution(a,b))
    def test_11_parity_dense_all_sizes(self):
        for n in u.SIZES:
            a,b=u.inputs(n,"dense",28101)
            self.assertEqual(u.ntt_convolution(a,b),u.naive_convolution(a,b))
    def test_12_parity_sparse_all_sizes(self):
        for n in u.SIZES:
            a,b=u.inputs(n,"sparse",28103)
            self.assertEqual(u.ntt_convolution(a,b),u.naive_convolution(a,b))
    def test_13_reproducible_frozen_inputs(self):
        for n in u.SIZES:
            self.assertEqual(u.inputs(n,"dense",28107),u.inputs(n,"dense",28107))
    def test_14_sparse_has_fewer_nonzeros(self):
        n=1024
        a,_=u.inputs(n,"dense",28101)
        b,_=u.inputs(n,"sparse",28101)
        self.assertLess(sum(bool(v) for v in b),sum(bool(v) for v in a)//2)
    def test_15_reject_unsupported_ntt_shape(self):
        for n in (0,1,3,7,63):
            with self.assertRaises(ValueError):u.transform((1,)*n)
    def test_16_reject_shape_mismatch(self):
        with self.assertRaises(ValueError):u.ntt_convolution((1,2),(3,4,5,6))
        with self.assertRaises(ValueError):u.naive_convolution((1,2),(3,4,5,6))
    def test_17_reject_unfrozen_inputs(self):
        with self.assertRaises(ValueError):u.inputs(256,"dense",28101)
        with self.assertRaises(ValueError):u.inputs(32,"other",28101)
        with self.assertRaises(ValueError):u.inputs(32,"dense",999)
    def test_18_semantic_counterexample_noncommutation(self):
        q=u.semantic_falsifier()
        self.assertTrue(q["explicit_not_shift_equivariant"])
        self.assertNotEqual(q["left_F_of_shift"],q["right_shift_of_F"])
    def test_19_fixed_convolution_shift_equivariance(self):
        n=32
        a,b=u.inputs(n,"dense",28101)
        self.assertEqual(u.ntt_convolution(u.shift(a),b),u.shift(u.ntt_convolution(a,b)))
    def test_20_fixed_convolution_cannot_represent_F(self):
        n=8
        e0=(1,)+(0,)*7
        self.assertNotEqual(u.position_sensitive(u.shift(e0)),u.shift(u.position_sensitive(e0)))
    def test_21_digest_deterministic_and_position_sensitive(self):
        x=(1,)+(0,)*31
        self.assertEqual(u.digest(x),u.digest(x))
        self.assertNotEqual(u.digest(x),u.digest(u.shift(x)))
    def test_22_sparse_naive_zero_skip_exact(self):
        n=512
        a=(1,)+(0,)*(n-1)
        b=(0,)*3+(9,)+(0,)*(n-4)
        self.assertEqual(u.ntt_convolution(a,b),u.naive_convolution(a,b))
    def test_23_no_claim_original_semantics(self):
        self.assertIn("NOT_LANGUAGE_SEMANTICS",u.source_check()["source_scope"])
    def test_24_paired_count_frozen(self):
        self.assertEqual(len(u.SIZES)*len(u.REGIMES)*len(u.SEEDS)*u.REPEATS,72)

if __name__=="__main__":unittest.main()

"""F124-BW universal mathematical obstruction, no source first-use."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("original_BW_analysis",HERE/"f124bw_expressivity_proof.py")
proof=importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


class TwoPointUniversalStructuralBound(unittest.TestCase):
    def test_three_xor_shears_is_swap_over_all_65536_inputs(self):
        for x in range(65536):
            self.assertEqual(proof.three_shear_xor(x),proof.byte_swap(x))

    def test_bq_frozen_hypothesis_is_conditional_injective(self):
        f=proof.frozen_model()
        self.assertEqual(f.STATE_BITS,32)
        for gain1,bias1,mode1 in (
                (1,0,0),(1,0,1),(53,37,0),(53,37,1),
                (127,255,0),(127,255,1)):
            p=(gain1,bias1,41,19,mode1,0)
            for h in (0,53,255):
                transformed=[f.forward((h<<8)|lo,p)&255 for lo in range(256)]
                self.assertEqual(len(set(transformed)),256)
                self.assertEqual(transformed,[
                    proof.closed_form_first_low(lo,h,p) for lo in range(256)
                ])

    def test_single_contradiction_applies_universally_by_cancellation(self):
        h=0x35
        x0=h<<8
        x1=x0|1
        self.assertEqual(proof.byte_swap(x0)&255,h)
        self.assertEqual(proof.byte_swap(x1)&255,h)
        # (lo + k) % 256 and lo XOR k are both bijections for any
        # fixed k. This is universal algebra, not a parameter sample.
        for k in range(256):
            self.assertNotEqual((0+k)&255,(1+k)&255)
            self.assertNotEqual(0^k,1^k)
        theoretical=proof.invariant_for_all_programs()
        self.assertTrue(theoretical["two_input_contradiction_for_all_BQ_programs"])

    def test_original_causal_source_and_holdout_untouched(self):
        result=proof.audit()
        self.assertEqual(result["three_XOR_shear_byteswap_domain_count"],65536)
        self.assertEqual(result["model_state_bits_unchanged"],32)
        for name in ("old_registered_scientific_source_used",
                     "new_development_924000_or_925000_cases_born",
                     "protected_128_case_cohorts_used",
                     "new_model_implemented_or_fit",
                     "scientific_transfer_accepted",
                     "optimizer_policy_promoted"):
            self.assertFalse(result[name],name)

    def test_effective_30bit_original_hypothesis_and_two_32bit_flags(self):
        f=proof.frozen_model()
        self.assertEqual(len(f.ODD_GAINS),64)
        self.assertEqual(64*256*64*256*2*2,2**30)
        for program in ((1,0,1,0,1,1),(53,37,41,19,0,1),
                        (127,255,127,255,1,0)):
            for option in (0,1):
                for reserve in (0,1):
                    packed=proof.encode_same_32bits_with_two_new_structural_flags(
                        program,option,reserve)
                    self.assertLess(packed,2**32)
                    self.assertEqual(
                        proof.decode_same_32bits_with_two_new_structural_flags(packed),
                        (program,option,reserve))

    def test_one_structural_flag_constructively_expresses_three_shear_swap(self):
        m=proof.frozen_model()
        old=(1,0,1,0,1,1)
        self.assertNotEqual(m.forward(0x3500,old)&255,m.forward(0x3501,old)&255)
        for x in range(65536):
            self.assertEqual(
                proof.optional_third_xor_shear(x,m,old,1),
                proof.byte_swap(x))
            self.assertEqual(proof.optional_third_xor_shear(x,m,old,0),
                             m.forward(x,old))
        self.assertFalse(proof.audit()["successor_real_CPU_RSS_parity_established"])

    def test_reject_invalid_probe_input(self):
        with self.assertRaises(RuntimeError):
            proof.byte_swap(-1)
        with self.assertRaises(RuntimeError):
            proof.three_shear_xor(65536)


if __name__=="__main__":
    unittest.main()

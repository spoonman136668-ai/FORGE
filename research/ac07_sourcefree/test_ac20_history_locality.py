"""AC-20 restricted source-free tests: no original episodes or model calls."""
import itertools
import unittest

import ac20_history_locality as a

class AC20HistoryLocalityTests(unittest.TestCase):
    def test_exact_original_source_and_native_commit_pins(self):
        self.assertEqual(a.SOURCE_COMMIT,
            "c94e9a4cd3641588b6b8507e71ccee5c27032bdf")
        self.assertEqual(a.SOURCE_BLOB,
            "6af2371dce21804140ea141ccb7be14e003ba275")
        self.assertEqual(a.NATIVE_COMMIT,
            "a39171a76d0d7817e3563682bb139a9d7ecf37c4")
        self.assertEqual(a.NATIVE_BLOB,
            "68a1423e0bd7206af511212c14b6ce8534154cc2")

    def test_all_sixteen_public_history_four_site_roundtrips(self):
        bits_seen = set()
        for history in itertools.product((0,1),repeat=4):
            bits = a.four_public_history_bits(*history)
            self.assertEqual(a.decode_four_public_history(bits),history)
            bits_seen.add(tuple(bits))
        self.assertEqual(len(bits_seen),16)

    def test_prior_ac19_terminal_readout_omits_earlier_two_public_bits(self):
        # In AC-19 terminal readout only public (stage=1, s2, x2) is present.
        patterns=set()
        for s1,x1,s2,x2 in itertools.product((0,1),repeat=4):
            patterns.add(tuple(a.ac19.encode_before(1,s2,x2)))
        self.assertEqual(len(patterns),4)

    def test_one_hop_site5_cannot_expose_four_binary_history_bits(self):
        signatures={(h[1],h[2],h[3])
                    for h in itertools.product((0,1),repeat=4)}
        self.assertEqual(len(signatures),8)
        self.assertLess(len(signatures),16)
        # A two-readout union covers all four public bits; this is NOT
        # evidence of a trained two-cell native history mechanism.
        joint={(h[0],h[1],h[2],h[3])
               for h in itertools.product((0,1),repeat=4)}
        self.assertEqual(len(joint),16)

    def test_original_equation_audit_conflicts_in_all_four_ac19_buckets(self):
        buckets={}
        for h in itertools.product((0,1),repeat=4):
            buckets.setdefault((h[2],h[3]),set()).add(
                a.source_equation_audit_only(*h,0.5))
        self.assertEqual(len(buckets),4)
        self.assertTrue(all(v == {0,1} for v in buckets.values()))
        self.assertNotEqual(
            a.source_equation_audit_only(0,0,0,1,0.5),
            a.source_equation_audit_only(1,1,0,1,0.5))

    def test_invalid_public_and_hidden_input_rejected(self):
        with self.assertRaisesRegex(ValueError,"AC20_INVALID_PUBLIC_S1"):
            a.four_public_history_bits(True,0,0,1)
        with self.assertRaisesRegex(ValueError,"AC20_INVALID_PUBLIC_X2"):
            a.four_public_history_bits(0,0,0,2)
        with self.assertRaisesRegex(ValueError,"AC20_INVALID_HISTORY_BITS"):
            a.decode_four_public_history([0,0,1,0,0,0,1,0])
        with self.assertRaisesRegex(ValueError,"AC20_INVALID_HISTORY_BITS"):
            a.decode_four_public_history([0,0,0,0,0,False,1,0])
        with self.assertRaisesRegex(ValueError,"AC20_AUDIT_LATENT_OUTSIDE_FIXED_EXAMPLE"):
            a.source_equation_audit_only(0,0,0,1,2)
        with self.assertRaises(TypeError):
            a.four_public_history_bits(0,0,0,1,u=0.5)

if __name__=="__main__":
    unittest.main()

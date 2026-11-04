"""G102 P1 development feasibility protocol checks (model-free)."""
import unittest
from research.cpu_g97.g102_original_storage import (
    NUM_VARIANTS, POSITIONS, TOKEN_DELTAS, variant_tokens, assess)


class OriginalStorageProtocolTests(unittest.TestCase):
    def test_four_fixed_equal_shape_variants(self):
        seed=list(range(200))
        variants=variant_tokens(seed,50257)
        self.assertEqual(len(variants),NUM_VARIANTS)
        self.assertEqual(len({tuple(v) for v in variants}),NUM_VARIANTS)
        for i,v in enumerate(variants):
            self.assertEqual(len(v),len(seed))
            self.assertEqual(sum(a!=b for a,b in zip(seed,v)),1)
            self.assertEqual(v[POSITIONS[i]],(seed[POSITIONS[i]]+TOKEN_DELTAS[i])%50257)

    def test_rejects_short_or_inconsistent_protocol(self):
        with self.assertRaisesRegex(RuntimeError,"SHORT_PREFIX"):
            variant_tokens([0]*10,50257)
        with self.assertRaisesRegex(RuntimeError,"INVALID_VOCAB"):
            variant_tokens(list(range(100)),999)
        with self.assertRaisesRegex(RuntimeError,"VARIANT_PROTOCOL_DRIFT"):
            variant_tokens(list(range(100)),50257,offsets=(0,1,5))

    def test_exact_mechanism_with_real_base_cost_and_controls(self):
        base=bytes(range(256))*20
        targets=[]
        for x in range(NUM_VARIANTS):
            b=bytearray(base)
            b[200+x]^=x+1
            targets.append(bytes(b))
        records,ac,decision=assess(base,targets)
        self.assertEqual(len(records),NUM_VARIANTS)
        self.assertEqual(ac["residual_with_base_bytes"],
                         len(base)+sum(r["xor_residual_bytes"] for r in records))
        self.assertTrue(all(r["exact"] for r in records))
        self.assertIn(decision,("STORAGE_FEASIBLE_DIAGNOSTIC","STORAGE_NO_GO_DIAGNOSTIC"))

    def test_insufficient_population_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"VARIANT_COUNT"):
            assess(b"abc",[b"abc"])


if __name__=="__main__":
    unittest.main()

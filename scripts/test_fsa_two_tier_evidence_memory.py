"""Engineering controls for fixed-budget two-tier evidence memory."""
import unittest
from unittest.mock import patch

from scripts.two_tier_evidence_memory import TwoTierEvidence


class TwoTierEvidenceTests(unittest.TestCase):
    def test_lifetime_saturation_never_decays_or_wraps(self):
        memory = TwoTierEvidence()
        memory._lifetime[0][0][1] = 65535
        size = len(memory.snapshot())
        for _ in range(30):
            memory.observe(0, 0, 1)
        self.assertEqual(memory.lifetime_counts(0, 0), (0, 65535))
        self.assertEqual(len(memory.snapshot()), size)
        self.assertEqual(TwoTierEvidence.LEARNED_BYTES, 194)
        self.assertEqual(TwoTierEvidence.CHECKPOINT_BYTES, 230)

    def test_recent_reversal_adapts_without_mutating_lifetime(self):
        memory = TwoTierEvidence()
        # Stationary first regime: action 0 has higher observed success.
        for _ in range(10):
            memory.observe(0, 0, 1)
            memory.observe(0, 1, 0)
        self.assertEqual(memory.choose_lifetime(0), 0)
        self.assertEqual(memory.choose(0), 0)
        prior_lifetime = (memory.lifetime_counts(0, 0),
                          memory.lifetime_counts(0, 1))
        # Recent reversal: action 1 now has higher observed success.
        for _ in range(4):
            memory.observe(0, 0, 0)
            memory.observe(0, 1, 1)
        self.assertEqual(memory.choose_lifetime(0), 0)
        self.assertEqual(memory.choose(0), 1)
        self.assertNotEqual(memory.recent_counts(0, 0), (0, 0))
        self.assertNotEqual(memory.recent_counts(0, 1), (0, 0))
        self.assertNotEqual(prior_lifetime, (memory.lifetime_counts(0, 0),
                                             memory.lifetime_counts(0, 1)))

    def test_recent_ring_is_fixed_size_and_evicts_oldest(self):
        memory = TwoTierEvidence()
        start_size = len(memory.snapshot())
        for i in range(10000):
            memory.observe(i % 16, i % 2, (i // 2) % 2)
        self.assertEqual(len(memory.snapshot()), start_size)
        self.assertEqual(memory._recent_count, 64)
        self.assertEqual(len(memory._recent), 64)
        self.assertEqual(len(memory.snapshot()), 230)

    def test_recent_fallback_requires_minimum_support_in_each_arm(self):
        memory = TwoTierEvidence()
        # Old lifetime evidence favors action 0, but only one recent observation
        # per arm is available, so the recent estimate must not override it.
        memory._lifetime[0][0][1] = 4
        memory._lifetime[0][1][0] = 4
        memory.observe(0, 0, 0)
        memory.observe(0, 1, 1)
        self.assertIsNone(memory._winner(memory.recent_counts(0, 0),
                                         memory.recent_counts(0, 1), 2))
        self.assertEqual(memory.choose_lifetime(0), 0)
        self.assertEqual(memory.choose(0, minimum_support=2), 0)


    def test_checkpoint_roundtrip_preserves_both_tiers_and_decisions(self):
        memory = TwoTierEvidence()
        for _ in range(12):
            memory.observe(4, 0, 1)
            memory.observe(4, 1, 0)
        for _ in range(5):
            memory.observe(4, 0, 0)
            memory.observe(4, 1, 1)
        before = memory.snapshot()
        restored = TwoTierEvidence.restore(before)
        self.assertEqual(restored.snapshot(), before)
        self.assertEqual(restored.lifetime_counts(4, 0), memory.lifetime_counts(4, 0))
        self.assertEqual(restored.recent_counts(4, 1), memory.recent_counts(4, 1))
        self.assertEqual(restored.choose(4), memory.choose(4))
        self.assertEqual(restored.choose_lifetime(4), memory.choose_lifetime(4))

    def test_checkpoint_tamper_wrong_size_and_unused_payload_rejected(self):
        memory = TwoTierEvidence()
        memory.observe(2, 1, 0)
        original = memory.snapshot()
        corrupt = bytearray(original)
        corrupt[10] ^= 1
        for candidate in (bytes(corrupt), original[:-1], b"BAD!" + original[4:]):
            with self.subTest(size=len(candidate)), self.assertRaises(ValueError):
                TwoTierEvidence.restore(candidate)
        # Forge a valid digest around an invalid nonzero unused ring slot.
        import hashlib
        raw = bytearray(original[:-32])
        raw[-1] = 1
        forged = bytes(raw) + hashlib.sha256(raw).digest()
        with self.assertRaisesRegex(ValueError, "UNUSED_SLOT_NONZERO"):
            TwoTierEvidence.restore(forged)

    def test_addresses_and_invalid_inputs_are_isolated(self):
        memory = TwoTierEvidence()
        before = memory.snapshot()
        for args in ((-1, 0, 0), (16, 0, 0), (0, 2, 0),
                     (0, 0, -1), (True, 0, 0), (0, True, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                memory.observe(*args)
            self.assertEqual(memory.snapshot(), before)
        memory.observe(0, 0, 1)
        self.assertEqual(memory.lifetime_counts(1, 0), (0, 0))
        self.assertEqual(memory.recent_counts(1, 0), (0, 0))
        for bad_support in (0, 65, True):
            with self.assertRaises(ValueError):
                memory.choose(0, minimum_support=bad_support)

    def test_no_file_network_or_interactive_execution(self):
        memory = TwoTierEvidence()
        with patch("builtins.open", side_effect=AssertionError("I/O forbidden")), \
             patch("builtins.input", side_effect=AssertionError("prompt forbidden")):
            memory.observe(0, 0, 1)
            snapshot = memory.snapshot()
            restored = TwoTierEvidence.restore(snapshot)
        self.assertEqual(restored.snapshot(), snapshot)


if __name__ == "__main__":
    unittest.main()

"""G100 development-only stream identity and separation tests (no model)."""
import unittest
from research.cpu_g97.g100_stream_manifest import freeze, canonical_bytes, ARMS
from research.cpu_g97.g97_stream_manifest import freeze as freeze_g97


class G100StreamManifestTests(unittest.TestCase):
    def setUp(self):
        self.cohort = [{"source_row": i, "instruction_sha256": f"{i:064x}"} for i in range(12)]

    def test_frozen_independent_development_stream(self):
        a, digest = freeze(self.cohort)
        b, digest2 = freeze(self.cohort)
        old, old_digest = freeze_g97(self.cohort)
        self.assertEqual(a, b)
        self.assertEqual(digest, digest2)
        self.assertNotEqual(digest, old_digest)
        self.assertNotEqual(a["strata"]["round_robin"]["requests"], old["strata"]["round_robin"]["requests"])
        self.assertEqual(a["phase"], "DEVELOPMENT_ONLY")
        self.assertEqual(a["rank_interval"], [276, 288])
        self.assertFalse(a["protected_heldout_used"])
        self.assertEqual(a["arms"], list(ARMS))
        for stratum in a["strata"].values():
            self.assertEqual(len(stratum["requests"]), 48)
            self.assertEqual(len(stratum["traffic_sha256"]), 64)
        self.assertEqual(len(canonical_bytes(a)), len(canonical_bytes(b)))

    def test_duplicate_source_and_invalid_hash_rejected(self):
        dup = list(self.cohort)
        dup[-1] = dict(dup[0])
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            freeze(dup)
        bad = [dict(r) for r in self.cohort]
        bad[2]["instruction_sha256"] = "not-a-sha256"
        with self.assertRaisesRegex(ValueError, "INVALID"):
            freeze(bad)

    def test_order_is_keyed_to_content_not_source_or_model_timing(self):
        a, _ = freeze(self.cohort)
        shifted = [dict(x, source_row=x["source_row"] + 100) for x in self.cohort]
        b, _ = freeze(shifted)
        for label in a["strata"]:
            aa = a["strata"][label]["requests"]
            bb = b["strata"][label]["requests"]
            self.assertEqual([x["instruction_sha256"] for x in aa],
                             [x["instruction_sha256"] for x in bb])
            self.assertEqual([x["source_row"] + 100 for x in aa],
                             [x["source_row"] for x in bb])


if __name__ == "__main__":
    unittest.main()

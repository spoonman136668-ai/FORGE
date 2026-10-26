"""Read-only original-source identity and public-custody tests.

NO original Shuttle episodes, RNG actions, simulator, model fitting or FSA use.
The public event fixture below is a shape check, NOT an original source event.
"""
import os
import unittest

from shuttle_source_contract import (
    ACTIONS, OBSERVATIONS, SOURCE_GIT_BLOB, PublicEventGuard,
    git_blob_id, parse_original_source, public_source_receipt,
)


class ShuttleOriginalSourceOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ITD02_SHUTTLE_SOURCE")
        if not path:
            raise unittest.SkipTest("Original pinned source absent; dedicated qualification sets ITD02_SHUTTLE_SOURCE")
        with open(path, "rb") as f:
            cls.raw = f.read()

    def test_pinned_authentic_source_and_all_probability_rows(self):
        self.assertEqual(git_blob_id(self.raw), SOURCE_GIT_BLOB)
        private = parse_original_source(self.raw)
        self.assertEqual(len(private.transition), 3)
        self.assertEqual(len(private.observation), 8)
        self.assertEqual(len(private.start), 8)
        self.assertEqual(len(private.reward_rows), 3)
        for action in private.transition:
            for row in action:
                self.assertEqual(len(row), 8)
                self.assertAlmostEqual(sum(row), 1.0, places=12)
        for row in private.observation:
            self.assertEqual(len(row), 5)
            self.assertAlmostEqual(sum(row), 1.0, places=12)
        self.assertEqual(private.reward_rows,
                         ((1, 1, 1, -3), (1, 6, 6, -3), (2, 3, 0, 10)))

    def test_public_receipt_has_no_private_source_law(self):
        receipt = public_source_receipt(self.raw)
        self.assertEqual(receipt["source_git_blob"], SOURCE_GIT_BLOB)
        self.assertEqual(receipt["original_episodes"], 0)
        self.assertEqual(receipt["public_actions"], ACTIONS)
        self.assertEqual(receipt["public_observations"], OBSERVATIONS)
        self.assertEqual(set(receipt), {
            "source_git_blob", "source_commit", "public_actions",
            "public_observations", "source_only", "original_episodes"})
        self.assertNotIn("state", str(receipt).lower())
        self.assertNotIn("transition", str(receipt).lower())

    def test_identity_drift_and_structural_drift_both_fail_closed(self):
        changed = self.raw.replace(b"discount: 0.95", b"discount: 0.96", 1)
        self.assertNotEqual(changed, self.raw)
        with self.assertRaisesRegex(ValueError, "IDENTITY_DRIFT"):
            parse_original_source(changed)
        # Re-pin mutated bytes *in the test only* to exercise matrix validation.
        changed = self.raw.replace(b"0.0 0.0 0.0 0.0 1.0",
                                   b"0.0 0.0 0.0 0.0 0.9", 1)
        self.assertNotEqual(changed, self.raw)
        with self.assertRaisesRegex(ValueError, "ROW_SUM"):
            parse_original_source(changed, expected_blob=git_blob_id(changed))

    def test_no_world_execution_or_private_state_in_public_seam(self):
        guard = PublicEventGuard()
        with self.assertRaisesRegex(ValueError, "NO_PENDING"):
            guard.accept(action="Backup", next_observation="MRV",
                         reward=0, terminal=False)
        for private in ("hidden_state", {"obs": "Nothing"}, None):
            with self.assertRaises(ValueError):
                guard.begin(private)
        guard.begin("Nothing")
        for bad in (
            {"action": "Teleport", "next_observation": "MRV", "reward": 0, "terminal": False},
            {"action": "Backup", "next_observation": "hidden_state", "reward": 0, "terminal": False},
            {"action": "Backup", "next_observation": "MRV", "reward": 9, "terminal": False},
            {"action": "Backup", "next_observation": "MRV", "reward": True, "terminal": False},
            {"action": "Backup", "next_observation": "MRV", "reward": 0, "terminal": 0},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    guard.accept(**bad)
                self.assertTrue(guard.pending)
                self.assertEqual(guard.transitions, 0)
        with self.assertRaises(TypeError):
            guard.accept(action="Backup", next_observation="MRV",
                         reward=0, terminal=False, hidden_state=3)
        # Synthetic public wire fixture only; NOT original Shuttle execution.
        event = guard.accept(action="Backup", next_observation="MRV",
                             reward=0, terminal=False)
        self.assertEqual(set(event), {"observation", "action", "next_observation",
                                      "reward", "terminal"})
        self.assertEqual(guard.transitions, 1)
        self.assertFalse(guard.pending)



def load_tests(loader, suite, pattern):
    # The existing source-only CI already executes this test module on both
    # platforms. Include the isolated producer's NO-ADMISSION tests without
    # altering workflow permissions or executing a source episode.
    from test_shuttle_owner_producer_sourceonly import (
        OriginalProducerNotAdmittedTests,
    )
    suite.addTests(loader.loadTestsFromTestCase(OriginalProducerNotAdmittedTests))
    return suite


if __name__ == "__main__":
    unittest.main()

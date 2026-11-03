"""Model-free G100 adapter isolation and restoration qualification."""
import unittest
from unittest.mock import patch
from research.cpu_g97 import g100_original_adapter as adapter
from research.cpu_g97.g100_deferred_admission import DeferredFirstAdmissionCache


class G100OriginalAdapterTests(unittest.TestCase):
    def test_candidate_separate_from_frozen_controls(self):
        frozen = adapter.g97.frozen
        original = frozen.AdmissionCache
        calls = []
        def fake(model, stream, prefixes, keys, policy, torch, proc):
            self.assertEqual(policy, "lru")
            cache = frozen.AdmissionCache(policy)
            self.assertIsInstance(cache, DeferredFirstAdmissionCache)
            calls.append(cache)
            return {"outputs": 1}, {"metrics": 2}
        with patch.object(frozen, "run_policy", side_effect=fake):
            result = adapter.run_g100(None, [], [], [], None, None)
        self.assertEqual(result, ({"outputs": 1}, {"metrics": 2}))
        self.assertEqual(len(calls), 1)
        self.assertIs(frozen.AdmissionCache, original)

    def test_restores_original_after_runner_failure(self):
        frozen = adapter.g97.frozen
        original = frozen.AdmissionCache
        with patch.object(frozen, "run_policy", side_effect=RuntimeError("G100_TEST_FAILURE")):
            with self.assertRaisesRegex(RuntimeError, "G100_TEST_FAILURE"):
                adapter.run_g100(None, [], [], [], None, None)
        self.assertIs(frozen.AdmissionCache, original)

    def test_g97_runner_still_uses_distinct_cache_class(self):
        frozen = adapter.g97.frozen
        original = frozen.AdmissionCache
        from g97_overflow_bypass import OverflowBypassCache
        def fake(model, stream, prefixes, keys, policy, torch, proc):
            candidate = frozen.AdmissionCache(policy)
            self.assertIs(type(candidate), OverflowBypassCache)
            self.assertNotIsInstance(candidate, DeferredFirstAdmissionCache)
            return [], {}
        with patch.object(frozen, "run_policy", side_effect=fake):
            adapter.g97.run_g97(None, [], [], [], None, None)
        self.assertIs(frozen.AdmissionCache, original)


if __name__ == "__main__":
    unittest.main()

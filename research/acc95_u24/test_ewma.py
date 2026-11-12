"""ACC-98 EWMA control contracts (offline, source-free FIT/DEV only)."""
import unittest
from ewma import EWMATable, RATES, evaluate_ewma
from switching import switching_trace

class EMAContracts(unittest.TestCase):
    def test_frozen_rate_grid(self):
        self.assertEqual(RATES, (0.02, 0.1, 0.3, 0.7))
        for bad in (0.0, 0.5, 1.0, "0.1", True):
            with self.assertRaises(ValueError):
                EWMATable(bad)

    def test_isolation_and_restore(self):
        m = EWMATable(0.3)
        original = m.snapshot()
        m.observe([((1, 0, 1), 1)])
        self.assertEqual(m.predict((1, 0, 1)), 1)
        self.assertEqual(m.predict((0, 0, 0)), 0)
        self.assertNotEqual(original, m.snapshot())
        restored = EWMATable.restore(m.snapshot())
        self.assertEqual(restored.snapshot(), m.snapshot())
        with self.assertRaises(ValueError):
            restored.observe([((0, 1, 1), 2)])
        with self.assertRaises(ValueError):
            EWMATable.restore('{"rate":0.3,"means":[0.1],"counts":[]}')

    def test_dev_deterministic_and_nonadmission(self):
        trace = switching_trace("DEV", 54, 701)
        a = evaluate_ewma(trace, 0.1)
        b = evaluate_ewma(trace, 0.1)
        self.assertEqual(a, b)
        self.assertEqual(a["phase_queries"], [2432, 1216, 2432])
        self.assertTrue(a["cold_restore_exact"])
        self.assertEqual(a["scientific_acceptance"], "NOT_GRANTED")
        self.assertFalse(a["resources_qualified"])

    def test_tamper_and_reserved_rejection(self):
        trace = switching_trace("FIT", 90, 601)
        trace["reserved_test_used"] = True
        with self.assertRaises(ValueError):
            evaluate_ewma(trace, 0.02)
        trace["reserved_test_used"] = False
        trace["records"][4]["step"] = 3
        with self.assertRaises(ValueError):
            evaluate_ewma(trace, 0.02)

if __name__ == "__main__":
    unittest.main()

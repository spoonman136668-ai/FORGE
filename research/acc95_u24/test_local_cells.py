"""ACC-99 local-cell contract and equal-information control tests."""
import unittest
from local_cells import LocalCells, evaluate_local
from ewma import EWMATable, evaluate_ewma
from switching import switching_trace

class LocalCellContracts(unittest.TestCase):
    def test_no_crosstalk_and_restart(self):
        model = LocalCells(0.3)
        model.observe([((1, 0, 1), 1)])
        self.assertEqual(model.predict((1, 0, 1)), 1)
        self.assertEqual(model.predict((0, 0, 0)), 0)
        self.assertEqual(model.count[0], 0)
        restored = LocalCells.restore(model.snapshot())
        self.assertEqual(restored.snapshot(), model.snapshot())
        with self.assertRaises(ValueError):
            LocalCells.restore('{"schema":"wrong"}')

    def test_rate_and_target_guards(self):
        for bad in (0.25, 0, "0.1", True):
            with self.assertRaises(ValueError):
                LocalCells(bad)
        with self.assertRaises(ValueError):
            LocalCells(0.1).observe([((1, 0, 1), 2)])

    def test_affine_equivalence_to_ewma_in_observation_stream(self):
        # Crucial falsifier: local update is an affine recoding of EWMA.
        for rate in (0.02, 0.1, 0.3, 0.7):
            local, ewma = LocalCells(rate), EWMATable(rate)
            stream = [((1, 0, 1), 1)] * 3 + [((1, 0, 1), 0)] * 5
            for visible in stream:
                local.observe([visible])
                ewma.observe([visible])
                self.assertAlmostEqual(local.state[5], 2 * ewma.means[5] - 1, places=12)
                self.assertEqual(local.predict((1, 0, 1)),
                                 ewma.predict((1, 0, 1)))

    def test_dev_and_seal(self):
        trace = switching_trace("DEV", 54, 701)
        report = evaluate_local(trace)
        self.assertEqual(report["phase_queries"], [2432, 1216, 2432])
        self.assertTrue(report["cold_restore_exact"])
        self.assertFalse(report["resources_qualified"])
        self.assertEqual(report["scientific_acceptance"], "NOT_GRANTED")
        self.assertEqual(evaluate_local(trace), report)
        self.assertEqual(len(evaluate_ewma(trace, 0.1)["phase_accuracy"]), 3)
        trace["reserved_test_used"] = True
        with self.assertRaises(ValueError):
            evaluate_local(trace)

if __name__ == "__main__":
    unittest.main()

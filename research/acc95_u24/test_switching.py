"""ACC-97 source-only negative and custody guards; never opens reserved TEST."""
import unittest
from switching import (ADAPT_STEPS, PRE_STEPS, POST_STEPS, TOTAL_STEPS,
                       switching_trace, development_screen, evaluate_count_table,
                       frozen_rule_pair)

class SwitchContracts(unittest.TestCase):
    def test_frozen_pair_and_reserved_guard(self):
        self.assertEqual(frozen_rule_pair("FIT", 90), (90, 110))
        self.assertEqual(frozen_rule_pair("DEV", 150), (150, 54))
        for split, rule, seed in (("TEST", 22, 809), ("DEV", 22, 701),
                                  ("FIT", 54, 601), ("DEV", 90, 701)):
            with self.assertRaises(ValueError):
                switching_trace(split, rule, seed)

    def test_exact_phases_visibility_and_determinism(self):
        a = switching_trace("FIT", 90, 601)
        b = switching_trace("FIT", 90, 601)
        self.assertEqual(a["trace_sha256"], b["trace_sha256"])
        self.assertEqual(len(a["records"]), 320)
        self.assertEqual(TOTAL_STEPS, PRE_STEPS + ADAPT_STEPS + POST_STEPS)
        for step, record in enumerate(a["records"]):
            self.assertEqual(record["step"], step)
            self.assertEqual(len(record["visible"]), 6)
            self.assertEqual(len(record["queries"]), 19)
        self.assertNotEqual(a["trace_sha256"],
                            switching_trace("FIT", 110, 601)["trace_sha256"])

    def test_carry_and_oracle_flag(self):
        t = switching_trace("DEV", 54, 701)
        carry = evaluate_count_table(t)
        oracle = evaluate_count_table(t, reset_at_switch=True)
        self.assertFalse(carry["oracle_reset"])
        self.assertTrue(oracle["oracle_reset"])
        self.assertEqual(carry["phase_queries"], [128*19, 64*19, 128*19])
        self.assertEqual(oracle["phase_queries"], carry["phase_queries"])
        self.assertEqual(carry["adapt_error"], int(carry["adapt_error"]))
        self.assertTrue(all(0 <= x <= 1 for x in carry["phase_accuracy"]))
        self.assertFalse(carry["resource_qualified"])

    def test_tamper_rejected(self):
        t = switching_trace("FIT", 90, 601)
        t["records"][13]["step"] = 12
        with self.assertRaises(ValueError):
            evaluate_count_table(t)

    def test_screen_no_scientific_claim(self):
        r = development_screen("DEV", 150, 709)
        self.assertEqual(r["scientific_acceptance"], "NOT_GRANTED")
        self.assertFalse(r["reserved_test_used"])
        self.assertEqual(r["classification"], "SOURCEFREE_DEV_DIAGNOSTIC_ONLY")

if __name__ == "__main__":
    unittest.main()

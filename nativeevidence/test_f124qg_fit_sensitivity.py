"""Source-frozen F124-QG FIT-only negative-gradient diagnostic tests."""
import inspect
import unittest

import f124q_fresh_source as source
import f124q_independent_binding as learner
import f124qg_fit_sensitivity as audit


class TestF124QG(unittest.TestCase):
    def test_exact_freeze_and_unmodified_Q_source(self):
        p=audit.admission()
        self.assertEqual(audit.git_blob(audit.FREEZE),audit.FREEZE_BLOB)
        self.assertEqual(audit.git_blob(source.__file__),audit.SOURCE_BLOB)
        self.assertEqual(audit.git_blob(learner.__file__),audit.LEARNER_BLOB)
        self.assertEqual(p["analysis"]["spsa_steps"],72)
        self.assertTrue(p["analysis"]["no_DEV_evaluation"])
        self.assertTrue(p["analysis"]["no_model_source_mutation"])

    def test_lanes_fit_only_public_graph_and_no_oracle(self):
        for lane in ("Wingless","Yggdrasil"):
            pairs=learner.fit_pairs(lane)
            self.assertEqual(len(pairs),48)
            self.assertTrue(set(source.COHORTS[lane]["FIT"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))
            for pos,neg in pairs:
                self.assertEqual(set(pos),{"start","target","roles","edges"})
                self.assertTrue(source.paired_admit(pos,neg))
        src=inspect.getsource(audit.audit)
        self.assertNotIn('["DEV"]',src)
        self.assertNotIn('protected(',src)
        with self.assertRaises(source.Quarantined):
            source.protected()

    def test_failed_oracle_graph_is_quarantined(self):
        with self.assertRaises(source.Quarantined):
            source.validate_public({"oracle":True})


if __name__=="__main__":
    unittest.main()

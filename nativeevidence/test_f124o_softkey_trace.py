"""F124-O adversarial identity, no-first-use and soft causal-path invariants."""
import copy
import tempfile
from pathlib import Path
import unittest

import f124n_novel_structure_source as source
import f124o_softkey_trace as m


class F124OSourceTests(unittest.TestCase):
    def test_frozen_preimplementation_identity(self):
        protocol = m.preregistered()
        self.assertEqual(protocol["parent"]["qualified_run_id"], 39077413007)
        self.assertTrue(all(protocol["authority"].values()))
        self.assertEqual(protocol["training"]["dev_pairs_per_lane"], 48)
        self.assertNotEqual(protocol["parent"]["qualified_f124n_head"],
                            protocol["parent"]["f124m_head"])

    def test_actual_public_raw_bits_not_reference_oracle(self):
        for lane in ("Wingless", "Yggdrasil"):
            seed = next(iter(source.COHORTS[lane]["FIT"]))
            p, n = source.build(lane, seed, source.VECTORS[0], "FIT")
            for graph in (p, n):
                logit, work = m.predict(graph, 1.0, 3.0)
                self.assertIsInstance(logit, float)
                self.assertGreater(work["edge_scans"], 0)
                self.assertGreater(work["raw_bit_ops"], 0)
            with self.assertRaises(source.Quarantined):
                m.predict({**p, "oracle_label": True}, 1.0, 3.0)
            with self.assertRaises(source.Quarantined):
                m.predict(p, 0.01, 3.0)

    def test_source_identity_and_failure_quarantine(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "forged.json"
            bad.write_text('{"lanes":[]}', encoding="utf-8")
            with self.assertRaises(source.Quarantined):
                m.checked(bad, m.PARENT_N_SHA)
        with self.assertRaises((source.Quarantined, KeyError)):
            m.admission({}, {})
        with self.assertRaises(source.Quarantined):
            source.protected(lane="Wingless", seed=180100)

    def test_frozen_balanced_pretraining_cohorts(self):
        for lane in ("Wingless", "Yggdrasil"):
            for phase in ("FIT", "DEV"):
                depths = {7:0,8:0,9:0}
                cases = m.paired_cases(lane,phase)
                count = 0
                for _, _, positive, negative in cases:
                    count += 1
                    depths[len(positive["roles"])] += 1
                    self.assertTrue(source.paired_admit(positive, negative))
                self.assertEqual(count, 48)
                self.assertEqual(depths, {7:16,8:16,9:16})
            self.assertTrue(set(source.COHORTS[lane]["FIT"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))

    def test_history_not_relabelled(self):
        # A complete source check requires pinned reports, never synthetic
        # acceptance; demonstrate a counterfeited portfolio is refused.
        n = {"schema":"forge.research.f124n.authenticated-original-weight-new-structure-development.v1"}
        mdata = {"schema":"forge.research.f124m.authentic-training-optimizer-advisory.v1"}
        with self.assertRaises((KeyError, source.Quarantined)):
            m.admission(mdata,n)
        self.assertEqual(m.SCHEMA, "forge.research.f124o.softkey-trace-train-and-dev.v1")


if __name__ == "__main__":
    unittest.main()

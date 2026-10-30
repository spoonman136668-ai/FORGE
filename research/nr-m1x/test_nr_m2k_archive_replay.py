"""NR-M2K read-only original archive transport fail-closed and boundary tests.

Synthetic negative fixtures are never original-world experimental evidence.
Only the independently retrieved original owner ZIP qualifies for source replay.
"""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from nr_m2k_archive_replay import (
    _config, _process, _summarize, _byte_sha256, replay_archive, ROLE_ON, ROLE_OFF
)
from nr_m2i_decision_evidence import sha256

class NRM2KArchiveTransportTests(unittest.TestCase):
    def test_preregistered_original_archive_identity_and_non_execution(self):
        cfg = _config()
        self.assertEqual(cfg["parent"]["pr"], 1267)
        self.assertEqual(cfg["original_owner"]["artifact_id"], 12945140842)
        self.assertEqual(cfg["original_owner"]["original_episodes"], 234)
        self.assertEqual(cfg["original_owner"]["original_selected_actions"], 42755)
        self.assertEqual(cfg["expected_development_diagnostics"]["enabled_cycle_two"], 98)
        self.assertEqual(cfg["expected_development_diagnostics"]["enabled_cycle_four"], 11)
        self.assertEqual(cfg["expected_development_diagnostics"]["enabled_cycle_zero_new_exact_views_action_cost"], 134)
        self.assertTrue(all(v is False for v in cfg["no_authority"].values()))

    def test_no_archive_no_replay(self):
        with tempfile.TemporaryDirectory(prefix="nr-m2k-") as folder:
            with self.assertRaises(ValueError):
                replay_archive(Path(folder)/"absent.zip")
            path = Path(folder)/"unknown.zip"
            path.write_bytes(b"not an original artifact")
            with self.assertRaisesRegex(ValueError,"ZIP_BYTE_IDENTITY_MISMATCH"):
                replay_archive(path)

    def test_forged_small_valid_zip_still_denied_without_exact_owner_byte_sha(self):
        with tempfile.TemporaryDirectory(prefix="nr-m2k-") as folder:
            p=Path(folder)/"fake.zip"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("first.json",json.dumps({"fake":True}))
                z.writestr("second.json",json.dumps({"fake":True}))
            self.assertEqual(_byte_sha256(p),sha256(p.read_bytes()))
            with self.assertRaisesRegex(ValueError,"ZIP_BYTE_IDENTITY_MISMATCH"):
                replay_archive(p)

    def test_missing_source_owner_provenance_and_incomplete_process_fail_closed(self):
        cfg = _config()
        for doc in (None, {}, {"schema":"wrong"},
                    {"schema":"itd02.mg56.original-public-mission-symbolic-novelty-predictor.dev.v1",
                     "canonical_source_sha256":cfg["original_owner"]["source_canonical_sha256"],
                     "source":{"scientific_first_use":True}}):
            with self.subTest(doc=doc):
                with self.assertRaises(ValueError):
                    _process(doc,"first.json",cfg)

    def test_missing_original_role_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"MISSING_ORIGINAL_ROLE"):
            _summarize([])
        rows=[{
            "family":"synthetic", "seed":i, "role":ROLE_ON,
            "source_original_actions":1, "two_step_cycles":0,
            "four_step_cycles":0,"closed_cycle_action_cost":0,
            "closed_cycle_zero_new_exact_views":0,
            "closed_cycle_zero_new_symbolic_scenes":0,
            "genuine_original_goals":0
        } for i in range(9)]
        with self.assertRaisesRegex(ValueError,"MISSING_ORIGINAL_ROLE"):
            _summarize(rows)

    def test_exact_original_source_development_reference_is_not_scientific_gain(self):
        cfg=_config()
        self.assertTrue(cfg["original_owner"]["exposed_dev_only"])
        self.assertIn("not",cfg["goal"].lower())
        self.assertIn("No HTTP",__import__("nr_m2k_archive_replay").__doc__)
        self.assertEqual(cfg["expected_development_diagnostics"]["enabled_genuine_original_goals"],1)
        self.assertEqual(cfg["expected_development_diagnostics"]["disabled_genuine_original_goals"],3)

if __name__=="__main__":
    unittest.main()

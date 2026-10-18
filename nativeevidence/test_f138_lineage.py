"""Adversarial F138 lineage regressions: no inferred scientific authority."""
import hashlib
import tempfile
from pathlib import Path
import unittest

import f138_lineage as f

SHA = "03bd3673beb16352cbca2b9261e754ccf2cc6865"
BASE = {
    "repository": f.REPO,
    "ref": "refs/heads/main",
    "source_sha": SHA,
    "run_id": "39118033321",
    "run_attempt": "1",
    "event": "workflow_dispatch",
    "origin": "f137-windows-recovery",
    "parent_run_id": "39118017343",
    "parent_source_sha": SHA,
}


class LineageTests(unittest.TestCase):
    def make(self, **changes):
        row = BASE.copy()
        row.update(changes)
        return f.build(**row)

    def rejected(self, **changes):
        with self.assertRaises(f.LineageError):
            self.make(**changes)

    def test_real_windows_parent_and_no_science(self):
        r = self.make()
        self.assertEqual(r["parent_run_id"], 39118017343)
        self.assertEqual(r["origin"], "f137-windows-recovery")
        self.assertFalse(r["genuine_integrated_schedule"])
        self.assertFalse(r["scientific_first_use_authorized"])
        self.assertEqual(r["scientific_originals_dispatched"], 0)
        self.assertEqual(r["accepted_ref_mutations"], 0)
        self.assertEqual(r["optimizer_promotions"], 0)
        self.assertEqual(r["codex_calls"], 0)
        self.assertEqual(r["paid_model_calls"], 0)

    def test_genuine_schedule_is_not_relay(self):
        r = self.make(event="schedule", origin="schedule",
                      parent_run_id="", parent_source_sha="")
        self.assertTrue(r["genuine_integrated_schedule"])
        self.assertIsNone(r["parent_run_id"])
        self.assertIsNone(r["parent_source_sha"])

    def test_non_schedule_origin_cannot_forge_schedule(self):
        self.rejected(origin="schedule")
        self.rejected(event="schedule")
        self.rejected(event="push", origin="schedule",
                      parent_run_id="", parent_source_sha="")
        self.rejected(event="schedule", origin="schedule",
                      parent_run_id="39118017343", parent_source_sha=SHA)

    def test_manual_does_not_impersonate_parent(self):
        self.rejected(origin="manual")
        r = self.make(origin="manual", parent_run_id="", parent_source_sha="")
        self.assertFalse(r["genuine_integrated_schedule"])
        self.assertIsNone(r["parent_run_id"])

    def test_all_controller_origins_require_exact_parent(self):
        for origin in sorted(f.RECOVERIES):
            r = self.make(origin=origin)
            self.assertEqual(r["parent_run_id"], 39118017343)
            self.rejected(origin=origin, parent_run_id="")
            self.rejected(origin=origin, parent_source_sha="0" * 40)

    def test_reject_repository_ref_and_source_drift(self):
        self.rejected(repository="someone/FORGE")
        self.rejected(ref="refs/heads/research")
        self.rejected(source_sha="0" * 39)
        self.rejected(source_sha="A" * 40)
        self.rejected(parent_source_sha="1" * 40)

    def test_reject_bad_rerun_and_parent_identity(self):
        self.rejected(run_id="0")
        self.rejected(run_id="../../39118")
        self.rejected(run_attempt="0")
        self.rejected(run_attempt="1.0")
        self.rejected(parent_run_id="39118033321")
        self.rejected(parent_run_id="99999999999")
        self.rejected(parent_run_id="-42")

    def test_unauthorized_event_or_parent(self):
        self.rejected(event="workflow_run")
        self.rejected(origin="f137-scientific-recovery")
        self.rejected(event="pull_request", origin="pull_request",
                      ref="refs/heads/main", parent_run_id="",
                      parent_source_sha="")
        r = self.make(event="pull_request", origin="pull_request",
                      ref="refs/pull/600/merge", parent_run_id="",
                      parent_source_sha="")
        self.assertFalse(r["genuine_integrated_schedule"])

    def test_canonical_append_only_digest(self):
        r = self.make()
        data = f.encode(r)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            actual = f.write_once(root, r)
            self.assertEqual(actual, hashlib.sha256(data).hexdigest())
            self.assertEqual((root / "f138-lineage.json").read_bytes(), data)
            self.assertEqual((root / "f138-lineage.sha256").read_text(),
                             actual + "  f138-lineage.json\n")
            with self.assertRaises(f.LineageError):
                f.write_once(root, r)

    def test_digest_identical_between_independent_os_builds(self):
        self.assertEqual(f.encode(self.make()), f.encode(self.make()))

    def test_regression_contract_is_only_a_witness_not_authority(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows" /
                    "forge-integrated-synthetic-cycle.yml").read_text()
        self.assertIn("Capture F138 source-bound development lineage", workflow)
        self.assertIn("forge-f138-lineage-", workflow)
        self.assertIn("F138_DUAL_OS_LINEAGE_VERIFIED", workflow)
        self.assertIn("retention-days: 90", workflow)
        self.assertIn("github.event_name == 'schedule'", workflow)
        self.assertIn("f137-windows-recovery", workflow)


if __name__ == "__main__":
    unittest.main()

"""Persistent-file CKAD custody negative tests; no trainer or model invoked."""
from __future__ import annotations
from pathlib import Path
import tempfile
import unittest

from f139.ckad_campaign_request import CampaignDenied, next_stage
from f139.ckad_native_stage_artifact import inspect_native_checkpoint, inspect_persisted_stage
from f139.ckad_stage_custody import canonical, digest, receipt_digest
from f139.test_ckad_campaign_request import campaign


def native(n=0):
    # STRUCTURAL fixture, not an actual qualified native cold-restore image.
    return canonical({"schema": "yggdrasil.ckad.native-cumulative-learner.v1",
                      "source_mode": "engineering_fixture_only",
                      "properties_ascii": '{"fixture":1}', "source_ascii": '{"fixture":2}',
                      "hypotheses_ascii": [None]*16, "quarantined": [False]*16,
                      "events": ([{"test_only": n}] if n else []),
                      "accepted_native": False, "scientific_pass": False})


class NativeStageArtifactTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.c = campaign(native())
        self.proposal = next_stage(self.c, [])["next_stage"]
        self.names = {"input_file": "input.native.json", "output_file": "output.native.json",
                      "evidence_file": "evidence.json", "control_file": "control.json",
                      "evaluation_file": "evaluation.json"}
        for name, raw in {"input.native.json": native(),
                          "output.native.json": native(1),
                          "evidence.json": b'{"observed":1}',
                          "control.json": b'{"control":1}',
                          "evaluation.json": b'{"held":1}'}.items():
            (self.root / name).write_bytes(raw)

    def audit(self, **overrides):
        args = dict(campaign=self.c, receipts=[], stage_proposal=self.proposal,
                    root=self.root, observations=1, interventions=0, cpu_seconds=1,
                    **self.names)
        args.update(overrides)
        return inspect_persisted_stage(**args)

    def test_actual_files_source_bound_and_not_execution_proof(self):
        doc = self.audit()
        self.assertEqual(doc["files_read"], 5)
        self.assertEqual(doc["receipt"]["input_checkpoint_sha256"], digest(native()))
        self.assertEqual(doc["receipt"]["output_checkpoint_sha256"], digest(native(1)))
        for flag in ("source_owner_run_authenticated", "native_cold_restore_verified",
                     "stage_executed_by_forge", "training_execution_authorized",
                     "scientific_pass", "promotion_authorized", "new_controller"):
            self.assertFalse(doc[flag])

    def test_invalid_noncanonical_and_unauthorized_checkpoint_rejected(self):
        for raw in (b"arbitrary-bytes", b'{"hello":"world"}',
                    b'{"schema":"v1","schema":"v1"}', b'{"x":NaN}',
                    native().replace(b'"accepted_native":false', b'"accepted_native":true'),
                    native().replace(b'"scientific_pass":false', b'"scientific_pass":true'),
                    native().replace(b',"events":', b', "events":'),
                    native().replace(b'.v1"', b'.v9"')):
            with self.subTest(raw=raw[:32]), self.assertRaises(CampaignDenied):
                inspect_native_checkpoint(raw)

    def test_proposal_replay_wrong_persisted_input_and_missing_receipt_pin(self):
        with self.assertRaises(CampaignDenied):
            self.audit(stage_proposal=dict(self.proposal, stage_index=1))
        (self.root / "input.native.json").write_bytes(native(3))
        with self.assertRaises(CampaignDenied):
            self.audit()
        (self.root / "input.native.json").write_bytes(native())
        first = self.audit()["receipt"]
        nxt = next_stage(self.c, [first], independently_pinned_head=receipt_digest(first))
        (self.root / "input.native.json").write_bytes(native(1))
        (self.root / "output.native.json").write_bytes(native(2))
        with self.assertRaises(CampaignDenied):
            self.audit(receipts=[first], stage_proposal=nxt["next_stage"])

    def test_regular_artifact_only_and_no_aliases(self):
        (self.root / "control.json").unlink()
        with self.assertRaises(CampaignDenied):
            self.audit()
        (self.root / "control.json").write_bytes(b"ok")
        with self.assertRaises(CampaignDenied):
            self.audit(input_file="../input.native.json")
        with self.assertRaises(CampaignDenied):
            self.audit(input_file="output.native.json")
        try:
            (self.root / "link.json").symlink_to(self.root / "output.native.json")
        except (OSError, NotImplementedError):
            pass
        else:
            with self.assertRaises(CampaignDenied):
                self.audit(output_file="link.json")

    def test_frozen_budgets_and_reported_usage(self):
        with self.assertRaises(CampaignDenied):
            self.audit(observations=1000)
        with self.assertRaises(CampaignDenied):
            self.audit(cpu_seconds=1000)


if __name__ == "__main__":
    unittest.main()

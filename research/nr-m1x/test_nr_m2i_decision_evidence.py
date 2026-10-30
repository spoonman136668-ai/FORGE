"""NR-M2I source-only witness falsifiers; NEVER runs an original environment."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from nr_m2d_pinned_original_public import MISSION
from nr_m2e_extended_public import full_public
from nr_m2i_decision_evidence import (
    DecisionEvidenceLedger, SCHEMA, canonical, sha256, source_public_digest,
)

CONTRACT = Path(__file__).with_name("NR_M2I_PREREG.json")
PARENT_SHA = "04f13074a6c115cd4e0b33741f84d41c7a10254c"

def public_fixture():
    public = {"image": [[[1, 0, 0] for _ in range(7)] for _ in range(7)],
              "direction": 0, "mission": MISSION}
    return full_public(public)

def decision_fixture(reason="PARENT", selected=0, parent=0, selected_n=0,
                     selected_credit=0, exploration=0):
    before = public_fixture()
    after = copy.deepcopy(before)
    after["image"][1][2] = [2, 4, 0]
    after = full_public(after)
    counts = [0] * 7
    masses = [0.0] * 7
    counts[selected] = selected_n
    masses[selected] = selected_credit
    event = {
        "source_before_sha256": source_public_digest(before),
        "source_policy_sha1": PARENT_SHA,
        "parent_action": parent,
        "selected_action": selected,
        "allowed_actions": list(range(7)),
        "context_digest": sha256(canonical([MISSION, 1, 2])),
        "selected_before_feedback_counts": counts,
        "selected_before_goal_effect_mass": masses,
        "explicit_exploration_budget_spent": exploration,
        "selected_action_reason": reason,
        "event_sequence": 1,
        "episode_id": "SOURCE_ONLY_TEST_NOT_ORIGINAL_WORLD",
        "after_sha256": source_public_digest(after),
        "real_reward": 0.0,
        "terminated": False,
        "truncated": False,
    }
    return event, before, after

class NRM2IProspectiveEvidence(unittest.TestCase):
    def test_frozen_contract_before_source_and_original_custody(self):
        c = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(c["schema"], "forge.nr-m2i.prospective-selected-decision-evidence.v1")
        self.assertEqual(c["prospective_only"]["event_schema"], SCHEMA)
        self.assertEqual(c["source_custody"]["qualified_nr_m2h_head"],
                         "f85b57c055ca900abd353a0094da7c05a4958429")
        self.assertEqual(c["source_custody"]["original_owner_policy_blob"],
                         "6ead3934b56a5ba502ffdab8481d96c18ac5bf8f")
        self.assertEqual(c["source_custody"]["original_event_artifact_id"], 12945140842)
        self.assertEqual(c["source_custody"]["original_action_count"], 422)
        self.assertFalse(any(c["prohibitions"].values()))
        self.assertIn("source_before_sha256", c["prospective_only"]["required_fields"])
        self.assertIn("parent_action", c["prospective_only"]["required_fields"])
        self.assertIn("selected_action", c["prospective_only"]["required_fields"])

    def test_parent_stays_parent_without_override(self):
        e, b, y = decision_fixture()
        ledger = DecisionEvidenceLedger()
        raw, digest = ledger.record(e, b, y)
        receipt = json.loads(raw)
        self.assertEqual(receipt["evidence_class"], "UNCHANGED_PARENT")
        self.assertEqual(receipt["parent_source_attestation"],
                         "UNVERIFIED_BY_SOURCE_ONLY_MODULE")
        self.assertFalse(receipt["source_original_world_execution"])
        self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
        self.assertEqual(ledger.receipts, 1)

    def test_evidence_and_exploration_are_separate(self):
        for reason, n, mass, budget, expected in [
            ("GOAL_EVIDENCE", 4, 3, 0, "TRIED_WITH_ENGINEERED_GOAL_EVIDENCE"),
            ("EXPLICIT_EXPLORATION", 0, 0, 1, "UNTRIED_NO_GOAL_EVIDENCE"),
            ("EXPLICIT_EXPLORATION", 2, 0, 1, "TRIED_NO_GOAL_EVIDENCE"),
        ]:
            with self.subTest(reason=reason, n=n, mass=mass):
                e, b, y = decision_fixture(reason, 1, 0, n, mass, budget)
                raw, _ = DecisionEvidenceLedger().record(e, b, y)
                self.assertEqual(json.loads(raw)["evidence_class"], expected)
                self.assertEqual(json.loads(raw)["decision"]["real_reward"], 0.0)

    def test_missing_parent_and_unselected_rights_fail_closed(self):
        good, before, after = decision_fixture()
        for mutant in (
            lambda e: e.pop("parent_action"),
            lambda e: e.update({"parent_action": True}),
            lambda e: e.update({"selected_action": 7}),
            lambda e: e.update({"allowed_actions": [0, 1, 1]}),
            lambda e: e.update({"source_policy_sha1": "00"}),
            lambda e: e.update({"context_digest": "f00"}),
            lambda e: e.update({"source_before_sha256": "0" * 64}),
            lambda e: e.update({"after_sha256": "0" * 64}),
            lambda e: e.update({"event_sequence": True}),
            lambda e: e.update({"event_sequence": 2}),
            lambda e: e.update({"selected_before_feedback_counts": [0] * 8}),
            lambda e: e.update({"selected_before_goal_effect_mass": [0] * 8}),
            lambda e: e.update({"selected_before_feedback_counts": [-1] + [0]*6}),
            lambda e: e.update({"selected_before_goal_effect_mass": [1] + [0]*6}),
            lambda e: e.update({"real_reward": float("nan")}),
            lambda e: e.update({"real_reward": True}),
            lambda e: e.update({"terminated": True, "truncated": True}),
            lambda e: e.update({"selected_action_reason": "EVIDENCE"}),
            lambda e: e.update({"extra_hidden_state": 1}),
        ):
            with self.subTest(mutant=mutant):
                e = copy.deepcopy(good)
                mutant(e)
                with self.assertRaises(ValueError):
                    DecisionEvidenceLedger().record(e, before, after)

    def test_intent_cannot_be_relabelled_as_learnt_goal_support(self):
        for reason, n, mass, spent in [
            ("GOAL_EVIDENCE", 0, 0, 0),
            ("GOAL_EVIDENCE", 3, 0, 0),
            ("EXPLICIT_EXPLORATION", 0, 0, 0),
            ("PARENT", 0, 0, 0),
        ]:
            e, b, y = decision_fixture(reason, 1, 0, n, mass, spent)
            with self.assertRaises(ValueError):
                DecisionEvidenceLedger().record(e, b, y)
        e, b, y = decision_fixture("GOAL_EVIDENCE", 1, 0, 2, 1, 0)
        raw, _ = DecisionEvidenceLedger().record(e, b, y)
        self.assertEqual(json.loads(raw)["decision"]["real_reward"], 0.0)
        # Engineered public goal-event credit is not genuine terminal reward.
        self.assertFalse(json.loads(raw)["decision"]["terminated"])

    def test_sequential_link_cold_process_restore_and_tamper(self):
        ledger = DecisionEvidenceLedger()
        e, b, y = decision_fixture()
        first, digest = ledger.record(e, b, y)
        e["event_sequence"] = 2
        second, digest2 = ledger.record(e, b, y)
        self.assertEqual(json.loads(second)["previous_receipt_sha256"], digest)
        self.assertEqual(ledger.next_sequence, 3)
        checkpoint = ledger.checkpoint()
        restored = DecisionEvidenceLedger.restore(checkpoint, sha256(checkpoint))
        self.assertEqual(restored.checkpoint(), checkpoint)
        with self.assertRaises(ValueError):
            DecisionEvidenceLedger.restore(checkpoint + b" ", sha256(checkpoint))
        with self.assertRaises(ValueError):
            DecisionEvidenceLedger.restore(checkpoint + b" ", sha256(checkpoint+b" "))
        with tempfile.TemporaryDirectory(prefix="nr-m2i-") as tmp:
            p = Path(tmp) / "witness-cold.json"
            p.write_bytes(checkpoint)
            program = (
                "import pathlib,sys;"
                "from nr_m2i_decision_evidence import DecisionEvidenceLedger,sha256;"
                "raw=pathlib.Path(sys.argv[1]).read_bytes();"
                "x=DecisionEvidenceLedger.restore(raw,sys.argv[2]);"
                "assert x.next_sequence==3 and x.checkpoint()==raw"
            )
            finished = subprocess.run(
                [sys.executable, "-B", "-c", program, str(p), sha256(checkpoint)],
                cwd=str(Path(__file__).parent),
                capture_output=True, text=True, timeout=35,
            )
            self.assertEqual(finished.returncode, 0, finished.stdout+finished.stderr)

if __name__ == "__main__":
    unittest.main()

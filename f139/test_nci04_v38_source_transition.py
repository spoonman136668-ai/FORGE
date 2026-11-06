"""V38 diagnostic-source successor: frozen negative and fail-closed tests.

Synthetic fixtures do not authorize a live owner installation.
"""
import inspect
import unittest
from unittest.mock import patch

from f139 import nci04_v37_source_transition as predecessor
from f139 import nci04_v38_source_transition as contract
from f139 import nci04_v38_original_owner_transition_cli as cli
from f139 import nci04_v32_original_owner_transition_cli as shared
from f139.local_controller import Database


class V38SuccessorTests(unittest.TestCase):
    def previous(self):
        return [{"schema": predecessor.SCHEMA,
                 "from_source_sha": predecessor.FROM_V36,
                 "to_source_sha": contract.FROM_V37}]

    def proof(self):
        from f139.test_nci04_v37_source_transition import proof as v37_proof
        document = v37_proof(1241)
        document["schema"] = contract.SCHEMA
        document["from_source_sha"] = contract.FROM_V37
        document["to_source_sha"] = "e" * 40
        document["original_head_seq"] = 1241
        document["v37_transition_sha256"] = document.pop("v36_transition_sha256")
        document["purpose"] = "terminal-read-diagnostics"
        return document

    def test_schema_is_new_and_bound_to_exact_original_v37(self):
        self.assertEqual(contract.SCHEMA, "forge.f139.source-transition.v33")
        self.assertEqual(contract.FROM_V37,
                         "3dd63467d649a347692b6b42cd5074ff1038d3de")
        self.assertEqual(cli.contract, contract)
        self.assertIn("v38", inspect.getsource(shared.guarded_transition))
        self.assertNotEqual(contract.FIELDS, predecessor.FIELDS)

    def test_cold_proof_requires_purpose_and_immutable_negative_custody(self):
        doc = self.proof()
        row = {"seq": 1242, "prior_sha": doc["prior_event_head_sha256"]}
        from f139.nci04_native_contract import canonical
        state_keys = (
            "verified_historical_tasks", "custodied_negative_tasks",
            "custodied_negative_tickets", "terminal_tasks_sha256",
            "history_sha256", "v37_transition_sha256",
            "preserved_counters", "i1464_negative_event_sha256",
            "i1464_original_receipt_sha256", "partial_publication_custody")
        with patch.object(contract, "snapshot",
                          return_value={k: doc[k] for k in state_keys}):
            contract.verify_cold_event(None, row, doc, self.previous())
            for delta in (
                {"purpose": "model-execution"},
                {"schema": predecessor.SCHEMA},
                {"from_source_sha": predecessor.FROM_V36},
                {"to_source_sha": contract.FROM_V37},
                {"original_head_seq": 1240},
                {"original_head_seq": True},
                {"scientific_first_use": True},
                {"new_dispatches": 1},
                {"v2_receipt_authorized": True},
                {"preserved_counters": {}},
                {"i1464_negative_event_sha256": "0" * 64},
                {"partial_publication_custody": {}},
                {"v37_transition_sha256": "0" * 64},
                {"extra": True},
            ):
                with self.subTest(delta=delta), self.assertRaises(
                        contract.MaintenanceDenied):
                    contract.verify_cold_event(
                        None, row, {**doc, **delta}, self.previous())
            for chain in ([], self.previous() + [self.previous()[-1]],
                          [{"schema": "forge.f139.source-transition.v31",
                            "to_source_sha": contract.FROM_V37}]):
                with self.subTest(chain=chain), self.assertRaises(
                        contract.MaintenanceDenied):
                    contract.verify_cold_event(None, row, doc, chain)

    def test_spent_counters_preserve_the_single_original_partial_attempt(self):
        base = dict(G3_DRAFT_ATTEMPTED=1, G3_DRAFT_AUTHENTICATED=1,
                    FREE_REASONER_ATTEMPTED=8, MODEL_DRAFT_ATTEMPTED=102,
                    MODEL_DRAFT_AUTHENTICATED=101)
        self.assertTrue(contract.preserved_counters_valid(base))
        self.assertTrue(contract.preserved_counters_valid({
            **base, "MODEL_DRAFT_ATTEMPTED": 105,
            "MODEL_DRAFT_AUTHENTICATED": 104}))
        for delta in (
            {"MODEL_DRAFT_ATTEMPTED": 101},
            {"MODEL_DRAFT_ATTEMPTED": 103},
            {"MODEL_DRAFT_AUTHENTICATED": 102},
            {"FREE_REASONER_ATTEMPTED": 7},
            {"G3_DRAFT_ATTEMPTED": True},
            {"unknown": 1},
        ):
            with self.subTest(delta=delta):
                self.assertFalse(contract.preserved_counters_valid({
                    **base, **delta}))

    def test_no_write_or_read_without_original_custody(self):
        with self.assertRaises(contract.MaintenanceDenied):
            contract.build_proof(None, "e" * 40, 1, "a" * 64,
                                 contract.TOOLCHAIN)
        with self.assertRaises(contract.MaintenanceDenied):
            contract.readonly_snapshot(None)
        with self.assertRaises(contract.MaintenanceDenied):
            contract.commit_transition(None, {}, owner_witness=lambda: True)


if __name__ == "__main__":
    unittest.main()

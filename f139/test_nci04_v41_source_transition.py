"""Inactive V41 v36 transition schema and negative guard qualification."""
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139 import nci04_v41_source_transition as route
from f139.local_controller import Database, SingleOwner


class V41TransitionContractTests(unittest.TestCase):
    def document(self):
        return {
            **{key: None for key in route.FIELDS},
            "schema": route.SCHEMA,
            "from_source_sha": route.FROM_V40,
            "to_source_sha": "f"*40,
            "owner_event_id": 807,
            "prior_event_head_sha256": "a"*64,
            "original_head_seq": route.MIN_HEAD,
            "frozen_observed_seq": route.MIN_HEAD,
            "frozen_observed_head_sha256": route.preflight.OBSERVED_HEAD,
            "verified_historical_tasks": 153,
            "custodied_negative_tasks": 56,
            "custodied_negative_tickets": [],
            "terminal_tasks_sha256": "b"*64,
            "history_sha256": "c"*64,
            "v40_transition_sha256": "d"*64,
            "preserved_counters": {
                "G3_DRAFT_ATTEMPTED":1, "G3_DRAFT_AUTHENTICATED":1,
                "MODEL_DRAFT_ATTEMPTED":168,
                "MODEL_DRAFT_AUTHENTICATED":166,
                "FREE_REASONER_ATTEMPTED":8},
            "negative_1239_sha256": route.partial.EVENT,
            "negative_1462_sha256": route.ref_only.EVENT,
            "genenv_executable_sha256": "e"*64,
            "genenv_toolchain": route.TOOLCHAIN,
            "generation_mechanism_sha256": "f"*64,
            "qualified_worker_blob": route.QUALIFIED_WORKER_BLOB,
            "qualifying_catalog_repair_sha": route.REPAIR_MERGE,
            "source_lanes": ["Wingless", "Yggdrasil"],
            "purpose": route.PURPOSE,
            "new_dispatches": 0,
            "scientific_first_use": False,
            "v2_receipt_authorized": False,
            "hybrid_admission": False,
        }

    def test_exact_v36_schema_accepts_only_frozen_cold_state(self):
        doc = self.document()
        row = {"seq": route.MIN_HEAD+1, "prior_sha":"a"*64}
        with patch.object(route, "snapshot", return_value={
                key: doc[key] for key in (
                    "frozen_observed_seq","frozen_observed_head_sha256",
                    "verified_historical_tasks","custodied_negative_tasks",
                    "custodied_negative_tickets","terminal_tasks_sha256",
                    "history_sha256","v40_transition_sha256",
                    "preserved_counters","negative_1239_sha256",
                    "negative_1462_sha256")}):
            route.verify_cold_event(None,row,doc,[dict(schema=route.v40.SCHEMA)])
        # This verifies field grammar, not authentic SQLite. Genuine cold
        # source-history tests remain a separate unfulfilled release gate.

    def test_mutation_approval_science_hybrid_and_replay_are_denied(self):
        doc = self.document()
        row = {"seq":route.MIN_HEAD+1,"prior_sha":"a"*64}
        mutations = [
            {"schema":"different"}, {"from_source_sha":"0"*40},
            {"to_source_sha":route.FROM_V40}, {"to_source_sha":"unbound"},
            {"owner_event_id":True}, {"owner_event_id":0},
            {"original_head_seq":route.MIN_HEAD+1},
            {"prior_event_head_sha256":"0"*64},
            {"qualifying_catalog_repair_sha":"0"*40},
            {"qualified_worker_blob":"0"*40}, {"source_lanes":["Hybrid"]},
            {"purpose":"enable-training"}, {"genenv_toolchain":"wrong"},
            {"genenv_executable_sha256":"bad"},
            {"generation_mechanism_sha256":"bad"},
            {"new_dispatches":1}, {"new_dispatches":True},
            {"scientific_first_use":True}, {"v2_receipt_authorized":True},
            {"hybrid_admission":True}, {"extra":False},
        ]
        for change in mutations:
            with self.subTest(change=change), self.assertRaises(route.V41TransitionDenied):
                route.verify_cold_event(None,row,{**doc,**change},[])
        with self.assertRaises(route.V41TransitionDenied):
            route.verify_cold_event(None,row,doc,[dict(schema=route.SCHEMA)])

    def test_no_unguarded_live_write_or_source_transition_method(self):
        self.assertFalse(hasattr(route,"commit_transition"))
        self.assertFalse(hasattr(route,"guarded_transition"))
        self.assertFalse(hasattr(route,"main"))
        self.assertFalse(hasattr(route,"run_once"))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"state.sqlite"
            with closing(Database.initialize(path,route.FROM_V40)) as owner:
                before=owner.meta().copy()
                with self.assertRaises(route.V41TransitionDenied):
                    route.build_proof(owner, "f"*40, 807, "a"*64, route.TOOLCHAIN)
                self.assertEqual(owner.meta(),before)
            with closing(Database.open_readonly(path)) as readonly:
                with SingleOwner(path.with_suffix(".lock")):
                    with self.assertRaises(route.V41TransitionDenied):
                        route.build_proof(readonly,"f"*40,807,"a"*64,route.TOOLCHAIN)
                self.assertEqual(readonly.meta(),before)

    def test_wrong_v40_seal_without_sqlite_is_denied(self):
        with self.assertRaises(route.V41TransitionDenied):
            route.snapshot(None,{"seq":route.MIN_HEAD+1,"prior_sha":"a"*64},[])

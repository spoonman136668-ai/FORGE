#!/usr/bin/env python3
"""TW3 original-source-shaped action exposure falsification: DEV ONLY."""
import unittest

from tw3_dev_movement_proposal import (
    RECEIPT, RESULT, redact_original_result, source_authority, validate_proposal,
)


def proposal():
    return {"actor": "npc:0", "destination": "location:1"}


def allow(x=None, **opts):
    args = {
        "scoped_actor": "npc:0",
        "public_destinations": frozenset(("location:0", "location:1")),
        "action_budget_remaining": 3,
        "already_in_flight": False,
    }
    args.update(opts)
    return validate_proposal(proposal() if x is None else x, **args)


class TW3FailClosedActions(unittest.TestCase):
    def reject(self, reason, act):
        with self.assertRaisesRegex(ValueError, reason):
            act()

    def test_01_proposal_only_dev_validated(self):
        r = allow()
        self.assertEqual(r["status"], RESULT)
        self.assertFalse(r["source_executed"])
        self.assertFalse(r["fsa_first_use_admitted"])

    def test_02_action_cost_is_one_even_if_only_proposal(self):
        self.assertTrue(allow()["costs_one_action_slot"])

    def test_03_action_fields_exact(self):
        self.assertEqual(set(proposal()), {"actor", "destination"})

    def test_04_no_route_field(self):
        bad = dict(proposal(), route=["location:999"])
        self.reject("EXACT_REQUEST_FIELDS", lambda: allow(bad))

    def test_05_no_cost_field(self):
        bad = dict(proposal(), cost=12)
        self.reject("EXACT_REQUEST_FIELDS", lambda: allow(bad))

    def test_06_no_future_arrival_time(self):
        bad = dict(proposal(), arrivesAt=333)
        self.reject("EXACT_REQUEST_FIELDS", lambda: allow(bad))

    def test_07_no_world_seed(self):
        bad = dict(proposal(), seed="original-secret")
        self.reject("EXACT_REQUEST_FIELDS", lambda: allow(bad))

    def test_08_no_scientific_permission_self_claim(self):
        bad = dict(proposal(), fsa_pass=True)
        self.reject("EXACT_REQUEST_FIELDS", lambda: allow(bad))

    def test_09_reject_other_actor(self):
        self.reject("ACTOR_CUSTODY", lambda: allow(
            {"actor": "npc:1", "destination": "location:1"}))

    def test_10_reject_missing_actor(self):
        self.reject("EXACT_REQUEST_FIELDS", lambda: allow(
            {"destination": "location:1"}))

    def test_11_reject_unknown_dest(self):
        self.reject("DESTINATION_NOT_PUBLIC", lambda: allow(
            {"actor": "npc:0", "destination": "location:999"}))

    def test_12_reject_no_catalog(self):
        self.reject("PUBLIC_CATALOG_SHAPE", lambda: allow(
            public_destinations=frozenset()))

    def test_13_reject_mutable_catalog(self):
        self.reject("PUBLIC_CATALOG_SHAPE", lambda: allow(
            public_destinations={"location:1"}))

    def test_14_reject_catalog_with_private_marker(self):
        self.reject("PUBLIC_CATALOG_SHAPE", lambda: allow(
            public_destinations=frozenset(("location:1", "secret-target"))))

    def test_15_reject_zero_remaining_actions(self):
        self.reject("FINITE_ACTION_BUDGET", lambda: allow(action_budget_remaining=0))

    def test_16_reject_negative_remaining_actions(self):
        self.reject("FINITE_ACTION_BUDGET", lambda: allow(action_budget_remaining=-1))

    def test_17_reject_boolean_budget(self):
        self.reject("FINITE_ACTION_BUDGET", lambda: allow(action_budget_remaining=True))

    def test_18_reject_unbounded_budget(self):
        self.reject("FINITE_ACTION_BUDGET", lambda: allow(action_budget_remaining=101))

    def test_19_allow_last_budget_slot(self):
        self.assertEqual(allow(action_budget_remaining=1)["status"], RESULT)

    def test_20_reject_inflight_second_action(self):
        self.reject("IN_FLIGHT_OR_UNKNOWN", lambda: allow(already_in_flight=True))

    def test_21_reject_missing_flight_certificate(self):
        self.reject("IN_FLIGHT_OR_UNKNOWN", lambda: allow(already_in_flight=None))

    def test_22_reject_untrusted_scoped_actor(self):
        self.reject("SCOPED_ACTOR", lambda: allow(scoped_actor=""))

    def test_23_reject_malformed_destination(self):
        self.reject("DESTINATION_FORMAT", lambda: allow(
            {"actor":"npc:0","destination":"../../owner_secret"}))

    def test_24_reject_nested_destination(self):
        self.reject("DESTINATION_FORMAT", lambda: allow(
            {"actor":"npc:0","destination":{"id":"location:1"}}))

    def test_25_never_expose_journey_path_or_future_time(self):
        raw = {"started":True,"journey":{
            "path":["location:0","location:222","location:1"],
            "leg":0,"startedAt":5,"legArrivesAt":17,
            "totalCost":10000,"arrival":599,
            "seed":"SECRET_SEED"
        }}
        x = redact_original_result(raw)
        self.assertEqual(x["status"], RECEIPT)
        self.assertNotIn("location:222", str(x))
        self.assertNotIn("10000", str(x))
        self.assertNotIn("SECRET", str(x))

    def test_26_blocked_raw_reason_and_details_not_exposed(self):
        raw = {"started":False,"reason":"full","details":{
            "capacity":1,"occupancy":1,"from":"location:999"}}
        x = redact_original_result(raw)
        self.assertNotIn("full", str(x))
        self.assertNotIn("location:999", str(x))
        self.assertEqual(x["revealed_private_fields"], 0)

    def test_27_started_blocked_and_already_there_same_receipt(self):
        started={"started":True,"journey":{"path":["location:999"],"arrival":333}}
        blocked={"started":False,"reason":"forbidden","details":{"to":"location:999"}}
        same={"started":False,"reason":"already-there"}
        self.assertEqual(redact_original_result(started),redact_original_result(blocked))
        self.assertEqual(redact_original_result(same),redact_original_result(blocked))

    def test_28_reject_raw_result_missing_started(self):
        self.reject("SOURCE_RESULT_STARTED", lambda: redact_original_result(
            {"reason":"full","details":{}}))

    def test_29_reject_boolean_as_dictionary(self):
        self.reject("SOURCE_RESULT_SHAPE", lambda: redact_original_result(True))

    def test_30_no_caller_self_attested_source_authority(self):
        s=source_authority()
        self.assertTrue(s["original_workflow_tests_passed"])
        self.assertFalse(s["source_owner_public_destination_catalog"])
        self.assertFalse(s["independent_learner_action_custody"])
        self.assertFalse(s["fsa_admission"])
        self.assertFalse(s["science_go"])

    def test_31_allowed_catalog_is_not_qualified_real_world(self):
        s=allow()
        self.assertFalse(s["source_owner_catalog_authenticated"])

    def test_32_reject_false_activator_actor_id(self):
        self.reject("SCOPED_ACTOR",lambda:allow(scoped_actor="admin/root"))

    def test_33_valid_home_destination_under_same_development_budget(self):
        r=allow({"actor":"npc:0","destination":"location:0"})
        self.assertEqual(r["destination"],"location:0")

    def test_34_canonical_original_entity_ids(self):
        r=allow({"actor":"npc:0","destination":"location:1"})
        self.assertEqual(r["status"],RESULT)
        self.assertFalse(r["source_owner_catalog_authenticated"])

    def test_35_old_synthetic_names_are_not_original_ids(self):
        self.reject("SCOPED_ACTOR",lambda:allow(scoped_actor="npc:ada"))
        self.reject("PUBLIC_CATALOG_SHAPE",lambda:allow(public_destinations=frozenset(("loc:market",))))
        self.reject("DESTINATION_FORMAT",lambda:allow({"actor":"npc:0","destination":"loc:market"}))

    def test_36_reject_noncanonical_or_overflow_npc(self):
        for invalid in ("npc:01","npc:-1","npc:abc","npc:9007199254740992","npc:999999999999999999999999"):
            with self.subTest(invalid=invalid):
                self.reject("SCOPED_ACTOR",lambda:allow(scoped_actor=invalid))

    def test_37_reject_noncanonical_or_overflow_location(self):
        for invalid in ("location:01","location:-1","location:market","location:9007199254740992","location:999999999999999999999999"):
            with self.subTest(invalid=invalid):
                self.reject("DESTINATION_FORMAT",lambda:allow({"actor":"npc:0","destination":invalid}))

    def test_38_valid_syntax_not_same_as_public_catalog_permission(self):
        self.reject("DESTINATION_NOT_PUBLIC",lambda:allow({"actor":"npc:0","destination":"location:2"}))
        self.assertFalse(allow()["fsa_first_use_admitted"])

    def test_39_max_original_safe_entity_index(self):
        r=allow({"actor":"npc:9007199254740991","destination":"location:9007199254740991"},
                scoped_actor="npc:9007199254740991",
                public_destinations=frozenset(("location:9007199254740991",)))
        self.assertEqual(r["status"],RESULT)

    def test_40_pure_dev_check_does_not_consume_authoritative_budget(self):
        a=allow(action_budget_remaining=2)
        b=allow(action_budget_remaining=2)
        self.assertEqual(a,b)
        self.assertFalse(a["source_executed"])
        self.assertFalse(source_authority()["independent_learner_action_custody"])


if __name__ == "__main__":
    unittest.main()

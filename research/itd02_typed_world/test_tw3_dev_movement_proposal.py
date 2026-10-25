#!/usr/bin/env python3
"""TW3 original-source-shaped action exposure falsification: DEV ONLY."""
import unittest

from tw3_dev_movement_proposal import (
    RECEIPT, RESULT, redact_original_result, source_authority, validate_proposal,
)


def proposal():
    return {"actor": "npc:ada", "destination": "loc:market"}


def allow(x=None, **opts):
    args = {
        "scoped_actor": "npc:ada",
        "public_destinations": frozenset(("loc:home", "loc:market")),
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
        bad = dict(proposal(), route=["loc:secret"])
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
            {"actor": "npc:ben", "destination": "loc:market"}))

    def test_10_reject_missing_actor(self):
        self.reject("EXACT_REQUEST_FIELDS", lambda: allow(
            {"destination": "loc:market"}))

    def test_11_reject_unknown_dest(self):
        self.reject("DESTINATION_NOT_PUBLIC", lambda: allow(
            {"actor": "npc:ada", "destination": "loc:secret"}))

    def test_12_reject_no_catalog(self):
        self.reject("PUBLIC_CATALOG_SHAPE", lambda: allow(
            public_destinations=frozenset()))

    def test_13_reject_mutable_catalog(self):
        self.reject("PUBLIC_CATALOG_SHAPE", lambda: allow(
            public_destinations={"loc:market"}))

    def test_14_reject_catalog_with_private_marker(self):
        self.reject("PUBLIC_CATALOG_SHAPE", lambda: allow(
            public_destinations=frozenset(("loc:market", "secret-target"))))

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
            {"actor":"npc:ada","destination":"../../owner_secret"}))

    def test_24_reject_nested_destination(self):
        self.reject("DESTINATION_FORMAT", lambda: allow(
            {"actor":"npc:ada","destination":{"id":"loc:market"}}))

    def test_25_never_expose_journey_path_or_future_time(self):
        raw = {"started":True,"journey":{
            "path":["loc:home","loc:private","loc:market"],
            "leg":0,"startedAt":5,"legArrivesAt":17,
            "totalCost":10000,"arrival":599,
            "seed":"SECRET_SEED"
        }}
        x = redact_original_result(raw)
        self.assertEqual(x["status"], RECEIPT)
        self.assertNotIn("loc:private", str(x))
        self.assertNotIn("10000", str(x))
        self.assertNotIn("SECRET", str(x))

    def test_26_blocked_raw_reason_and_details_not_exposed(self):
        raw = {"started":False,"reason":"full","details":{
            "capacity":1,"occupancy":1,"from":"loc:secret"}}
        x = redact_original_result(raw)
        self.assertNotIn("full", str(x))
        self.assertNotIn("loc:secret", str(x))
        self.assertEqual(x["revealed_private_fields"], 0)

    def test_27_started_blocked_and_already_there_same_receipt(self):
        started={"started":True,"journey":{"path":["loc:secret"],"arrival":333}}
        blocked={"started":False,"reason":"forbidden","details":{"to":"loc:secret"}}
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
        r=allow({"actor":"npc:ada","destination":"loc:home"})
        self.assertEqual(r["destination"],"loc:home")


if __name__ == "__main__":
    unittest.main()

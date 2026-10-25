#!/usr/bin/env python3
"""TW2 open handcrafted development event-filter adversarial tests only."""
import unittest

from tw2_dev_travel_projection import (
    project_event, original_science_authority, CENSUS,
)


def original(t="travel.departed"):
    return {
        "id": 7,
        "tick": 20,
        "type": t,
        "actors": ["npc:ada"],
        "location": "loc:home",
        "data": {
            "traveller": "npc:ada",
            "from": "loc:home",
            "to": "loc:unknown-next-node",
            "destination": "loc:SECRET_FUTURE_DESTINATION",
            "cost": 99,
            "arrivesAt": 999,
            "at": "loc:market",
            "final": True,
            "travelled": 999,
            "reason": "forbidden",
            "capacity": 123,
            "permitted": ["npc:secret"],
            "seed": "SECRET_GENERATION_SEED",
            "full_path": ["loc:private"],
        },
        "causes": [182, 183, "SECRET_CAUSE_CHAIN"],
    }


class TW2PublicDevelopmentProjectionTests(unittest.TestCase):
    def project(self, e=None, actor="npc:ada", cursor=(0, 0)):
        return project_event(original() if e is None else e, actor, cursor)

    def denied(self, message, fn):
        with self.assertRaisesRegex(ValueError, message):
            fn()

    def test_01_departure_positive(self):
        item, cursor = self.project()
        self.assertEqual(item, {
            "kind": "travel.departed", "tick": 20,
            "traveller": "npc:ada", "status": "departed"})
        self.assertEqual(cursor, (20, 7))

    def test_02_drop_generation_seed(self):
        e = original("world.generated")
        self.assertEqual(self.project(e), (None, (0, 0)))

    def test_03_drop_parentage_record(self):
        self.assertIsNone(self.project(original("society.parentage-recorded"))[0])

    def test_04_drop_owner_registry_event(self):
        self.assertIsNone(self.project(original("world.owner-updated"))[0])

    def test_05_drop_unknown_event(self):
        self.assertIsNone(self.project(original("npc.moved"))[0])

    def test_06_exclude_route_and_destination(self):
        e, _ = self.project()
        self.assertEqual(set(e), {"kind", "tick", "traveller", "status"})
        self.assertNotIn("loc:unknown-next-node", str(e))
        self.assertNotIn("SECRET_FUTURE", str(e))

    def test_07_arrived_location_positive(self):
        e, _ = self.project(original("travel.arrived"))
        self.assertEqual(e["at"], "loc:market")
        self.assertEqual(e["status"], "arrived")

    def test_08_arrival_filters_route_cost_time(self):
        e, _ = self.project(original("travel.arrived"))
        self.assertEqual(set(e), {"kind", "tick", "traveller", "status", "at"})
        self.assertNotIn("999", str(e))

    def test_09_blocked_safe_reason(self):
        e, _ = self.project(original("travel.blocked"))
        self.assertEqual(e["reason"], "forbidden")

    def test_10_blocked_omits_capacities_and_access_list(self):
        e, _ = self.project(original("travel.blocked"))
        self.assertNotIn("123", str(e))
        self.assertNotIn("secret", str(e))
        self.assertEqual(set(e), {"kind", "tick", "traveller", "status", "reason"})

    def test_11_strict_actor_mismatch(self):
        self.denied("CROSS_ACTOR", lambda: self.project(actor="npc:ben"))

    def test_12_multi_actor_event_rejected(self):
        e = original()
        e["actors"] = ["npc:ada", "npc:ben"]
        self.denied("CROSS_ACTOR", lambda: self.project(e))

    def test_13_missing_actor_rejected(self):
        e = original()
        e.pop("actors")
        self.denied("CROSS_ACTOR", lambda: self.project(e))

    def test_14_data_traveller_mismatch(self):
        e = original()
        e["data"]["traveller"] = "npc:ben"
        self.denied("TRAVELLER_INCONSISTENT", lambda: self.project(e))

    def test_15_invalid_reason_rejected(self):
        e = original("travel.blocked")
        e["data"]["reason"] = "hidden-owner-npc:secret"
        self.denied("BLOCK_REASON_NOT_PUBLIC", lambda: self.project(e))

    def test_16_arrival_without_public_location_rejected(self):
        e = original("travel.arrived")
        e["data"].pop("at")
        self.denied("ARRIVAL_LOCATION", lambda: self.project(e))

    def test_17_boolean_tick_rejected(self):
        e = original()
        e["tick"] = True
        self.denied("ORIGINAL_EVENT_ID_OR_TICK", lambda: self.project(e))

    def test_18_boolean_id_rejected(self):
        e = original()
        e["id"] = True
        self.denied("ORIGINAL_EVENT_ID_OR_TICK", lambda: self.project(e))

    def test_19_reordered_tick_rejected(self):
        self.denied("NONMONOTONIC_EVENT", lambda: self.project(cursor=(21, 6)))

    def test_20_duplicate_event_rejected(self):
        self.denied("NONMONOTONIC_EVENT", lambda: self.project(cursor=(20, 7)))

    def test_21_same_tick_next_original_id_accepted(self):
        _, cursor = self.project(cursor=(20, 6))
        self.assertEqual(cursor, (20, 7))

    def test_22_new_tick_with_replayed_lower_event_id_denied(self):
        self.denied("NONMONOTONIC_EVENT", lambda:self.project(cursor=(19, 200)))

    def test_23_no_secret_in_any_allowed_output(self):
        for typ in ("travel.departed", "travel.arrived", "travel.blocked"):
            item, _ = self.project(original(typ))
            for secret in ("SECRET_", "999", "permitted", "capacity",
                           "arrivesAt", "cost", "causes", "path"):
                self.assertNotIn(secret, str(item))

    def test_24_cursor_strict_validation(self):
        self.denied("CURSOR", lambda: self.project(cursor=(True, 3)))

    def test_25_no_scoped_actor_rejected(self):
        self.denied("SCOPED_ACTOR_REQUIRED", lambda: self.project(actor=""))

    def test_26_missing_event_type_returns_nothing(self):
        e = original()
        del e["type"]
        self.assertEqual(self.project(e), (None, (0, 0)))

    def test_27_original_science_authority_remains_denied(self):
        status = original_science_authority()
        self.assertEqual(status["disposition"], CENSUS)
        self.assertFalse(status["learner_action_dispatch_authorized"])
        self.assertFalse(status["original_public_observation_authorized"])
        self.assertFalse(status["scientific_go"])

    def test_28_blocked_not_grounds_for_parentage_or_owner_change(self):
        e, _ = self.project(original("travel.blocked"))
        self.assertEqual(e["kind"], "travel.blocked")
        self.assertEqual(e["status"], "blocked")
        self.assertNotIn("owner", str(e))
        self.assertNotIn("parent", str(e))

    def test_29_new_tick_with_new_original_event_id_accepted(self):
        _, cursor=self.project(cursor=(19, 6))
        self.assertEqual(cursor,(20, 7))

    def test_30_cursor_requires_explicit_new_world_reset(self):
        self.denied("NONMONOTONIC_EVENT",lambda:self.project(cursor=(19, 900)))
        _, cursor=self.project(cursor=(0, 0))
        self.assertEqual(cursor,(20, 7))

    def test_31_tick_regression_still_denied_when_event_id_grows(self):
        e=original()
        e["id"]=901
        self.denied("NONMONOTONIC_EVENT",lambda:self.project(e,cursor=(21,900)))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""TW1 strictly synthetic DEV falsification. No RPGWorldSim runtime or science."""
import copy
import unittest
import tw1_dev_typed_truth as m


def fixture():
    return {
        "role": m.ROLE,
        "npcs": ["npc:ada", "npc:ben", "npc:cy"],
        "locations": ["loc:home", "loc:market"],
        "buildings": ["bld:cottage", "bld:empty"],
        "occupancy": {"npc:ada": "loc:home", "npc:ben": None, "npc:cy": "loc:market"},
        "owners": {"bld:cottage": "npc:ada", "bld:empty": None},
        "parentage": {
            "npc:cy": {
                "mother": {"kind": "known", "npc": "npc:ada"},
                "father": {"kind": "absent", "reason": "unknown"}},
            "npc:ben": {
                "mother": {"kind": "known", "npc": "npc:ada"},
                "father": {"kind": "known", "npc": "npc:cy"}}},
        "location_census_complete": True,
        "owner_census_complete": True,
        "parentage_census_complete": True
    }


class TW1SourceNativeDevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.s = fixture()

    def result(self, rel, a, b):
        return m.evaluate(self.s, rel, a, b)

    def invalid(self, text, callback):
        with self.assertRaisesRegex(ValueError, text):
            callback()

    def test_01_location_positive(self):
        self.assertEqual(self.result("located_in", "npc:ada", "loc:home"), m.TRUE)

    def test_02_location_negative_with_complete_census(self):
        self.assertEqual(self.result("located_in", "npc:ada", "loc:market"), m.FALSE)

    def test_03_unplaced_traveler_is_unknown(self):
        self.assertEqual(self.result("located_in", "npc:ben", "loc:market"), m.UNKNOWN)

    def test_04_location_incomplete_does_not_claim_false(self):
        self.s["location_census_complete"] = False
        self.assertEqual(self.result("located_in", "npc:ada", "loc:market"), m.UNKNOWN)

    def test_05_location_positive_survives_incomplete_snapshot(self):
        self.s["location_census_complete"] = False
        self.assertEqual(self.result("located_in", "npc:ada", "loc:home"), m.TRUE)

    def test_06_ownership_positive(self):
        self.assertEqual(self.result("owns", "npc:ada", "bld:cottage"), m.TRUE)

    def test_07_owner_of_other_property_negative_if_complete(self):
        self.assertEqual(self.result("owns", "npc:ben", "bld:cottage"), m.FALSE)

    def test_08_no_owner_is_unknown_not_false(self):
        self.assertEqual(self.result("owns", "npc:ben", "bld:empty"), m.UNKNOWN)

    def test_09_owner_incomplete_is_unknown(self):
        self.s["owner_census_complete"] = False
        self.assertEqual(self.result("owns", "npc:ben", "bld:cottage"), m.UNKNOWN)

    def test_10_parent_positive_known_mother(self):
        self.assertEqual(self.result("parent_of", "npc:ada", "npc:cy"), m.TRUE)

    def test_11_absent_father_cannot_imply_negative(self):
        self.assertEqual(self.result("parent_of", "npc:ben", "npc:cy"), m.UNKNOWN)

    def test_12_true_parent_not_same_as_child(self):
        self.assertEqual(self.result("parent_of", "npc:ada", "npc:ben"), m.TRUE)

    def test_13_parent_of_all_known_different(self):
        self.assertEqual(self.result("parent_of", "npc:ben", "npc:cy"), m.UNKNOWN)

    def test_14_complete_parentage_two_known_false_for_third(self):
        self.assertEqual(self.result("parent_of", "npc:ben", "npc:cy"), m.UNKNOWN)

    def test_15_second_known_parent_is_true(self):
        self.assertEqual(self.result("parent_of", "npc:cy", "npc:ben"), m.TRUE)

    def test_16_incomplete_parentage_blocks_false(self):
        self.s["parentage_census_complete"] = False
        self.assertEqual(self.result("parent_of", "npc:cy", "npc:ben"), m.TRUE)

    def test_17_missing_parentage_unknown(self):
        self.assertEqual(self.result("parent_of", "npc:cy", "npc:ada"), m.UNKNOWN)

    def test_18_wrong_type_ownership_denied(self):
        self.invalid("TYPE_OR_UNKNOWN_ENTITY", lambda: self.result("owns", "npc:ada", "loc:home"))

    def test_19_wrong_type_location_denied(self):
        self.invalid("TYPE_OR_UNKNOWN_ENTITY", lambda: self.result("located_in", "npc:ada", "bld:cottage"))

    def test_20_unknown_person_denied(self):
        self.invalid("TYPE_OR_UNKNOWN_ENTITY", lambda: self.result("parent_of", "npc:unknown", "npc:cy"))

    def test_21_self_parentage_denied(self):
        self.invalid("SELF_RELATION", lambda: self.result("parent_of", "npc:ada", "npc:ada"))

    def test_22_reverse_parent_role_does_not_become_true(self):
        self.assertEqual(self.result("parent_of", "npc:cy", "npc:ada"), m.UNKNOWN)

    def test_23_missing_role_denied(self):
        self.s["role"] = "L10_PROSPECTIVE_NEW_SOURCE_FAMILY"
        self.invalid("DEV_ROLE_AND_FIELDS", lambda: m.validate(self.s))

    def test_24_payload_field_denied(self):
        self.s["hidden_generator_seed"] = "secret"
        self.invalid("DEV_ROLE_AND_FIELDS", lambda: m.validate(self.s))

    def test_25_boolean_faked_as_census_type_denied(self):
        self.s["parentage_census_complete"] = 1
        self.invalid("CENSUS_CERTIFICATE", lambda: m.validate(self.s))

    def test_26_duplicated_npc_denied(self):
        self.s["npcs"].append("npc:ada")
        self.invalid("TYPED_UNIVERSE", lambda: m.validate(self.s))

    def test_27_unknown_parent_reason_denied(self):
        self.s["parentage"]["npc:cy"]["father"]["reason"] = "fake"
        self.invalid("PARENT_ABSENCE_REASON", lambda: m.validate(self.s))

    def test_28_duplicate_same_known_parent_denied(self):
        self.s["parentage"]["npc:cy"]["father"] = {"kind":"known","npc":"npc:ada"}
        self.invalid("PARENT_DISTINCT", lambda: m.validate(self.s))

    def test_29_self_parent_denied_even_in_source(self):
        self.s["parentage"]["npc:cy"]["father"] = {"kind":"known","npc":"npc:cy"}
        self.invalid("PARENT_KNOWN_PERSON", lambda: m.validate(self.s))

    def test_30_unknown_query_relation_denied(self):
        self.invalid("RELATION", lambda: self.result("carried_is_owner", "npc:ada", "bld:cottage"))

    def test_31_unknowns_kept_in_denominator(self):
        res = m.account([m.TRUE,m.FALSE,m.UNKNOWN,m.UNKNOWN])
        self.assertEqual((res["total"],res["true"],res["false"],res["unknown"]), (4,1,1,2))
        self.assertTrue(res["unknown_retained"])
        self.assertFalse(res["scientific_go"])

    def test_32_no_prospective_evaluator_or_source_auth(self):
        self.assertFalse(m.account([m.UNKNOWN])["original_source_executed"])
        self.assertFalse(m.account([m.UNKNOWN])["independent_scorer_authorized"])

    def test_33_missing_ownership_record_is_unknown(self):
        del self.s["owners"]["bld:cottage"]
        self.assertEqual(self.result("owns", "npc:ada", "bld:cottage"), m.UNKNOWN)

    def test_34_missing_occupancy_record_is_unknown(self):
        del self.s["occupancy"]["npc:ada"]
        self.assertEqual(self.result("located_in", "npc:ada", "loc:home"), m.UNKNOWN)

    def test_35_invalid_missing_parentage_slot_rejected(self):
        del self.s["parentage"]["npc:cy"]["father"]
        self.invalid("PARENT_SLOTS", lambda: m.validate(self.s))


if __name__ == "__main__":
    unittest.main()

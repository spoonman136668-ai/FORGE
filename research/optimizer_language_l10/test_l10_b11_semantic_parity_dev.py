#!/usr/bin/env python3
"""L10-B11 original-rule typed mapping and NLTK public development tests."""
from __future__ import annotations

import unittest

import l10_b9_open_dev_world as dev
import l10_b11_semantic_parity_dev as sem


class L10B11SourceSemantics(unittest.TestCase):
    def setUp(self):
        self.truth = dev.signed_facts(dev.public_initial_state())

    def reject(self, predicate, args, types, reason):
        with self.assertRaisesRegex(ValueError, reason):
            sem.map_textworld_positive(predicate, args, types)

    def test_01_only_original_at_object_room_maps(self):
        self.assertEqual(sem.map_textworld_positive(
            "at", ("Aster", "Boreal"), ("o", "r")),
            ("Aster", "located_in", "Boreal", 1))

    def test_02_inventory_carried_is_not_owned(self):
        self.reject("in", ("Aster", "Boreal"),
                    ("o", "I"), "UNSUPPORTED_MEANING")

    def test_03_container_inside_is_not_ownership(self):
        self.reject("in", ("Aster", "Boreal"),
                    ("o", "c"), "UNSUPPORTED_MEANING")

    def test_04_parent_of_not_in_original_rules(self):
        self.reject("parent_of", ("Aster", "Boreal"),
                    ("o", "r"), "UNSUPPORTED_MEANING")

    def test_05_owns_not_in_original_rules(self):
        self.reject("owns", ("Aster", "Boreal"),
                    ("o", "r"), "UNSUPPORTED_MEANING")

    def test_06_player_room_not_object_room(self):
        self.reject("at", ("Aster", "Boreal"),
                    ("P", "r"), "UNSUPPORTED_MEANING")

    def test_07_unknown_original_action_field(self):
        self.reject("go", ("Aster", "Boreal"),
                    ("o", "r"), "UNSUPPORTED_MEANING")

    def test_08_wrong_types(self):
        self.reject("at", ("Aster", "Boreal"),
                    ("r", "o"), "UNSUPPORTED_MEANING")

    def test_09_missing_type_declaration(self):
        self.reject("at", ("Aster", "Boreal"),
                    (), "TYPED_PREDICATE_SCHEMA")

    def test_10_nonpublic_entity(self):
        self.reject("at", ("Aster", "PrivateRoom"),
                    ("o", "r"), "PUBLIC_NAMES")

    def test_11_self_relationship(self):
        self.reject("at", ("Aster", "Aster"),
                    ("o", "r"), "PUBLIC_NAMES")

    def test_12_no_closed_world_negatives_authorized(self):
        status = sem.source_eligibility()
        self.assertFalse(status["closed_world_negative_claims_from_missing_TextWorld_facts"])
        self.assertFalse(status["full_L10_source_admission"])

    def test_13_no_full_relation_coverage(self):
        state = sem.source_eligibility()
        self.assertFalse(state["owns_supported_from_original_TextWorld"])
        self.assertFalse(state["parent_of_supported_from_original_TextWorld"])
        self.assertIn("NO_GO", state["disposition"])

    def test_14_nltk_accepts_all_36_genuine_dev_facts(self):
        r = sem.check_all_signed_with_nltk(self.truth, self.truth)
        self.assertEqual(r["NLTK_correct_signed_claims"], 36)
        self.assertTrue(r["exact"])

    def test_15_nltk_does_not_claim_authority(self):
        r = sem.check_all_signed_with_nltk(self.truth, self.truth)
        self.assertFalse(r["scientific_go"])
        self.assertFalse(r["independent_owner_scorer_acceptance"])
        self.assertFalse(r["original_TextWorld_source_executed"])
        self.assertFalse(r["pinned_original_NLTK_git_blob_executed"])
        self.assertEqual(r["prospective_examples_consumed"], 0)

    def test_16_nltk_rejects_different_valid_36_fact_world(self):
        other = dev.intervene(dev.public_initial_state(),
                              {"subject":"Aster","relation":"located_in","object":"Cora"})
        r = sem.check_all_signed_with_nltk(self.truth, dev.signed_facts(other))
        self.assertFalse(r["exact"])
        self.assertEqual(r["NLTK_correct_signed_claims"], 34)

    def test_17_independently_true_after_transition(self):
        altered = dev.intervene(dev.public_initial_state(),
                                {"subject":"Dana","relation":"owns","object":"Aster"})
        facts = dev.signed_facts(altered)
        self.assertTrue(sem.check_all_signed_with_nltk(facts, facts)["exact"])

    def test_18_graph_order_is_not_a_semantic_feature(self):
        self.assertTrue(sem.check_all_signed_with_nltk(
            self.truth, tuple(reversed(self.truth)))["exact"])

    def test_19_one_missing_signed_claim_denied(self):
        with self.assertRaisesRegex(ValueError, "PROPOSED_DENOMINATOR"):
            sem.check_all_signed_with_nltk(self.truth, self.truth[:-1])

    def test_20_one_duplicate_signed_claim_denied(self):
        with self.assertRaisesRegex(ValueError, "PROPOSED_DUPLICATE"):
            sem.check_all_signed_with_nltk(
                self.truth, self.truth[:-1] + (self.truth[0],))

    def test_21_unknown_relation_denied(self):
        rows = list(self.truth)
        s, r, o, p = rows[0]
        rows[0] = (s, "secret", o, p)
        with self.assertRaisesRegex(ValueError, "PROPOSED_SEMANTIC_TYPE"):
            sem.check_all_signed_with_nltk(self.truth, tuple(rows))

    def test_22_invalid_boolean_polarity_denied(self):
        rows = list(self.truth)
        s, r, o, p = rows[0]
        rows[0] = (s, r, o, True)
        with self.assertRaisesRegex(ValueError, "PROPOSED_SEMANTIC_TYPE"):
            sem.check_all_signed_with_nltk(self.truth, tuple(rows))

    def test_23_wrong_sign_without_replacement_denied(self):
        rows = list(self.truth)
        s, r, o, p = rows[0]
        rows[0] = (s, r, o, -p)
        with self.assertRaisesRegex(ValueError, "PROPOSED_UNIQUE_POSITIVE"):
            sem.check_all_signed_with_nltk(self.truth, tuple(rows))

    def test_24_self_object_denied(self):
        rows = list(self.truth)
        s, r, o, p = rows[0]
        rows[0] = (s, r, s, p)
        with self.assertRaisesRegex(ValueError, "PROPOSED_SEMANTIC_TYPE"):
            sem.check_all_signed_with_nltk(self.truth, tuple(rows))

    def test_25_empty_truth_denied(self):
        with self.assertRaisesRegex(ValueError, "TRUTH_DENOMINATOR"):
            sem.check_all_signed_with_nltk([], self.truth)

    def test_26_non_tuple_record_denied(self):
        rows = list(self.truth)
        rows[0] = list(rows[0])
        with self.assertRaisesRegex(ValueError, "PROPOSED_FACT_SCHEMA"):
            sem.check_all_signed_with_nltk(self.truth, tuple(rows))


if __name__ == "__main__":
    unittest.main()

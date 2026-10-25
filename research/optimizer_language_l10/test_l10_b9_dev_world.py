#!/usr/bin/env python3
"""Open synthetic-DEV action-consequence semantic adversarial tests only."""
from __future__ import annotations
import unittest

import l10_b9_open_dev_world as world
import l10_b9_separate_dev_checker as checker


def act(subject="Aster", relation="located_in", obj="Cora"):
    return {"subject": subject, "relation": relation, "object": obj}


class L10B9DevWorldTests(unittest.TestCase):
    def setUp(self):
        self.before = world.public_initial_state()
        self.action = act()
        self.after = world.intervene(self.before, self.action)
        self.before_text = world.render(self.before)
        self.after_text = world.render(self.after)

    def test_01_public_dev_role(self):
        self.assertEqual(world.ROLE, checker.ROLE)
        self.assertEqual(world.ROLE, "L10_SYNTHETIC_DEV")

    def test_02_no_mutation_of_before_state(self):
        self.assertEqual(self.before["Aster", "located_in"], "Boreal")

    def test_03_complete_twelve_public_slots(self):
        self.assertEqual(len(self.before), 12)

    def test_04_complete_thirtysix_facts(self):
        self.assertEqual(len(world.signed_facts(self.before)), 36)

    def test_05_all_signed_truth_included(self):
        f = world.signed_facts(self.before)
        self.assertEqual(sum(v == 1 for *_, v in f), 12)
        self.assertEqual(sum(v == -1 for *_, v in f), 24)

    def test_06_independent_checker_parses_full_graph(self):
        self.assertEqual(len(checker.decode_graph(self.before_text)), 36)

    def test_07_change_exact_targeted_relation(self):
        self.assertEqual(self.after["Aster", "located_in"], "Cora")
        self.assertEqual(self.before["Aster", "located_in"], "Boreal")

    def test_08_all_nontarget_slots_conserved(self):
        for key in world.SLOTS:
            if key != ("Aster", "located_in"):
                self.assertEqual(self.before[key], self.after[key])

    def test_09_independent_checker_accepts_real_step(self):
        self.assertEqual(checker.check_intervention(
            self.before_text, self.action, self.after_text),
            "DEV_TRANSITION_EXACT_SIGNED_GRAPH_PASS")

    def test_10_noop_same_object_is_valid(self):
        same = act(obj="Boreal")
        after = world.intervene(self.before, same)
        self.assertEqual(after, self.before)
        self.assertIn("PASS", checker.check_intervention(
            self.before_text, same, world.render(after)))

    def test_11_replay_deterministic(self):
        actions = [self.action, act("Dana", "owns", "Aster")]
        self.assertEqual(world.replay(actions), world.replay(tuple(actions)))

    def test_12_replay_has_one_state_per_action_plus_initial(self):
        self.assertEqual(len(world.replay([self.action] * 12)), 13)

    def test_13_replay_rejects_more_than_twelve_steps(self):
        with self.assertRaisesRegex(ValueError, "ACTION_BUDGET"):
            world.replay([self.action] * 13)

    def test_14_public_graph_digest_deterministic(self):
        self.assertEqual(world.fixture_digest_only(self.before),
                         world.fixture_digest_only(dict(self.before)))

    def test_15_public_graph_digest_changes_after_effect(self):
        self.assertNotEqual(world.fixture_digest_only(self.before),
                            world.fixture_digest_only(self.after))

    def test_16_different_real_interventions_not_equivalent(self):
        alt = world.intervene(self.before, act(obj="Dana"))
        self.assertNotEqual(self.after, alt)
        self.assertEqual(alt["Aster", "located_in"], "Dana")

    def test_17_unknown_relation_denied(self):
        with self.assertRaisesRegex(ValueError, "ACTION_DOMAIN"):
            world.intervene(self.before, act(relation="is_magic"))

    def test_18_self_relation_denied(self):
        with self.assertRaisesRegex(ValueError, "ACTION_DOMAIN"):
            world.intervene(self.before, act(obj="Aster"))

    def test_19_missing_action_field_denied(self):
        with self.assertRaisesRegex(ValueError, "ACTION_FIELDS"):
            world.intervene(self.before, {"subject": "Aster", "object": "Cora"})

    def test_20_added_hidden_action_field_denied(self):
        a = dict(self.action, source_hidden_role="GOAL")
        with self.assertRaisesRegex(ValueError, "ACTION_FIELDS"):
            world.intervene(self.before, a)

    def test_21_broken_state_slot_denied(self):
        state = dict(self.before)
        state.pop(("Aster", "owns"))
        with self.assertRaisesRegex(ValueError, "STATE_SLOTS"):
            world.intervene(state, self.action)

    def test_22_forced_nonpublic_state_denied(self):
        state = dict(self.before)
        state["Aster", "owns"] = "Unknown"
        with self.assertRaisesRegex(ValueError, "STATE_OBJECT"):
            world.render(state)

    def test_23_missing_semantic_fact_denied(self):
        text = "; ".join(self.after_text.split("; ")[:-1])
        with self.assertRaisesRegex(ValueError, "FULL_GRAPH_DENOMINATOR"):
            checker.decode_graph(text)

    def test_24_duplicate_proposition_denied(self):
        pieces = self.after_text.split("; ")
        pieces[-1] = pieces[0]
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CLAIM"):
            checker.decode_graph("; ".join(pieces))

    def test_25_missing_positive_due_to_negation_denied(self):
        bad = self.after_text.replace(
            "Aster :: located_in :: Cora :: +",
            "Aster :: located_in :: Cora :: -")
        with self.assertRaisesRegex(ValueError, "EXACT_ONE_TRUE_OBJECT"):
            checker.decode_graph(bad)

    def test_26_counterfactual_misreport_denied(self):
        alternative = world.render(world.intervene(self.before, act(obj="Dana")))
        with self.assertRaisesRegex(ValueError, "COUNTERFACTUAL_EFFECT_MISMATCH"):
            checker.check_intervention(self.before_text, self.action, alternative)

    def test_27_unrelated_fact_corruption_denied(self):
        corrupt = world.intervene(self.after, act("Boreal", "owns", "Cora"))
        with self.assertRaisesRegex(ValueError, "COUNTERFACTUAL_EFFECT_MISMATCH"):
            checker.check_intervention(self.before_text, self.action, world.render(corrupt))

    def test_28_subject_object_inversion_denied(self):
        bad = self.after_text.replace(
            "Aster :: located_in :: Cora :: +",
            "Cora :: located_in :: Aster :: +")
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CLAIM"):
            checker.decode_graph(bad)

    def test_29_parser_rejects_nonsemantic_prose(self):
        bad = self.after_text.replace(" :: located_in :: ", " is around ", 1)
        with self.assertRaisesRegex(ValueError, "SIGNED_SEMANTIC_CLAUSE"):
            checker.decode_graph(bad)

    def test_30_order_not_semantic_signal(self):
        shuffled = "; ".join(reversed(self.after_text.split("; ")))
        self.assertEqual(checker.decode_graph(shuffled),
                         checker.decode_graph(self.after_text))

    def test_31_wrong_action_cannot_explain_true_transition(self):
        with self.assertRaisesRegex(ValueError, "COUNTERFACTUAL_EFFECT_MISMATCH"):
            checker.check_intervention(
                self.before_text, act(obj="Dana"), self.after_text)


if __name__ == "__main__":
    unittest.main()

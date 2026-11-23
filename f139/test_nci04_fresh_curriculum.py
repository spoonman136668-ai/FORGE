"""DEV-only, no provider/network/controller side effects."""
import unittest

from f139.nci04_fresh_curriculum import (
    CurriculumDenied, PROPOSAL_SCHEMA, select_next,
)

SOURCE = "a" * 40
TREE = "b" * 40


def hist(after="1", intent="2", stage="VERIFIED", evidence="3"):
    return {
        "after_sha256": after * 64, "intent_sha256": intent * 64,
        "stage": stage,
        "terminal_evidence_sha256": evidence * 64 if stage == "VERIFIED" else None,
    }


def proposal(after="4", intent="5", cost=2, prereq=None, exclude=None):
    return {
        "schema": PROPOSAL_SCHEMA, "source_sha": SOURCE,
        "target_tree_sha": TREE, "after_sha256": after * 64,
        "intent_sha256": intent * 64, "mechanism_sha256": "6" * 64,
        "qualification_sha256": "7" * 64,
        "prerequisites": list(prereq or []), "exclusions": list(exclude or []),
        "cost_units": cost, "development_only": True,
        "scientific_first_use": False, "paid_model_calls": 0,
        "accepted_ref_mutations": 0,
    }


def pick(history=None, proposals=None, budget=10):
    return select_next(
        history=[hist()] if history is None else history,
        proposals=[] if proposals is None else proposals,
        source_sha=SOURCE, target_tree_sha=TREE,
        remaining_cost_units=budget,
    )


class HistoryConditionedSelectorTests(unittest.TestCase):
    def test_history_dependent_and_deterministic_with_reordered_pool(self):
        plain = proposal(after="4", intent="5", cost=1)
        dependent = proposal(after="8", intent="9", cost=4,
                             prereq=["1" * 64])
        self.assertEqual(pick(proposals=[plain, dependent]), dependent)
        self.assertEqual(pick(proposals=[dependent, plain]), dependent)
        self.assertEqual(pick(history=[hist(after="a", intent="b")],
                              proposals=[plain, dependent]), plain)

    def test_consumed_identity_never_reselected(self):
        candidate = proposal()
        self.assertIsNone(pick(
            history=[hist(after="4", intent="5")],
            proposals=[candidate]))
        self.assertIsNone(pick(
            history=[hist(after="4", intent="f")],
            proposals=[candidate]))

    def test_uncertain_post_blocks_all_successors(self):
        with self.assertRaisesRegex(CurriculumDenied, "LAST_TICKET_NOT_TERMINAL"):
            pick(history=[hist(), hist(after="a", intent="b", stage="START_RISK")],
                 proposals=[proposal()])

    def test_wait_provider_and_negative_cannot_claim_completion(self):
        for stage in ("WAIT_PROVIDER", "NEGATIVE", "READY"):
            with self.subTest(stage=stage):
                with self.assertRaises(CurriculumDenied):
                    pick(history=[hist(after="a", intent="b", stage=stage)],
                         proposals=[proposal()])

    def test_exclusions_include_consumed_negatives(self):
        past = [hist(after="a", intent="b", stage="NEGATIVE"), hist()]
        self.assertIsNone(pick(history=past, proposals=[
            proposal(exclude=["a" * 64])]))
        self.assertIsNotNone(pick(history=past, proposals=[
            proposal(prereq=["1" * 64])]))

    def test_fails_closed_on_unsafe_authority(self):
        for key, value in (
            ("scientific_first_use", True), ("paid_model_calls", 1),
            ("accepted_ref_mutations", 1), ("development_only", False),
            ("source_sha", "0" * 40), ("target_tree_sha", "0" * 40),
            ("qualification_sha256", "unverified"),
        ):
            with self.subTest(key=key):
                p = proposal()
                p[key] = value
                with self.assertRaises(CurriculumDenied):
                    pick(proposals=[p])

    def test_bad_provenance_history_and_duplicate_pool_fail(self):
        for bad in (
            [{**hist(), "terminal_evidence_sha256": None}],
            [hist(), hist()],
            [hist(after="g")],
        ):
            with self.assertRaises(CurriculumDenied):
                pick(history=bad, proposals=[proposal()])
        with self.assertRaisesRegex(CurriculumDenied, "DUPLICATE_PROPOSAL"):
            pick(proposals=[proposal(), proposal()])

    def test_budget_zero_and_exhaustion(self):
        self.assertIsNone(pick(proposals=[proposal()], budget=0))
        self.assertIsNone(pick(proposals=[]))
        self.assertIsNotNone(pick(proposals=[proposal(cost=2)], budget=2))

    def test_contradictory_deps_and_unbounded_input_fail(self):
        p = proposal(prereq=["1" * 64], exclude=["1" * 64])
        with self.assertRaises(CurriculumDenied):
            pick(proposals=[p])
        with self.assertRaises(CurriculumDenied):
            pick(proposals=[proposal()] * 65)

    def test_sealed_prior_exclusions_and_uncertain_publication_are_spent(self):
        p = proposal()
        self.assertIsNone(select_next(
            history=[hist()], proposals=[p],
            source_sha=SOURCE, target_tree_sha=TREE,
            remaining_cost_units=10,
            spent_after_sha256=frozenset({p["after_sha256"]})))
        self.assertIsNone(select_next(
            history=[hist()], proposals=[p],
            source_sha=SOURCE, target_tree_sha=TREE,
            remaining_cost_units=10,
            spent_intent_sha256=frozenset({p["intent_sha256"]})))

    def test_sealed_prior_exclusions_must_be_well_formed(self):
        for spent_after in ({"4" * 64}, frozenset({"z" * 64})):
            with self.assertRaisesRegex(CurriculumDenied, "SEALED_SPENT"):
                select_next(
                    history=[hist()], proposals=[proposal()],
                    source_sha=SOURCE, target_tree_sha=TREE,
                    remaining_cost_units=10, spent_after_sha256=spent_after)


if __name__ == "__main__":
    unittest.main()

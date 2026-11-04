"""Negative controls for the non-authorizing prospective assignment boundary."""
import copy
import unittest

from f139.nci04_prospective_assignment import validate_assignment, sha256, SCHEMA

A = sha256(b"candidate-A")
B = sha256(b"candidate-B")
OWNER = "a" * 40
POLICY = sha256(b"policy")
EVENT = sha256(b"event")


def fixture():
    return dict(schema=SCHEMA, lane="Yggdrasil", ticket="development-1",
                owner_source_sha=OWNER, candidate_sha256=A,
                eligible_candidate_sha256=sorted([A, B]),
                policy_sha256=POLICY, selection_mode="DETERMINISTIC",
                selection_probability_bp=10000, assignment_event_sha256=EVENT,
                decision_utc="2026-11-03T12:00:00Z",
                outcome_available_at_decision=False)


def check(row):
    return validate_assignment(
        row, expected_ticket="development-1", expected_source_sha=OWNER,
        expected_candidate_sha256=A, expected_eligible_hashes=[A, B])


class ProspectiveAssignmentTests(unittest.TestCase):
    def test_actual_git_source_and_fractional_owner_clock(self):
        row = fixture()
        row["decision_utc"] = "2026-11-03T12:00:00.123456Z"
        self.assertTrue(check(row)["internal_consistency"])

    def test_reject_digest_in_place_of_git_source(self):
        row = fixture()
        row["owner_source_sha"] = sha256(b"owner")
        with self.assertRaisesRegex(ValueError, "SOURCE_SHA"):
            validate_assignment(row, expected_ticket=row["ticket"],
                                expected_source_sha=row["owner_source_sha"],
                                expected_candidate_sha256=A,
                                expected_eligible_hashes=[A, B])

    def test_reject_impossible_calendar_date(self):
        row = fixture()
        row["decision_utc"] = "2026-02-31T12:00:00Z"
        with self.assertRaisesRegex(ValueError, "TIMESTAMP"):
            check(row)

    def test_valid_is_never_authorizing(self):
        result = check(fixture())
        self.assertTrue(result["internal_consistency"])
        self.assertFalse(result["independent_randomization_proven"])
        self.assertFalse(result["decision_time_proven"])
        self.assertFalse(result["scientific_authorized"])

    def test_reject_retrospective(self):
        row = fixture()
        row["outcome_available_at_decision"] = True
        with self.assertRaises(ValueError):
            check(row)

    def test_reject_fake_deterministic_probability(self):
        row = fixture()
        row["selection_probability_bp"] = 5000
        with self.assertRaises(ValueError):
            check(row)

    def test_reject_duplicate_slate(self):
        row = fixture()
        row["eligible_candidate_sha256"] = [A, A]
        with self.assertRaises(ValueError):
            check(row)

    def test_reject_wrong_candidate(self):
        row = fixture()
        row["candidate_sha256"] = B
        with self.assertRaises(ValueError):
            check(row)

    def test_reject_unexpected_field(self):
        row = fixture()
        row["scientific_accepted"] = True
        with self.assertRaises(ValueError):
            check(row)

    def test_reject_missing_decision_time(self):
        row = fixture()
        row["decision_utc"] = ""
        with self.assertRaises(ValueError):
            check(row)

    def test_randomized_claim_remains_unproven(self):
        row = fixture()
        row["selection_mode"] = "RANDOMIZED_CLAIM"
        row["selection_probability_bp"] = 5000
        result = check(row)
        self.assertFalse(result["independent_randomization_proven"])


if __name__ == "__main__":
    unittest.main()

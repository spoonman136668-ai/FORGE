"""Negative tests for read-only prospective development feedback joins."""
import unittest

from f139.nci04_prospective_assignment import SCHEMA, sha256
from f139.nci04_prospective_feedback_join import join_prospective_development

A, B = sha256(b"A"), sha256(b"B")
OWNER = "a" * 40


def assignment():
    return dict(schema=SCHEMA, lane="Yggdrasil", ticket="ticket-1",
                owner_source_sha=OWNER, candidate_sha256=A,
                eligible_candidate_sha256=sorted([A, B]),
                policy_sha256=sha256(b"policy"), selection_mode="DETERMINISTIC",
                selection_probability_bp=10000,
                assignment_event_sha256=sha256(b"event"),
                decision_utc="2026-11-03T12:00:00Z",
                outcome_available_at_decision=False)


def feedback():
    return dict(schema="forge.f139.native-development-feedback.v1",
                mode="OBSERVED_TEST_DIAGNOSTICS_ONLY", ticket="ticket-1",
                owner_source_sha=OWNER, candidate_sha256=A,
                artifact_sha256=sha256(b"zip"), report_sha256=sha256(b"report"),
                run_id=123, original_signed_admission_sha256=sha256(b"admission"),
                development_only=True, scientific_accepted=False,
                optimizer_training_authorized=False, dispatch_authorized=False,
                scientific_first_use=False, quality_score=None,
                selection_probability=None, decision_time_menu=None)


def join(a=None, f=None):
    return join_prospective_development(
        assignment() if a is None else a, feedback() if f is None else f,
        expected_eligible_hashes=[A, B])


class JoinTests(unittest.TestCase):
    def test_diagnostic_join_does_not_authorize(self):
        result = join()
        self.assertEqual(result["mode"], "DEVELOPMENT_DIAGNOSTIC_JOIN_ONLY")
        self.assertFalse(result["decision_time_independently_proven"])
        self.assertFalse(result["randomization_independently_proven"])
        self.assertFalse(result["optimizer_training_authorized"])

    def test_ticket_mismatch(self):
        f = feedback()
        f["ticket"] = "another"
        with self.assertRaises(ValueError):
            join(f=f)

    def test_source_mismatch(self):
        f = feedback()
        f["owner_source_sha"] = sha256(b"wrong")
        with self.assertRaises(ValueError):
            join(f=f)

    def test_candidate_mismatch(self):
        f = feedback()
        f["candidate_sha256"] = B
        with self.assertRaises(ValueError):
            join(f=f)

    def test_retrospective(self):
        a = assignment()
        a["outcome_available_at_decision"] = True
        with self.assertRaises(ValueError):
            join(a=a)

    def test_no_scientific_promotion(self):
        f = feedback()
        f["scientific_accepted"] = True
        with self.assertRaises(ValueError):
            join(f=f)

    def test_no_training_promotion(self):
        f = feedback()
        f["optimizer_training_authorized"] = True
        with self.assertRaises(ValueError):
            join(f=f)

    def test_missing_admission(self):
        f = feedback()
        del f["original_signed_admission_sha256"]
        with self.assertRaises(ValueError):
            join(f=f)


if __name__ == "__main__":
    unittest.main()

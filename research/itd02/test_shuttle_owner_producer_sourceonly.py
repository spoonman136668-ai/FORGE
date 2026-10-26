"""Fail-closed producer authorization tests; NEVER run original source episodes.

All tests stop before original source reset/step, RNG draw, model FIT, or
protected source first-use. This does not test the physical transition kernel.
"""
import os
import unittest

from shuttle_owner_producer import NotAdmitted, OriginalShuttlePrivateOwner
from shuttle_source_contract import SOURCE_GIT_BLOB


class _RejectingVerifier:
    def verify_open(self, meta):
        raise NotAdmitted("EXTERNAL_FSA_ADMISSION_NOT_AVAILABLE")


class _MismatchedVerifier:
    def verify_open(self, meta):
        return {"source_git_blob": SOURCE_GIT_BLOB,
                "prereg_id": meta["prereg_id"],
                "cohort_id": meta["cohort_id"],
                "episode_id": meta["episode_id"],
                "seed": meta["seed"], "max_steps": meta["max_steps"] + 1,
                "authority_receipt": "not-a-real-grant"}


class _ForbiddenJournal:
    def write_intent(self, record):
        raise AssertionError("UNAUTHORIZED_JOURNAL_INTENT")

    def write_terminal(self, record):
        raise AssertionError("UNAUTHORIZED_JOURNAL_RESULT")


class OriginalProducerNotAdmittedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ITD02_SHUTTLE_SOURCE")
        if not path:
            raise unittest.SkipTest("Pinned original source is required for source-only qualification")
        with open(path, "rb") as f:
            cls.raw = f.read()

    def make_owner(self, **kwargs):
        return OriginalShuttlePrivateOwner(self.raw, **kwargs)

    def opening(self, owner):
        return owner.open(prereg_id="UNAUTHORIZED-FIXTURE",
                          cohort_id="NO-FSA-COHORT", episode_id="NO-EPISODE",
                          seed=123, max_steps=4)

    def test_default_producer_cannot_start_original_source(self):
        owner = self.make_owner()
        with self.assertRaisesRegex(NotAdmitted, "INDEPENDENT_ADMISSION"):
            self.opening(owner)
        self.assertEqual(owner.public_metadata()["steps"], 0)
        self.assertFalse(owner.public_metadata()["admitted"])
        self.assertFalse(owner.public_metadata()["open"])
        self.assertIsNone(owner._rng)
        self.assertIsNone(owner._state)
        with self.assertRaises(NotAdmitted):
            owner.step("Backup")

    def test_rejected_external_admission_has_zero_original_draws(self):
        owner = self.make_owner(admission=_RejectingVerifier(),
                                journal=_ForbiddenJournal())
        with self.assertRaisesRegex(NotAdmitted, "NOT_AVAILABLE"):
            self.opening(owner)
        self.assertIsNone(owner._rng)
        self.assertIsNone(owner._state)
        self.assertEqual(owner.public_metadata()["steps"], 0)

    def test_mismatched_external_grant_is_not_accepted(self):
        owner = self.make_owner(admission=_MismatchedVerifier(),
                                journal=_ForbiddenJournal())
        with self.assertRaisesRegex(NotAdmitted, "GRANT_MISMATCH"):
            self.opening(owner)
        self.assertIsNone(owner._rng)
        self.assertIsNone(owner._state)
        self.assertEqual(owner.public_metadata()["steps"], 0)

    def test_no_direct_step_or_invalid_action_before_admission(self):
        owner = self.make_owner()
        for action in ("Backup", "GoForward", "TurnAround", "hidden_state"):
            with self.subTest(action=action):
                with self.assertRaises(NotAdmitted):
                    owner.step(action)
        self.assertEqual(owner.public_metadata(), {
            "source_git_blob": SOURCE_GIT_BLOB, "open": False,
            "steps": 0, "admitted": False, "faulted": False})


if __name__ == "__main__":
    unittest.main()

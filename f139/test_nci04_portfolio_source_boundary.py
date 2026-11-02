"""Negative controls for the inactive portfolio source boundary."""
import hashlib
import unittest
from dataclasses import replace

from f139.nci04_portfolio_source_boundary import (
    PortfolioSourceRejected, SourceCandidate, validate_source_candidate,
)

BEFORE = b"def choose():\n    return 0\n"
AFTER = b"def choose():\n    return 1\n"
SHA = lambda b: hashlib.sha256(b).hexdigest()
PARENT = "a" * 40


def candidate(**changes):
    base = SourceCandidate(
        generator="dream_rsi", lane="Yggdrasil", path="native/example.py",
        parent_sha=PARENT, before_sha256=SHA(BEFORE),
        after_sha256=SHA(AFTER), mechanism_sha256="b" * 64,
        question="Does the changed rule improve decisions?",
        hypothesis="A changed rule might improve utility.", after=AFTER)
    return replace(base, **changes)


def check(c, **kw):
    return validate_source_candidate(
        c, lane="Yggdrasil", path="native/example.py", parent_sha=PARENT,
        before=BEFORE, historical_sha256=kw.get("historical_sha256", frozenset()),
        historical_ast_sha256=kw.get("historical_ast_sha256", frozenset()))


class PortfolioSourceBoundaryTests(unittest.TestCase):
    def test_source_candidate_requires_actual_change(self):
        self.assertEqual(len(check(candidate())), 64)

    def test_historical_bytes_cannot_replay(self):
        with self.assertRaisesRegex(PortfolioSourceRejected, "HISTORICAL_REPLAY"):
            check(candidate(), historical_sha256=frozenset({SHA(AFTER)}))

    def test_comment_only_change_rejected(self):
        raw = BEFORE + b"# different comment\n"
        with self.assertRaisesRegex(PortfolioSourceRejected, "NO_SEMANTIC_CHANGE"):
            check(candidate(after=raw, after_sha256=SHA(raw)))

    def test_source_drift_rejected(self):
        with self.assertRaisesRegex(PortfolioSourceRejected, "SOURCE_DIGEST_DRIFT"):
            check(candidate(after_sha256="0" * 64))

    def test_historical_ast_rejected(self):
        ast_id = check(candidate())
        with self.assertRaisesRegex(PortfolioSourceRejected, "HISTORICAL_REPLAY"):
            check(candidate(), historical_ast_sha256=frozenset({ast_id}))

    def test_invalid_python_rejected(self):
        raw = b"def choose(:\n"
        with self.assertRaisesRegex(PortfolioSourceRejected, "SOURCE_NOT_PARSEABLE"):
            check(candidate(after=raw, after_sha256=SHA(raw)))

    def test_no_advisory_only_substitution(self):
        with self.assertRaisesRegex(PortfolioSourceRejected, "UNRECOGNIZED_PROPOSAL"):
            check({"generator": "dream_rsi", "mechanism_sha256": "b" * 64})

    def test_wrong_lane_parent_and_family_rejected(self):
        for bad in (candidate(lane="Wingless"), candidate(parent_sha="c" * 40),
                    candidate(generator="unknown")):
            with self.subTest(bad=bad):
                with self.assertRaises(PortfolioSourceRejected):
                    check(bad)


if __name__ == "__main__":
    unittest.main()

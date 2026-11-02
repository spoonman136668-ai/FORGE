"""Negative controls for the inactive portfolio source boundary."""
import hashlib
import unittest
from dataclasses import replace

from f139.nci04_portfolio_source_boundary import (
    PortfolioSourceRejected, SourceCandidate, validate_source_candidate, validate_generation_batch,
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


class GenerationBatchTests(unittest.TestCase):
    def batch(self, outputs, **changes):
        args = dict(generator="dream_rsi", mechanism=b"qualified mechanism",
                    mechanism_sha256=SHA(b"qualified mechanism"), lane="Yggdrasil",
                    path="native/example.py", parent_sha=PARENT, before=BEFORE,
                    historical_sha256=frozenset(), historical_ast_sha256=frozenset())
        args.update(changes)
        return validate_generation_batch(outputs, **args)

    def output(self, **changes):
        return candidate(mechanism_sha256=SHA(b"qualified mechanism"), **changes)

    def test_actual_source_output_validated(self):
        self.assertEqual(self.batch((self.output(),))[0][0].after, AFTER)

    def test_advisory_optimizer_result_is_not_source(self):
        with self.assertRaisesRegex(PortfolioSourceRejected, "UNRECOGNIZED_PROPOSAL"):
            self.batch(({"weights": [1, 2], "scientific_accepted": False},))

    def test_mechanism_artifact_drift_rejected(self):
        with self.assertRaisesRegex(PortfolioSourceRejected, "ARTIFACT_DRIFT"):
            self.batch((self.output(),), mechanism=b"different implementation")

    def test_output_family_must_match_pinned_generator(self):
        with self.assertRaisesRegex(PortfolioSourceRejected, "OUTPUT_MISMATCH"):
            self.batch((self.output(generator="theta_evolve"),))

    def test_duplicate_batch_and_retained_negatives_rejected(self):
        with self.assertRaisesRegex(PortfolioSourceRejected, "HISTORICAL_REPLAY"):
            self.batch((self.output(), self.output()))
        with self.assertRaisesRegex(PortfolioSourceRejected, "HISTORICAL_REPLAY"):
            self.batch((self.output(),), historical_sha256=frozenset({SHA(AFTER)}))

    def test_batch_bound_is_fail_closed(self):
        for outputs in ((), [self.output()], (self.output(),) * 17):
            with self.assertRaisesRegex(PortfolioSourceRejected, "BOUNDED_SOURCE_BATCH"):
                self.batch(outputs)


if __name__ == "__main__":
    unittest.main()

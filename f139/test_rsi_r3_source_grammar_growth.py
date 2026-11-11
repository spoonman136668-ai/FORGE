"""Frozen source-grammar growth capacity test; not an RSI performance test."""
from dataclasses import replace
from pathlib import Path
import subprocess
import unittest

from f139 import rsi_r3_source_cycle as g0
from f139.rsi_r3_source_grammar_growth import (
    GrammarGrowthDenied, ORIGINAL_BLOB, TARGET, digest, git_blob,
    propose, rewrite, verify,
)

ROOT = Path(__file__).resolve().parents[1]


def committed_source() -> bytes:
    """Read the exact immutable Git blob, not autocrlf-transformed worktree."""
    result = subprocess.run(
        ["git", "-C", str(ROOT), "show", "HEAD:" + TARGET],
        capture_output=True, timeout=20, check=True)
    return result.stdout


BASE = committed_source()
G1_FEEDBACK = ((2, (12, 2, 8, 3)), (3, (12, 3, 4, 9)))
G2_FEEDBACK = ((3, (12, 5, 5, 4)), (4, (12, 3, 9, 9)))


def candidate():
    return propose(original=BASE, consumed=frozenset())


def reviewed_g1():
    p = candidate()
    # Only the exact rewritten, Git-blob-pinned trusted source is run.
    # This is a DEV test-process evaluation, not a sandbox or live owner.
    env = {"__name__": "__main__"}
    exec(compile(p.source, TARGET, "exec"), env)
    return env


class GrammarGrowthTests(unittest.TestCase):
    def test_original_source_is_pinned_and_g1_expands_actual_python_grammar(self):
        self.assertEqual(git_blob(BASE), ORIGINAL_BLOB)
        p = candidate()
        self.assertTrue(verify(p, BASE, frozenset()))
        self.assertEqual(digest(p.source), p.after_sha256)
        self.assertNotEqual(p.before_sha256, p.after_sha256)
        self.assertEqual(len(g0.RANK_EXPRESSIONS), 4)
        with self.assertRaises(g0.R3Denied):
            g0.source_for(4)
        g1 = reviewed_g1()
        self.assertEqual(len(g1["RANK_EXPRESSIONS"]), 5)
        self.assertIn(b"min(row[2], row[3])", g1["source_for"](4))
        self.assertNotIn(g1["source_for"](4),
                         tuple(g0.source_for(i) for i in range(4)))
        for flag in ("original_owner_admitted", "autonomous_rsi_proven",
                     "scientific_first_use", "worker_dispatched", "deployed"):
            self.assertFalse(getattr(p, flag))
        self.assertEqual(BASE, committed_source())
        checked_out = (ROOT / TARGET).read_bytes()
        self.assertIn(checked_out, (BASE, BASE.replace(b"\n", b"\r\n")))

    def test_revised_real_g1_source_generates_new_g2_after_feedback(self):
        g1 = reviewed_g1()
        first = g1["generate"](parent_source=g1["source_for"](0),
                               generation=1, feedback=G1_FEEDBACK,
                               used_operators=frozenset({0}))
        self.assertEqual(first.operator, 2)
        second = g1["generate"](parent_source=first.source,
                                generation=2, feedback=G2_FEEDBACK,
                                used_operators=frozenset({0, 2}))
        self.assertEqual(second.operator, 4)
        self.assertEqual(second.parent_sha256, first.source_sha256)
        self.assertTrue(g1["verify"]((first, second)))
        self.assertNotEqual(first.source_sha256, second.source_sha256)
        # The original G0 cannot validate or generate the novel G2 syntax.
        with self.assertRaises(g0.R3Denied):
            g0._operator_for(second.source)
        env = {"__builtins__": {"max": max, "min": min}}
        exec(compile(second.source, "<reviewed-g2>", "exec"), env)
        self.assertEqual(env["rank"]((10, 1, 8, 5)), 14)
        self.assertEqual(env["rank"]((10, 1, 5, 8)), 14)

    def test_tampering_and_replay_fail_closed(self):
        p = candidate()
        for corrupt in (BASE + b"\n# drift", b"import os\n", b"",
                        BASE.replace(b"    env = ", b"    env = eval(0); ", 1)):
            with self.subTest(corrupt=corrupt[-30:]), self.assertRaises(
                    GrammarGrowthDenied):
                propose(original=corrupt, consumed=frozenset())
        with self.assertRaisesRegex(GrammarGrowthDenied, "SOURCE_ALREADY_CONSUMED"):
            propose(original=BASE, consumed=frozenset({p.after_sha256}))
        for invalid in (None, set(), frozenset({3}), frozenset({"bad"})):
            with self.subTest(invalid=invalid), self.assertRaises(GrammarGrowthDenied):
                propose(original=BASE, consumed=invalid)
        for forged in (replace(p, source=p.source + b"\n"),
                       replace(p, autonomous_rsi_proven=True),
                       replace(p, after_sha256="0" * 64)):
            with self.assertRaises(GrammarGrowthDenied):
                verify(forged, BASE, frozenset())
        self.assertEqual(rewrite(BASE), rewrite(BASE))


if __name__ == "__main__":
    unittest.main()

"""Source-only repair protocol regression, including rejection controls."""
from dataclasses import replace
import unittest

from f139.rsi_r6_known_repair_cycle import (
    Evidence, FAILURE, RepairDenied, digest, propose, task_scope,
)

ORIGINAL = b'''import sqlite3
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as temp:
    location = str(Path(temp) / "state.sqlite")
    with sqlite3.connect(location) as conn:
        conn.execute("CREATE TABLE result(v INTEGER)")
        conn.execute("INSERT INTO result VALUES (1)")
'''
LOG = (b"Traceback (most recent call last):\n"
       b"PermissionError: [WinError 32] The process cannot access the file\n"
       b"C:\\f139\\state.sqlite\n")


def witness(source=ORIGINAL, log=LOG):
    return Evidence("a" * 40, 39782884958, 119838389983,
                    FAILURE, digest(log), log, "f139/diagnostic.py",
                    digest(source))


class KnownRepairCycleTests(unittest.TestCase):
    def test_existing_native_repair_is_selected_and_content_addressed(self):
        source = ORIGINAL
        evidence = witness()
        result = propose(evidence=evidence, pinned_before=source,
                         consumed_scopes=frozenset())
        self.assertNotEqual(result.source, source)
        self.assertIn(b"import contextlib, sqlite3", result.source)
        self.assertIn(b"contextlib.closing(sqlite3.connect(location))", result.source)
        self.assertEqual(result.parent_sha, "a" * 40)
        self.assertEqual(result.original_sha256, digest(source))
        self.assertEqual(result.candidate_sha256, digest(result.source))
        self.assertEqual(result.task_scope_sha256, task_scope(evidence))
        self.assertEqual(result.mechanism, "r16-direct")
        self.assertFalse(result.eligible_for_owner)
        self.assertFalse(result.qualified)
        self.assertFalse(result.deployed)
        self.assertFalse(result.scientific_first_use)
        self.assertFalse(result.autonomous_rsi_proven)
        self.assertIn("CREATE TABLE result", result.source.decode())

    def test_alias_grammar_reuses_existing_independent_r4(self):
        alias_source = ORIGINAL.replace(b"import sqlite3\n", b"import sqlite3 as dbapi\n").replace(
            b"with sqlite3.connect(location)", b"with dbapi.connect(location)")
        candidate = propose(evidence=witness(alias_source),
                            pinned_before=alias_source,
                            consumed_scopes=frozenset())
        self.assertIn(b"contextlib.closing(sqlite3.connect(location))", candidate.source)
        self.assertEqual(candidate.mechanism, "r16-ast-alias-normalization")
        self.assertFalse(candidate.eligible_for_owner)

    def test_original_r13_workflow_embedded_python_is_repaired(self):
        from f139.rsi_r6_known_repair_cycle import WORKFLOW_PATH
        # Real R13 failure class, but synthetic bytes: this is a grammar
        # regression, NOT a replay of an authenticated Windows incident.
        script = (
            "name: R13 scoped source-only test\n"
            "run: |\n"
            "          $script = @'\n"
            "          import sqlite3, tempfile\n"
            "          with tempfile.TemporaryDirectory() as folder:\n"
            "              with sqlite3.connect(folder + '/state.sqlite') as db:\n"
            "                  db.execute('CREATE TABLE t(v INTEGER)')\n"
            "          '@\n"
        ).encode("ascii")
        e = replace(witness(script), target_path=WORKFLOW_PATH)
        candidate = propose(evidence=e, pinned_before=script,
                            consumed_scopes=frozenset())
        self.assertEqual(candidate.mechanism, "r16-embedded-workflow")
        self.assertEqual(candidate.path, WORKFLOW_PATH)
        self.assertIn(b"import contextlib, sqlite3, tempfile", candidate.source)
        self.assertIn(b"contextlib.closing(sqlite3.connect(", candidate.source)
        self.assertIn(b"as db, db:", candidate.source)
        self.assertTrue(candidate.source.startswith(
            b"name: R13 scoped source-only test\nrun: |\n"))
        self.assertFalse(candidate.qualified)
        self.assertFalse(candidate.eligible_for_owner)
        self.assertEqual(candidate.candidate_sha256, digest(candidate.source))

    def test_workflow_path_scope_is_exact_and_unrelated_workflows_denied(self):
        for badpath in (
                ".github/workflows/qualify.yml",
                ".github/workflows/forge-f139-r14-native-output.yml",
                ".github/workflows/forge-f139-r13-owner-continuity-cold-audit.yml.bak",
                ".github/workflows/../../f139/local_controller.py"):
            with self.subTest(badpath=badpath):
                e = replace(witness(), target_path=badpath)
                with self.assertRaisesRegex(RepairDenied, "TARGET_SCOPE_INVALID"):
                    propose(evidence=e, pinned_before=ORIGINAL,
                            consumed_scopes=frozenset())

    def test_existing_f7_policy_error_not_auto_repaired(self):
        forbidden = b"FORGE_PUBLIC_SUBPROCESS_SOURCE_DRIFT:added=['nativediscovery/f7_generations_test.go']"
        e = witness(log=forbidden)
        with self.assertRaisesRegex(RepairDenied, "FAILURE_SIGNATURE_MISMATCH"):
            propose(evidence=e, pinned_before=ORIGINAL, consumed_scopes=frozenset())

    def test_consume_once_then_fails_closed(self):
        e = witness()
        with self.assertRaisesRegex(RepairDenied, "SCOPE_ALREADY_CONSUMED"):
            propose(evidence=e, pinned_before=ORIGINAL,
                    consumed_scopes=frozenset({task_scope(e)}))

    def test_provenance_and_source_drift_fail_closed(self):
        e = witness()
        changes = [
            replace(e, head_sha="not-a-sha"),
            replace(e, run_id=0),
            replace(e, job_id=True),
            replace(e, failed_log=e.failed_log+b"garbage"),
            replace(e, failure_class="G141_ORIGINAL_GO_TEST_OR_RACE_FAILED"),
            replace(e, target_path="../isolationguard/check.py"),
            replace(e, target_path="f139/private\\key.py"),
            replace(e, target_source_sha256="0"*64),
            replace(e, failed_log=LOG.replace(b"WinError 32",b"WinError 5")),
        ]
        for bad in changes:
            with self.subTest(bad=bad):
                with self.assertRaises(RepairDenied):
                    propose(evidence=bad, pinned_before=ORIGINAL,
                            consumed_scopes=frozenset())

    def test_no_arbitrary_repair_from_a_matching_log(self):
        source = b"import os\nprint('not a sqlite connection leak')\n"
        with self.assertRaisesRegex(RepairDenied, "KNOWN_GRAMMAR_NOT_APPLICABLE"):
            propose(evidence=witness(source), pinned_before=source,
                    consumed_scopes=frozenset())

    def test_uncertain_custody_and_invalid_data_denied(self):
        e = witness()
        for scopes in (None, {task_scope(e)}, frozenset({"not-a-sha"})):
            with self.subTest(scopes=scopes), self.assertRaises(RepairDenied):
                propose(evidence=e, pinned_before=ORIGINAL, consumed_scopes=scopes)
        with self.assertRaises(RepairDenied):
            propose(evidence=e, pinned_before=ORIGINAL+b"\n", consumed_scopes=frozenset())


if __name__ == "__main__":
    unittest.main()

"""R4 native source-repair functional controls; no original owner execution."""
from dataclasses import replace
from pathlib import Path
import os
import subprocess
import sys
import unittest

from f139.r16_semantic_repair import FAILURE_CLASS, UnsafeRepair, _repair_python
from f139.rsi_r4_historical_repair import git_blob
from f139.rsi_r4_native_alias_repair import (
    AliasRepairDenied, SCHEMA, digest, propose,
)

ROOT = Path(__file__).resolve().parents[1]


def candidate(source: str, *, path="f139/native_sqlite_repair_specimen.py"):
    return propose(original_source=source.encode("ascii"),
                   expected_sha256=digest(source.encode("ascii")),
                   path=path, failure_class=FAILURE_CLASS)


def specimen(alias="dbapi"):
    return (
        f"import pathlib, sqlite3 as {alias}, tempfile\n"
        'with tempfile.TemporaryDirectory(prefix="forge-r4-native-") as root:\n'
        '    database = pathlib.Path(root) / "state.sqlite"\n'
        f'    with {alias}.connect(str(database)) as writer:\n'
        '        writer.execute("create table x (value integer)")\n'
        '        writer.execute("insert into x values (17)")\n'
        '    try:\n'
        f'        with {alias}.connect(str(database)) as rollback:\n'
        '            rollback.execute("insert into x values (99)")\n'
        '            raise ValueError("expected rollback")\n'
        '    except ValueError: pass\n'
        f'    with {alias}.connect(str(database)) as check:\n'
        '        rows = [row[0] for row in check.execute("select value from x")]\n'
        '        if rows != [17]: raise RuntimeError("R4_COMMIT_OR_ROLLBACK_FAIL")\n'
        'print("R4_NATIVE_COMMIT_ROLLBACK_AND_CLEANUP_PASS")\n'
    )


def run_source(script: bytes):
    return subprocess.run(
        [sys.executable, "-B", "-c", script.decode("ascii")],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=20, check=False)


class NativeAliasSourceRepairTests(unittest.TestCase):
    def test_original_qualified_r16_source_unchanged(self):
        before = (ROOT / "f139/r16_semantic_repair.py").read_bytes()
        self.assertEqual(git_blob(before.replace(b"\r\n", b"\n")),
                         "2b2aee0aa3556546b3f38176f7e9db8b0e234032")
        self.assertEqual(SCHEMA,
                         "forge.f139.rsi-r4.native-sqlite-alias-repair.v1")

    def test_alias_repair_reaches_native_commit_rollback_and_close(self):
        for alias in ("dbapi", "sql_agentfree"):
            with self.subTest(alias=alias):
                original = specimen(alias).encode("ascii")
                with self.assertRaisesRegex(UnsafeRepair, "SQLITE_IMPORT_UNTRUSTED"):
                    _repair_python(original.decode("ascii"))
                output = candidate(original.decode("ascii"))
                self.assertEqual(output.repaired_connections, 3)
                self.assertEqual(output.rule, "r16-ast-alias-normalization")
                self.assertNotEqual(output.original_sha256, output.proposed_sha256)
                self.assertEqual(output.original_sha256, digest(original))
                self.assertEqual(output.proposed_sha256, digest(output.proposed_source))
                self.assertIn(b"contextlib.closing(sqlite3.connect(",
                              output.proposed_source)
                self.assertEqual(output.proposed_source.count(b"contextlib.closing("), 3)
                self.assertEqual(output.proposed_source.count(b", writer:"), 1)
                self.assertEqual(output.proposed_source.count(b", rollback:"), 1)
                self.assertEqual(output.proposed_source.count(b", check:"), 1)
                result = run_source(output.proposed_source)
                self.assertEqual(result.returncode, 0,
                                 result.stderr.decode("utf-8", "replace"))
                self.assertIn(b"R4_NATIVE_COMMIT_ROLLBACK_AND_CLEANUP_PASS",
                              result.stdout)
                self.assertFalse(output.original_owner_activated)
                self.assertFalse(output.independently_qualified)
                self.assertFalse(output.scientific_first_use)
                self.assertFalse(output.rsi_proven)

    def test_static_naive_close_only_does_not_preserve_transaction(self):
        repaired = candidate(specimen()).proposed_source
        # Simulate the conventional naive close-only fix: closing() alone
        # without also entering the SQLite transaction context.
        naive = repaired
        for binding in (b"writer", b"rollback", b"check"):
            naive = naive.replace(b" as " + binding + b", " + binding + b":",
                                  b" as " + binding + b":")
        self.assertNotEqual(naive, repaired)
        compile(naive, "naive_control.py", "exec")
        proc = run_source(naive)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b"R4_COMMIT_OR_ROLLBACK_FAIL", proc.stderr)

    def test_unaliased_repair_parity_and_no_reapplication(self):
        source = ("import sqlite3, tempfile\n"
                  "with tempfile.TemporaryDirectory() as area:\n"
                  "    with sqlite3.connect(area+'/data.sqlite') as connection:\n"
                  "        connection.execute('select 1')\n")
        old, changes = _repair_python(source)
        next_patch = candidate(source)
        self.assertEqual(next_patch.rule, "r16-direct")
        self.assertEqual(next_patch.repaired_connections, changes)
        self.assertEqual(next_patch.proposed_source, old.encode("ascii"))
        with self.assertRaisesRegex(UnsafeRepair, "ALREADY_REPAIRED"):
            candidate(next_patch.proposed_source.decode("ascii"))

    def test_invalid_path_class_source_and_hash_denied(self):
        source = specimen().encode("ascii")
        signed = digest(source)
        for args, reason in (
            ({"path": "../owner.py"}, "TARGET_PATH_NOT_ALLOWED"),
            ({"path": "f139/../local_controller.py"}, "TARGET_PATH_NOT_ALLOWED"),
            ({"path": "f139/foo.sh"}, "TARGET_PATH_NOT_ALLOWED"),
            ({"failure_class": "UNKNOWN"}, "FAILURE_CLASS_NOT_ALLOWED"),
            ({"expected_sha256": "0"*64}, "PINNED_SOURCE_DRIFT"),
            ({"expected_sha256": "not-a-hash"}, "EXPECTED_DIGEST_INVALID"),
            ({"original_source": source+b"\r\n"}, "SOURCE_TYPE_SIZE_OR_EOL"),
            ({"original_source": source+b"#\xff\n",
              "expected_sha256": digest(source+b"#\xff\n")}, "ASCII_ONLY"),
        ):
            with self.subTest(args=args), self.assertRaisesRegex(
                    AliasRepairDenied, reason):
                params = dict(original_source=source,
                              expected_sha256=signed,
                              path="f139/dev/sqlite.py",
                              failure_class=FAILURE_CLASS)
                params.update(args)
                propose(**params)

    def test_reject_alias_outside_with_shadowing_and_untrusted_code(self):
        sample = specimen()
        bads = {
            "ALIAS_REFERENCE_OUTSIDE_WITH": (
                sample.replace("print(\"R4_NATIVE", "print(dbapi.Row)\nprint(\"R4_NATIVE")),
            "PARAMETER_SHADOW": (
                sample + "def hidden(dbapi): return None\n"),
            "CANONICAL_NAME_COLLISION": (
                sample + "sqlite3 = 7\n"),
            "SOURCE_INVALID": (
                sample + "def broken(:\n"),
            "ALIAS_CONTEXT_COMPLEX": (
                sample.replace("as writer:", 'as writer, open(str(database), "w") as f:')),
            "SECOND_IMPORT": sample + "from other_module import dbapi\n",
            "IMPORT_NAME_COLLISION": sample + "import dbapi\n",
            "MATCH_BINDING": sample + (
                'match {"a": 1}:\n'
                '    case {"a": 1, **dbapi}:\n'
                '        pass\n'),
            "DYNAMIC_BINDING": sample + 'exec("dbapi = 1")\n',
        }
        for reason, source in bads.items():
            with self.subTest(reason=reason), self.assertRaisesRegex(
                    AliasRepairDenied, reason):
                candidate(source)

    def test_reject_multiple_imports_and_missing_temp_scope(self):
        sample = specimen()
        for code, reason in (
            (sample.replace("import pathlib,", "import sqlite3 as other\nimport pathlib,"),
             "EXACT_IMPORT_REQUIRED"),
            (sample.replace('tempfile.TemporaryDirectory(prefix="forge-r4-native-")',
                            "pathlib.Path('.')"), "NO_TEMPORARY"),
            (sample.replace(" as dbapi", " as sqlite3"), "ALIAS_INVALID"),
        ):
            with self.subTest(reason=reason), self.assertRaisesRegex(
                    (AliasRepairDenied, UnsafeRepair), reason):
                candidate(code)


if __name__ == "__main__":
    unittest.main()

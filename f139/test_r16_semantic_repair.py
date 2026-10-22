"""R16 fixed-budget proposal synthesis; all specimens are isolated fixtures."""
from __future__ import annotations

import unittest

from f139.r16_semantic_repair import (
    FAILURE_CLASS, UnsafeRepair, synthesize_workflow_repair,
)


def wrap(py):
    source = "".join("          " + line
                     for line in py.splitlines(keepends=True))
    return ("name: original\non:\n  push:\njobs:\n  audit:\n"
            "    run: |\n      $script = @'\n"
            + source + "          '@\n      python -c $script\n")


class R16SynthesisTests(unittest.TestCase):
    def test_heldout_one_connection_new_names(self):
        src = ('import json, os, sqlite3, tempfile\n'
               'with tempfile.TemporaryDirectory() as t:\n'
               '    with sqlite3.connect(t+"/db") as x:\n'
               '        x.execute("select 1")\n')
        candidate, count = synthesize_workflow_repair(wrap(src), FAILURE_CLASS)
        self.assertEqual(count, 1)
        self.assertIn("import contextlib, json, os, sqlite3, tempfile",
                      candidate)
        self.assertIn('contextlib.closing(sqlite3.connect(t+"/db"))',
                      candidate)
        self.assertIn("name: original", candidate)

    def test_heldout_different_expression_with_loop(self):
        src = ('import pathlib, sqlite3, tempfile\n'
               'with tempfile.TemporaryDirectory() as t:\n'
               '    for file in ("a", "b", "c"):\n'
               '        with sqlite3.connect(str(pathlib.Path(t)/file),'
               'timeout=3) as db:\n'
               '            db.execute("select 1")\n')
        candidate, count = synthesize_workflow_repair(wrap(src), FAILURE_CLASS)
        self.assertEqual(count, 1)
        self.assertIn(
            "contextlib.closing(sqlite3.connect("
            "str(pathlib.Path(t)/file),timeout=3))", candidate)

    def test_multiple_distinct_connections(self):
        src = 'import sqlite3, tempfile\nwith tempfile.TemporaryDirectory() as t:\n'
        for name in ("alpha", "beta", "gamma"):
            src += (f'    with sqlite3.connect(t+"/{name}") as db:\n'
                    '        db.execute("select 1")\n')
        candidate, count = synthesize_workflow_repair(wrap(src), FAILURE_CLASS)
        self.assertEqual(count, 3)
        self.assertEqual(candidate.count("contextlib.closing("), 3)

    def test_real_sqlite_file_handle_release_on_unfamiliar_source(self):
        """Native subprocess: Windows baseline must fail; repaired must clean up.

        A SQLite connection used as a context manager commits/rolls back but
        does not close. A live connection blocks Windows temporary-directory
        removal, so this tests actual native resource ownership rather than
        merely checking a generated diff or a golden output string.
        """
        import os
        import subprocess
        import sys
        script = (
            'import pathlib, sqlite3, tempfile\n'
            'with tempfile.TemporaryDirectory(prefix="forge-r17-handle-") as area:\n'
            '    location = pathlib.Path(area) / "heldout.db"\n'
            '    with sqlite3.connect(str(location), timeout=4) as holding:\n'
            '        holding.execute("create table native (value integer)")\n'
            '        holding.execute("insert into native values (17)")\n'
            '    print("R17_SQLITE_WORK_FINISHED")\n'
            'print("R17_TEMPORARY_DIRECTORY_CLEANED")\n'
        )
        original = wrap(script)
        suggested, changed = synthesize_workflow_repair(original, FAILURE_CLASS)
        self.assertEqual(changed, 1)
        self.assertIn('contextlib.closing(sqlite3.connect(str(location), timeout=4))',
                      suggested)
        opener = "      $script = @'\n"
        first = suggested.index(opener) + len(opener)
        last = suggested.index("          '@\n", first)
        repaired_script = "".join(line[10:] for line in
                                  suggested[first:last].splitlines(keepends=True))
        self.assertNotEqual(script, repaired_script)
        before = subprocess.run([sys.executable, "-B", "-c", script],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=False, timeout=20)
        after = subprocess.run([sys.executable, "-B", "-c", repaired_script],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               check=False, timeout=20)
        if os.name == "nt":
            self.assertNotEqual(before.returncode, 0,
                                before.stdout.decode(errors="replace"))
            self.assertIn("PermissionError",
                          before.stderr.decode(errors="replace"))
        else:
            self.assertEqual(before.returncode, 0,
                             before.stderr.decode(errors="replace"))
        self.assertEqual(after.returncode, 0,
                         after.stderr.decode(errors="replace"))
        self.assertIn(b"R17_TEMPORARY_DIRECTORY_CLEANED", after.stdout)

    def test_idempotent_reapplication_refused(self):
        src = ('import sqlite3, tempfile\n'
               'with tempfile.TemporaryDirectory() as d:\n'
               '    with sqlite3.connect(d+"/a") as x:\n'
               '        pass\n')
        repaired, _ = synthesize_workflow_repair(wrap(src), FAILURE_CLASS)
        with self.assertRaisesRegex(UnsafeRepair, "ALREADY_REPAIRED"):
            synthesize_workflow_repair(repaired, FAILURE_CLASS)

    def test_unknown_failure_rejected(self):
        with self.assertRaisesRegex(UnsafeRepair, "UNKNOWN_FAILURE"):
            synthesize_workflow_repair("other", "UNKNOWN_NATIVE_FAILURE")

    def test_no_temporary_directory_rejected(self):
        src = ('import sqlite3\n'
               'with sqlite3.connect("persistent.sqlite") as db:\n'
               '    pass\n')
        with self.assertRaisesRegex(UnsafeRepair, "NO_TEMPORARY"):
            synthesize_workflow_repair(wrap(src), FAILURE_CLASS)

    def test_alias_import_rejected(self):
        src = ('import sqlite3 as sql, tempfile\n'
               'with tempfile.TemporaryDirectory() as d:\n'
               '    with sql.connect(d+"/x") as db:\n'
               '        pass\n')
        with self.assertRaisesRegex(UnsafeRepair, "SQLITE_IMPORT"):
            synthesize_workflow_repair(wrap(src), FAILURE_CLASS)

    def test_complex_context_rejected(self):
        src = ('import sqlite3, tempfile\n'
               'with tempfile.TemporaryDirectory() as d:\n'
               '    with sqlite3.connect(d+"/x") as db, '
               'open(d+"/z","w") as other:\n'
               '        pass\n')
        with self.assertRaisesRegex(UnsafeRepair, "CONNECTION_CONTEXT_COMPLEX"):
            synthesize_workflow_repair(wrap(src), FAILURE_CLASS)

    def test_excessive_rewrites_rejected(self):
        src = 'import sqlite3, tempfile\nwith tempfile.TemporaryDirectory() as d:\n'
        for n in range(7):
            src += (f'    with sqlite3.connect(d+"/{n}") as db:\n'
                    '        pass\n')
        with self.assertRaisesRegex(UnsafeRepair, "NO_BOUNDED"):
            synthesize_workflow_repair(wrap(src), FAILURE_CLASS)

    def test_multiple_scripts_rejected(self):
        src = ('import sqlite3, tempfile\n'
               'with tempfile.TemporaryDirectory() as d:\n'
               '    with sqlite3.connect(d+"/x") as db:\n'
               '        pass\n')
        with self.assertRaisesRegex(UnsafeRepair, "HEREDOC_AMBIGUOUS"):
            synthesize_workflow_repair(wrap(src) + wrap(src), FAILURE_CLASS)


if __name__ == "__main__":
    unittest.main()

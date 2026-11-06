"""Non-network controls for exact tree reconciliation and actual poll extraction."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import unittest

import mpai16_mind_palace_tools_transition_check as m


def fixture():
    entries = [(b"100644", name, pair[1]) for name, pair in m.CURRENT_CHANGES.items()]
    entries += [(b"100644", ("inspection-dependency-%02d.ps1" % i).encode(), "%040x" % (i + 1))
                for i in range(57)]
    old = [(mode, name, m.CURRENT_CHANGES[name][0] if name in m.CURRENT_CHANGES else sha)
           for mode, name, sha in entries
           if name not in m.CURRENT_CHANGES or m.CURRENT_CHANGES[name][0] is not None]
    return entries, m.tree_digest(entries, {}), m.tree_digest(old, {})


class TransitionTests(unittest.TestCase):
    def test_declared_changes_reconcile_every_unchanged_dependency(self):
        entries, current, old = fixture()
        with patch.object(m, "CURRENT_TOOLS", current), patch.object(m, "PIN_FINAL", old):
            m.verify_current_entries(entries)
            changed = deepcopy(entries)
            changed[-1] = (changed[-1][0], changed[-1][1], "f" * 40)
            with self.assertRaisesRegex(RuntimeError, "CURRENT_TREE_DIGEST"):
                m.verify_current_entries(changed)
            # Rebinding the current tree cannot hide an undeclared core edit.
            with patch.object(m, "CURRENT_TOOLS", m.tree_digest(changed, {})):
                with self.assertRaisesRegex(RuntimeError, "UNREVIEWED_DEPENDENCY"):
                    m.verify_current_entries(changed)

    def test_declared_new_file_tamper_or_omission_is_rejected(self):
        entries, _current, old = fixture()
        for mutation in (entries[:-1], entries + [(b"100644", b"unknown.ps1", "f" * 40)],
                         [(a, b, "f" * 40 if b in m.CURRENT_CHANGES else c) for a, b, c in entries]):
            with self.subTest(size=len(mutation)), patch.object(m, "PIN_FINAL", old):
                with self.assertRaises(RuntimeError):
                    m.verify_current_entries(mutation)

    def test_tree_parser_rejects_duplicate_names_and_non_file_modes(self):
        entries, _current, _old = fixture()
        def raw(rows):
            return b"".join(mode + b" blob " + sha.encode() + b"\t" + name + b"\0"
                            for mode, name, sha in rows)
        self.assertEqual(m.parse_ls_tree(raw(entries), 64), entries)
        for rows in (entries[:-1], entries + [entries[0]],
                     [(b"120000", entries[0][1], entries[0][2])] + entries[1:]):
            with self.assertRaises(RuntimeError):
                m.parse_ls_tree(raw(rows), 64)

    def test_poll_can_change_only_the_exact_reviewed_pin(self):
        previous = "unchanged no-write guard\n" + m.PIN_LINE_OLD + "unchanged cleanup\n"
        current = previous.replace(m.PIN_LINE_OLD, m.PIN_LINE_NEW)
        m.approved_poll(previous, current)
        for edited in (current.replace("no-write", "write"), current + "extra\n",
                       current.replace(m.CURRENT_TOOLS, "f" * 40)):
            with self.assertRaises(RuntimeError):
                m.approved_poll(previous, edited)

    def test_extracts_actual_inspection_and_independent_cleanup_without_other_yaml(self):
        workflow = (Path(__file__).resolve().parents[1] / m.POLL).read_text(encoding="utf-8")
        body, cleanup = m.poll_blocks(workflow)
        self.assertTrue(body.startswith("$ErrorActionPreference"))
        self.assertIn("UQ37_NINE_PROTECTED_HASHES_AND_MAIN_REF_STABLE=PASS", body)
        self.assertIn("UQ37_SCHEDULED_READONLY_INSPECTION=PASS", body)
        self.assertIn("UQ40_PRIVATE_SCRATCH_CLEAN=PASS", cleanup)
        self.assertNotIn("shell: pwsh", body + cleanup)
        with self.assertRaises(RuntimeError):
            m.poll_blocks(workflow.replace("        run: |", "        run: >", 1))


if __name__ == "__main__":
    unittest.main()

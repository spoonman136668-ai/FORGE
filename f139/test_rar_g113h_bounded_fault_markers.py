"""RAR-G113H inert source-only fault-marker safety tests; never spawn a child.

Actual G113G was one authorized run, failed closed, and is NOT retried here.
A passing static test or compile-only check is not native execution evidence.
"""
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).with_name("RARG113FOneShotWindowsJob.cs")


class RARG113HBoundedFaultMarkers(unittest.TestCase):
    def setUp(self):
        self.source = SOURCE.read_text(encoding="utf-8")
        match = re.search(
            r'AllowedFailureMarkers\s*=\s*new string\[\]\s*\{(.*?)\};',
            self.source, re.DOTALL,
        )
        self.assertIsNotNone(match, "Explicit native failure-marker allowlist required")
        self.allowed = re.findall(r'"(RAR_G113F_[A-Z_]+)"', match.group(1))

    def test_every_native_failure_marker_whitelisted_exactly_once(self):
        self.assertEqual(len(self.allowed), len(set(self.allowed)))
        self.assertGreaterEqual(len(self.allowed), 15)
        original = self.source[:self.source.index("AllowedFailureMarkers")]
        native_markers = set(re.findall(r'"(RAR_G113F_[A-Z_]+)"', original))
        self.assertEqual(set(self.allowed), native_markers)

    def test_unknown_and_external_text_cannot_be_emitted(self):
        src = self.source
        self.assertIn('if (!(exc is Win32Exception) && !(exc is InvalidOperationException))', src)
        self.assertIn('String.Equals(exc.Message, marker, StringComparison.Ordinal)', src)
        self.assertIn('return "RAR_G113F_UNKNOWN_NATIVE_FAILURE"', src)
        self.assertIn('return "RAR_G113F_UNCLASSIFIED_NATIVE_FAILURE"', src)
        self.assertIn('Console.Error.WriteLine("RAR_G113F_ABORTED:" + BoundedFailureMarker(exc))', src)
        self.assertNotIn('Console.Error.WriteLine(exc.Message)', src)
        self.assertNotIn('Console.Error.WriteLine(exc.ToString())', src)
        self.assertNotIn('exc.GetType().Name', src)

    def test_authority_and_one_shot_interlocks_unchanged(self):
        src = self.source
        self.assertIn('args.Length != 1 || args[0] != "--run-one-shot-offline"', src)
        self.assertIn('Path.Combine(systemDirectory, "cmd.exe")', src)
        self.assertIn(' /d /q /c exit 0', src)
        self.assertIn('Require(AssignProcessToJobObject(job, child.hProcess)', src)
        self.assertIn('Close(ref job);', src)
        self.assertIn('"native_training_cost_qualified\\\":false', src)
        self.assertIn('"scientific_first_use_authorized\\\":false', src)


if __name__ == "__main__":
    unittest.main()

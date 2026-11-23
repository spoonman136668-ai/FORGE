"""Offline boundary tests for opt-in MP-AI05 operational query entrypoint."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from mpai05_recall_cli import retrieve, _write_private

SHA = "a" * 40
TEMPLATE = ("Can you find the saved memory related to "
            "causal memory evidence and explain the original evidence?")


class FakeSnapshot:
    def __init__(self, empty_clean=False):
        self.calls = []
        self.empty_clean = empty_clean

    def recall(self, sha, query, projects, profile):
        self.calls.append((sha, query, projects[:], profile))
        records = [] if self.empty_clean and query == "causal memory evidence" else [
            {"id": "pinned/id", "source_refs": [{"type": "source", "ref": "reviewed"}]}]
        return {"source_sha": sha, "matches": records,
                "scope": projects, "query_used": query}


class OperationalConsumerTests(unittest.TestCase):
    def test_default_off_preserves_query(self):
        s = FakeSnapshot()
        data, receipt = retrieve(s, SHA, TEMPLATE, projects=["Mind-Palace"])
        self.assertEqual(receipt["mode"], "off")
        self.assertEqual(receipt["routing"], "disabled")
        self.assertEqual(data["query_used"], TEMPLATE)
        self.assertEqual(len(s.calls), 1)

    def test_eligible_normalizes_recognized_only(self):
        s = FakeSnapshot()
        data, receipt = retrieve(s, SHA, TEMPLATE, projects=["Mind-Palace"],
                                 mode="eligible")
        self.assertEqual(receipt["routing"], "normalized")
        self.assertEqual(data["query_used"], "causal memory evidence")
        self.assertNotIn(TEMPLATE, repr(receipt))

    def test_eligible_unknown_passes_through(self):
        s = FakeSnapshot()
        query = "How was memory evidence validated?"
        data, receipt = retrieve(s, SHA, query, projects=["Mind-Palace"],
                                 mode="eligible")
        self.assertEqual(receipt["routing"], "unmodified")
        self.assertEqual(data["query_used"], query)

    def test_zero_hit_falls_back(self):
        s = FakeSnapshot(empty_clean=True)
        data, receipt = retrieve(s, SHA, TEMPLATE, projects=["Mind-Palace"],
                                 mode="eligible")
        self.assertEqual(receipt["routing"], "original_fallback")
        self.assertEqual(data["query_used"], TEMPLATE)
        self.assertEqual(len(s.calls), 2)

    def test_shadow_serves_original_and_records_comparison(self):
        s = FakeSnapshot(empty_clean=True)
        data, receipt = retrieve(s, SHA, TEMPLATE, projects=["Mind-Palace"],
                                 mode="shadow")
        self.assertEqual(data["query_used"], TEMPLATE)
        self.assertEqual(receipt["routing"], "disabled")
        self.assertEqual(receipt["shadow_record_count"], 1)
        self.assertFalse(receipt["shadow_changed_top4"])
        self.assertEqual(len(s.calls), 3)  # original + cleaned + fallback original

    def test_source_and_scope_and_profile_enforced(self):
        s = FakeSnapshot()
        for source, scope, profile in [
            ("x", ["Mind-Palace"], "continuation"),
            (SHA, ["Wingless"], "continuation"),
            (SHA, ["Mind-Palace", "Wingless"], "continuation"),
            (SHA, ["Mind-Palace"], "bad"),
        ]:
            with self.subTest(source=source, scope=scope, profile=profile):
                with self.assertRaises(ValueError):
                    retrieve(s, source, TEMPLATE, projects=scope, profile=profile)
        self.assertFalse(s.calls)

    def test_input_limits(self):
        s = FakeSnapshot()
        for q in (" ", "x" * 4097):
            with self.assertRaises(ValueError):
                retrieve(s, SHA, q, projects=["Mind-Palace"])
        self.assertFalse(s.calls)

    def test_malformed_provenance_denied(self):
        class Invalid(FakeSnapshot):
            def recall(self, sha, query, projects, profile):
                return {"source_sha": sha, "matches": [{"id": "bad"}]}
        with self.assertRaises(RuntimeError):
            retrieve(Invalid(), SHA, TEMPLATE, projects=["Mind-Palace"])

    def test_private_result_exclusive_write_and_no_workspace(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as output:
            root = pathlib.Path(source)
            target = pathlib.Path(output) / "receipt.json"
            s = FakeSnapshot()
            result, receipt = retrieve(s, SHA, TEMPLATE, projects=["Mind-Palace"])
            _write_private(str(target), root, result, receipt)
            saved = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(saved["result"], result)
            with self.assertRaises(FileExistsError):
                _write_private(str(target), root, result, receipt)
            with self.assertRaises(ValueError):
                _write_private(str(root / "private.json"), root, result, receipt)
            with self.assertRaises(ValueError):
                _write_private("receipt.json", root, result, receipt)


if __name__ == "__main__":
    unittest.main()

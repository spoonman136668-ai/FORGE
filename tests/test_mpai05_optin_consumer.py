"""Bounded regression for the optional MP-AI05 retrieval consumer; no private source."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from mpai05_query_normalizer import normalize_query
from mpai05_retrieval_consumer import recall_with_normalizer


class Snapshot:
    def __init__(self, *, empty_clean=False):
        self.calls = []
        self.empty_clean = empty_clean

    def recall(self, sha, query, projects, profile):
        self.calls.append((sha, query, list(projects), profile))
        if self.empty_clean and query == "causal memory evidence":
            return {"source_sha": sha, "matches": []}
        return {"source_sha": sha, "matches": [
            {"id": "case/a", "source_refs": [{"type": "git", "ref": "file"}]}
        ], "query": query}


class QueryNormalizerTest(unittest.TestCase):
    phrase = ("Can you find the saved memory related to "
              "causal memory evidence and explain the original evidence?")
    another = ("I am trying to remember something from an earlier conversation about "
               "causal memory evidence. Would you check the context and tell me "
               "whether any relevant notes were recorded?")

    def test_known_templates(self):
        for query in (self.phrase, self.another):
            with self.subTest(query=query):
                x = normalize_query(query)
                self.assertTrue(x.transformed)
                self.assertEqual(x.query, "causal memory evidence")
                self.assertEqual(x.original, query)

    def test_unknown_not_modified(self):
        q = "How did the project make the causal memory decision?"
        x = normalize_query(q)
        self.assertFalse(x.transformed)
        self.assertEqual(x.query, q)

    def test_unsafe_abstention(self):
        q = "Can you find the saved memory related to \n and explain the original evidence?"
        self.assertEqual(normalize_query(q).query, q)
        with self.assertRaises(ValueError):
            normalize_query(" ")

    def test_disabled_is_byte_equivalent(self):
        s = Snapshot()
        expected = s.recall("a" * 40, self.phrase, ["Mind-Palace"], "continuation")
        s.calls.clear()
        x = recall_with_normalizer(s, "a" * 40, self.phrase, ["Mind-Palace"])
        self.assertEqual(x["routing"], "disabled")
        self.assertEqual(x["result"], expected)
        self.assertEqual(len(s.calls), 1)
        self.assertEqual(s.calls[0][1], self.phrase)

    def test_enabled_only_on_known_template(self):
        s = Snapshot()
        x = recall_with_normalizer(s, "a" * 40, self.phrase, ["Mind-Palace"],
                                   enabled=True)
        self.assertEqual(x["routing"], "normalized")
        self.assertEqual(s.calls[0], ("a" * 40, "causal memory evidence",
                                      ["Mind-Palace"], "continuation"))

    def test_unknown_routes_original(self):
        s = Snapshot()
        q = "What do we know about causal memory?"
        x = recall_with_normalizer(s, "a" * 40, q, ["Mind-Palace"], enabled=True)
        self.assertEqual(x["routing"], "unmodified")
        self.assertEqual(s.calls[0][1], q)

    def test_zero_hit_fallback_to_original(self):
        s = Snapshot(empty_clean=True)
        x = recall_with_normalizer(s, "a" * 40, self.phrase, ["Mind-Palace"],
                                   enabled=True)
        self.assertEqual(x["routing"], "original_fallback")
        self.assertEqual([z[1] for z in s.calls],
                         ["causal memory evidence", self.phrase])
        self.assertTrue(x["result"]["matches"])

    def test_scope_and_source_identity_not_rewritten(self):
        s = Snapshot()
        scope = ["Mind-Palace"]
        for enabled in (False, True):
            recall_with_normalizer(s, "b" * 40, self.phrase, scope,
                                   "historical", enabled=enabled)
        self.assertTrue(all(z[0] == "b" * 40 and z[2] == scope
                            and z[3] == "historical" for z in s.calls))


if __name__ == "__main__":
    unittest.main()

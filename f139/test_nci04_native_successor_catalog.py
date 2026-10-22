"""A8E2A4 native succession: only exact ledger-bound old issues may be skipped.

This never uses the real owner, source mutation, GitHub POST or native dispatch.
"""
from __future__ import annotations

import base64
import copy
import json
import unittest

from f139.local_controller import GitHub, F139Error
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import inspect_owner_issue
from test_nci04_owner_issue import issue, MAIN, TARGET, TREE

NEW_MAIN = "9" * 40


def source_issue(source: str, number: int, issue_id: int):
    raw = copy.deepcopy(issue())
    raw["number"], raw["id"] = number, issue_id
    body = json.loads(raw["body"])
    candidate = json.loads(base64.b64decode(body["intent_base64"], validate=True))
    body["source_sha"] = source
    candidate["controller_source_sha"] = source
    body["intent_base64"] = base64.b64encode(canonical(candidate)).decode("ascii")
    raw["body"] = json.dumps(body, sort_keys=True)
    return raw


class NativeSuccessionCatalogTests(unittest.TestCase):
    def setUp(self):
        self.original = source_issue(MAIN, 702, 5951234567)
        self.successor = source_issue(NEW_MAIN, 703, 5951234568)
        old = inspect_owner_issue(
            self.original, protected_main=MAIN,
            authenticated_target_commit=TARGET,
            authenticated_target_tree=TREE)
        self.history = {
            old.number: (old.issue_id, old.source_sha,
                         old.issue_body_sha256, old.ticket)
        }
        self.calls = []
        self.docs = [self.original, self.successor]

    def api(self):
        def runner(args):
            self.calls.append(tuple(args))
            route = args[0]
            if route == (
                "repos/spoonman136668-ai/FORGE/issues?state=open&labels="
                "f139-native-development-eligible&per_page=100&page=1"):
                return json.dumps(self.docs).encode("utf-8")
            if route == (
                "repos/spoonman136668-ai/Wingless/git/commits/" + TARGET):
                return json.dumps({
                    "sha": TARGET, "tree": {"sha": TREE}
                }).encode("utf-8")
            raise AssertionError("UNEXPECTED_READ_ONLY_ROUTE " + route)
        return GitHub(runner=runner)

    def test_original_known_source_ignored_new_source_admitted(self):
        result = self.api().native_eligible_issues(
            NEW_MAIN, historical_issues=self.history)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].number, 703)
        self.assertEqual(result[0].source_sha, NEW_MAIN)
        self.assertEqual(result[0].ticket.split("-")[2], "i703")
        self.assertTrue(all(
            not any("POST" in word for word in args) for args in self.calls))

    def test_only_original_still_labeled_yields_empty_successor_catalog(self):
        self.docs = [self.original]
        self.assertEqual(self.api().native_eligible_issues(
            NEW_MAIN, historical_issues=self.history), [])

    def test_unrecognized_stale_source_still_fails_closed(self):
        with self.assertRaisesRegex(F139Error,"NATIVE_ISSUE_OR_SOURCE_REJECTED"):
            self.api().native_eligible_issues(NEW_MAIN, historical_issues={})

    def test_changed_original_body_never_skipped(self):
        doc = copy.deepcopy(self.original)
        raw = json.loads(doc["body"])
        raw["kind"] = "invalid-historical-rewrite"
        doc["body"] = json.dumps(raw)
        self.docs = [doc, self.successor]
        with self.assertRaises(Exception):
            self.api().native_eligible_issues(
                NEW_MAIN, historical_issues=self.history)

    def test_changed_original_provider_issue_id_never_skipped(self):
        self.docs = [{**self.original,"id":self.original["id"]+11},
                     self.successor]
        with self.assertRaisesRegex(F139Error,"NATIVE_HISTORICAL_ISSUE_DRIFT"):
            self.api().native_eligible_issues(
                NEW_MAIN, historical_issues=self.history)

    def test_historical_ledger_source_or_digest_drift_never_skipped(self):
        for index, wrong in [(1, NEW_MAIN), (2, "f"*64)]:
            with self.subTest(index=index):
                history = list(self.history[702])
                history[index] = wrong
                with self.assertRaises(F139Error):
                    self.api().native_eligible_issues(
                        NEW_MAIN, historical_issues={702:tuple(history)})

    def test_duplicate_issue_cannot_mask_or_replay(self):
        self.docs = [self.original, self.original, self.successor]
        with self.assertRaisesRegex(F139Error,"NATIVE_DUPLICATE_OR_INVALID_ISSUE_IDENTITY"):
            self.api().native_eligible_issues(
                NEW_MAIN, historical_issues=self.history)


if __name__ == "__main__":
    unittest.main()

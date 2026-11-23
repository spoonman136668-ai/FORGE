"""A8E2A4 native succession: only exact ledger-bound old issues may be skipped.

This never uses the real owner, source mutation, GitHub POST or native dispatch.
"""
from __future__ import annotations

import base64
import copy
import json
import unittest
from unittest.mock import patch

from f139.local_controller import GitHub, F139Error
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import inspect_owner_issue
from test_nci04_owner_issue import issue, MAIN, TARGET, TREE

NEW_MAIN = "9" * 40


def source_issue(source: str, number: int, issue_id: int, lane="Wingless"):
    raw = copy.deepcopy(issue(lane))
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
        self.trees = {("Wingless", TARGET): TREE}

    def api(self):
        def runner(args):
            self.calls.append(tuple(args))
            route = args[0]
            prefix = ("repos/spoonman136668-ai/FORGE/issues?state=open&labels="
                      "f139-native-development-eligible&per_page=100&page=")
            if route.startswith(prefix) and route[len(prefix):].isdigit():
                page = int(route[len(prefix):])
                if page > 0:
                    return json.dumps(self.docs[(page-1)*100:page*100]).encode("utf-8")
            for (lane, sha), tree in self.trees.items():
                if route != "repos/spoonman136668-ai/" + lane + "/git/commits/" + sha:
                    continue
                return json.dumps({
                    "sha": sha, "tree": {"sha": tree}
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
        self.assertEqual(sum('/git/commits/' in args[0] for args in self.calls), 1)

    def test_reuse_expires_after_each_catalog_call(self):
        api = self.api()
        for _ in range(2):
            self.assertEqual(len(api.native_eligible_issues(
                NEW_MAIN, historical_issues=self.history)), 1)
        self.assertEqual(sum('/git/commits/' in args[0] for args in self.calls), 2)

    def test_two_page_catalog_shape_reads_fourteen_commits_for_135_issues(self):
        # Synthetic valid bodies with the observed public catalog's multiplicity;
        # this is a GET-count control, not an original-owner admission replay.
        sizes = (111, 3, 2, 1, 2, 1, 4, 1, 1, 1, 1, 3, 1, 3)
        self.docs, self.trees = [], {}
        for index, size in enumerate(sizes):
            sha = format(index + 100, '040x')
            for _ in range(size):
                n = len(self.docs)
                doc = source_issue(NEW_MAIN, 1000 + n, 5951240000 + n)
                body = json.loads(doc['body'])
                intent = json.loads(base64.b64decode(body['intent_base64']))
                intent['target_commit'] = sha
                body['intent_base64'] = base64.b64encode(canonical(intent)).decode('ascii')
                doc['body'] = json.dumps(body, sort_keys=True)
                self.docs.append(doc)
            self.trees[("Wingless", sha)] = TREE
        result = self.api().native_eligible_issues(NEW_MAIN)
        self.assertEqual([item.number for item in result], list(range(1000, 1135)))
        self.assertEqual(sum('/git/commits/' in args[0] for args in self.calls), 14)
        self.assertEqual(len(self.calls), 16)


    def test_exactly_200_open_issues_is_complete_not_truncated(self):
        self.docs = [source_issue(NEW_MAIN, 1000+i, 5951240000+i)
                     for i in range(200)]
        result = self.api().native_eligible_issues(NEW_MAIN)
        self.assertEqual(len(result), 200)
        pages = [args[0] for args in self.calls if
                 "/issues?state=open&labels=" in args[0]]
        self.assertEqual(len(pages), 3)
        self.assertTrue(pages[-1].endswith("page=3"))
        self.assertEqual(sum("/git/commits/" in args[0]
                             for args in self.calls), 1)
        self.assertTrue(all(not any("POST" in word for word in args)
                            for args in self.calls))

    def test_201st_issue_is_accessible_and_cross_page_duplicate_is_denied(self):
        self.docs = [source_issue(NEW_MAIN, 1000+i, 5951240000+i)
                     for i in range(201)]
        result = self.api().native_eligible_issues(NEW_MAIN)
        self.assertEqual(len(result), 201)
        self.assertEqual(result[-1].number, 1200)
        self.assertTrue(any(args[0].endswith("page=3")
                            for args in self.calls))
        self.docs[-1]["id"] = self.docs[0]["id"]
        with self.assertRaisesRegex(F139Error,
                                    "NATIVE_DUPLICATE_OR_INVALID_ISSUE_IDENTITY"):
            self.api().native_eligible_issues(NEW_MAIN)

    def test_bounded_catalog_sentinel_distinguishes_exact_cap_from_overflow(self):
        self.docs = [source_issue(NEW_MAIN, 1000+i, 5951240000+i)
                     for i in range(200)]
        with patch("f139.local_controller.NATIVE_ISSUE_CATALOG_MAX_PAGES", 2):
            self.assertEqual(len(self.api().native_eligible_issues(NEW_MAIN)), 200)
            self.docs.append(source_issue(NEW_MAIN, 1200, 5951240200))
            with self.assertRaisesRegex(F139Error, "NATIVE_CATALOG_TRUNCATED"):
                self.api().native_eligible_issues(NEW_MAIN)

    def test_identical_sha_in_other_repository_cannot_reuse_tree(self):
        other = source_issue(NEW_MAIN, 704, 5951234569, lane="Yggdrasil")
        self.docs = [self.successor, other]
        self.trees[("Yggdrasil", TARGET)] = 'd' * 40
        with self.assertRaisesRegex(F139Error, 'NATIVE_ISSUE_OR_SOURCE_REJECTED'):
            self.api().native_eligible_issues(NEW_MAIN)
        self.assertEqual(sum('/git/commits/' in args[0] for args in self.calls), 2)

    def test_different_commit_in_same_repository_is_independently_read(self):
        other = source_issue(NEW_MAIN, 704, 5951234569)
        body = json.loads(other['body'])
        intent = json.loads(base64.b64decode(body['intent_base64']))
        intent['target_commit'] = 'e' * 40
        body['intent_base64'] = base64.b64encode(canonical(intent)).decode('ascii')
        other['body'] = json.dumps(body, sort_keys=True)
        self.docs = [self.successor, other]
        self.trees[("Wingless", 'e' * 40)] = TREE
        self.assertEqual(len(self.api().native_eligible_issues(NEW_MAIN)), 2)
        self.assertEqual(sum('/git/commits/' in args[0] for args in self.calls), 2)

    def test_changed_body_after_reused_target_is_still_rejected(self):
        bad = copy.deepcopy(self.successor)
        bad['number'], bad['id'] = 704, 5951234569
        body = json.loads(bad['body'])
        body['scientific_first_use'] = True
        bad['body'] = json.dumps(body, sort_keys=True)
        self.docs = [self.successor, bad]
        with self.assertRaisesRegex(F139Error, 'NATIVE_ISSUE_OR_SOURCE_REJECTED'):
            self.api().native_eligible_issues(NEW_MAIN)
        self.assertEqual(sum('/git/commits/' in args[0] for args in self.calls), 1)

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

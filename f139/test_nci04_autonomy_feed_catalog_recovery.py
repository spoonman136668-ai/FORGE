"""Bounded GET-only F139 native-feed PR pagination recovery controls.

Source-only fixtures; no actual GitHub writes, original SQLite, controller,
new scheduler, user data or scientific first-use.
"""
from __future__ import annotations

import unittest

from f139.nci04_autonomy_feed import (
    NativeFeedDenied, prepare_feed, read_bounded_pr_catalog)
from f139.test_nci04_autonomy_feed import FakeProvider


PREFIX = "repos/spoonman136668-ai/Wingless/pulls?state=open&per_page=50&page="


class ShiftingCatalog(FakeProvider):
    def __init__(self, *, permanent=False, invalid=False):
        super().__init__()
        self.scan = 0
        self.calls = []
        self.permanent = permanent
        self.invalid = invalid

    def get(self, route):
        if route.startswith(PREFIX):
            page = int(route[len(PREFIX):])
            self.calls.append(page)
            if page == 1:
                self.scan += 1
                return [{"number": 2000 - n, "title": "ordinary"}
                        for n in range(50)]
            if page == 2:
                if self.invalid:
                    return [{"number": 1900 - n, "title": "ordinary"}
                            for n in range(51)]
                if self.scan == 1 or self.permanent:
                    # The new/closed PR moved the page boundary: duplicate
                    # number 1951 makes this snapshot unsafe.
                    return [{"number": 1951, "title": "ordinary"},
                            self.pr]
                return [{"number": 1950 - n, "title": "ordinary"}
                        for n in range(49)] + [self.pr]
        return super().get(route)


class BoundedCatalogRecoveryTests(unittest.TestCase):
    def test_one_torn_snapshot_recovers_original_owned_candidate(self):
        provider = ShiftingCatalog()
        used = set()
        report = prepare_feed(provider.get, source_sha=provider.source,
                              existing_candidate_identities=used)
        self.assertEqual(provider.calls, [1, 2, 1, 2])
        self.assertEqual([c["pr_number"] for c in report["candidates"]],
                         [383])
        self.assertEqual(report["rejected"], [])
        self.assertEqual(len(used), 1)
        self.assertEqual(report["candidates"][0]["scientific_first_use"],
                         False)

    def test_persistently_torn_catalog_fails_without_candidate_authentication(self):
        provider = ShiftingCatalog(permanent=True)
        used = set()
        visited = []
        def get(route):
            visited.append(route)
            return provider.get(route)
        with self.assertRaisesRegex(
                NativeFeedDenied, "PR_CATALOG_PAGE_DRIFT"):
            prepare_feed(get, source_sha=provider.source,
                         existing_candidate_identities=used)
        self.assertEqual(provider.calls, [1, 2, 1, 2])
        self.assertEqual(used, set())
        self.assertFalse(any("/pulls/383" in r for r in visited))
        self.assertFalse(any("/issues/807/comments" in r for r in visited))

    def test_oversized_second_page_denied_without_replay(self):
        provider = ShiftingCatalog(invalid=True)
        with self.assertRaisesRegex(NativeFeedDenied,
                                    "PR_CATALOG_INVALID"):
            prepare_feed(provider.get, source_sha=provider.source,
                         existing_candidate_identities=set())
        self.assertEqual(provider.calls, [1, 2])

    def test_short_first_page_is_still_one_read(self):
        provider = FakeProvider()
        seen = []
        def get(route):
            seen.append(route)
            return provider.get(route)
        docs = read_bounded_pr_catalog(
            get, "spoonman136668-ai/Wingless")
        self.assertEqual(docs, [provider.pr])
        self.assertEqual(seen, [PREFIX + "1"])

    def test_catalog_recovery_does_not_consume_repeated_provider_exception(self):
        provider = ShiftingCatalog()
        def get(route):
            if route == PREFIX + "2":
                raise RuntimeError("F139_GITHUB_API_FAILED")
            return provider.get(route)
        with self.assertRaisesRegex(RuntimeError, "GITHUB_API_FAILED"):
            read_bounded_pr_catalog(get, "spoonman136668-ai/Wingless")
        self.assertEqual(provider.calls, [1])
        # Transport owns its existing bounded GET retry; the feeder does
        # not obscure provider faults or try a new candidate source.

    def test_first_page_duplicate_also_cannot_proceed(self):
        provider = ShiftingCatalog(permanent=True)
        original_get = provider.get
        def get(route):
            if route == PREFIX + "1":
                provider.calls.append(1)
                return [{"number": 777, "title": "ordinary"}
                        for _ in range(50)]
            if route == PREFIX + "2":
                provider.calls.append(2)
                return []
            return original_get(route)
        with self.assertRaisesRegex(NativeFeedDenied,
                                    "PR_CATALOG_PAGE_DRIFT"):
            read_bounded_pr_catalog(get, "spoonman136668-ai/Wingless")
        self.assertEqual(provider.calls, [1, 2, 1, 2])


if __name__ == "__main__":
    unittest.main()

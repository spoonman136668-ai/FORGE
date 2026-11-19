"""Offline owner-policy/comment GET-route and fail-closed pagination tests."""
from __future__ import annotations

import copy
import json
import unittest

from f139.local_controller import GitHub
from f139.nci04_phase_comment_read import (
    COMMENT_ROUTE, ISSUE_ROUTE, MAX_PAGES, PhaseCommentReadDenied,
    inspect_pending_owner_intents,
)
from f139.nci04_phase_manual_intent import ISSUE_URL, OWNER_ID
from f139.test_nci04_phase_manual_intent import comment, intent, SOURCE

EPOCH = 41


def policy():
    return {
        "schema": "forge.f139.native-autonomy-feed-owner-policy.v1",
        "enabled": True, "source_sha": SOURCE,
        "title_prefix": "F139 autonomy DEV:",
        "lanes": ["Wingless", "Yggdrasil", "TTT-Hybrid"],
        "max_issue_creations_per_cycle": 2,
        "require_owner_authored_pr": True,
        "require_single_head_commit_delta": True,
        "require_single_allowed_source_file": True,
        "scientific_first_use": False, "paid_model_calls": 0,
        "accepted_ref_mutations": 0, "new_controller": False,
        "new_scheduler": False, "new_queue": False,
    }


def issue():
    return {
        "number": 807, "id": 6005668173, "state": "open",
        "user": {"login": "spoonman136668-ai", "id": OWNER_ID},
        "author_association": "OWNER",
        "body": json.dumps(policy(), sort_keys=True),
    }


def steering(comment_id=111, mode="HOLD", lane=None):
    row = comment(intent(mode=mode, lane=lane, source=SOURCE, epoch=EPOCH))
    row["id"] = comment_id
    return row


def discussion(comment_id=112, body="Ordinary discussion, not steering"):
    return {"id": comment_id, "issue_url": ISSUE_URL, "body": body,
            "user": {"login": "unrelated", "id": 123},
            "author_association": "NONE",
            "created_at": "2026-11-18T23:59:00Z",
            "updated_at": "2026-11-18T23:59:00Z"}


def provider(*, remote_issue=None, pages=None):
    calls = []
    if remote_issue is None:
        remote_issue = issue()
    if pages is None:
        pages = [[steering()], []]

    def run(args):
        if type(args) is not list or len(args) != 1:
            raise AssertionError("unexpected non-GET GH route")
        route = args[0]
        calls.append(route)
        if route == ISSUE_ROUTE:
            return json.dumps(remote_issue).encode()
        if route.startswith(COMMENT_ROUTE):
            page = int(route[len(COMMENT_ROUTE):])
            if 1 <= page <= len(pages):
                return json.dumps(pages[page - 1]).encode()
            return b"[]"
        raise AssertionError("unexpected GH route")

    return GitHub(runner=run), calls


def inspect(p, *, consumed=frozenset(), source=SOURCE,
            protected=SOURCE, epoch=EPOCH):
    return inspect_pending_owner_intents(
        provider=p, installed_source_sha=source,
        protected_main_sha=protected,
        owner_epoch=epoch, consumed_comment_ids=consumed)


class PhaseCommentReadTests(unittest.TestCase):
    def test_exact_owner_policy_and_comment_use_only_existing_get(self):
        p, calls = provider()
        report = inspect(p)
        self.assertEqual(calls, [ISSUE_ROUTE, COMMENT_ROUTE + "1"])
        self.assertEqual(report["comments_scanned"], 1)
        self.assertEqual(len(report["pending"]), 1)
        self.assertEqual(report["pending"][0]["mode"], "HOLD")
        for key in ("owner_admitted", "dispatch_authorized",
                    "scientific_first_use", "self_source_mutation",
                    "accepted_ref_mutation", "new_controller"):
            self.assertFalse(report[key])

    def test_unrelated_discussion_ignored_without_promoting_it(self):
        p, _ = provider(pages=[[discussion(110), steering(111)], []])
        report = inspect(p)
        self.assertEqual(report["comments_scanned"], 2)
        self.assertEqual([x["comment_id"] for x in report["pending"]], [111])

    def test_first_unconsumed_stays_first_after_replaying_ledger_ids(self):
        p, _ = provider(pages=[[steering(110), steering(112, "AUTO")], []])
        a = inspect(p)
        self.assertEqual([x["mode"] for x in a["pending"]], ["HOLD", "AUTO"])
        b = inspect(p, consumed=frozenset({110}))
        self.assertEqual([x["mode"] for x in b["pending"]], ["AUTO"])

    def test_pagination_is_exhaustive_not_one_page_guess(self):
        first = [discussion(i + 1) for i in range(100)]
        second = [steering(101, "RESEARCH", "Wingless")]
        p, calls = provider(pages=[first, second])
        report = inspect(p)
        self.assertEqual(report["comments_scanned"], 101)
        self.assertEqual(report["pending"][0]["lane"], "Wingless")
        self.assertEqual(calls, [ISSUE_ROUTE, COMMENT_ROUTE + "1",
                                 COMMENT_ROUTE + "2"])

    def test_full_catalog_limit_denied_not_silently_truncated(self):
        pages = [[discussion(i + 1 + 100 * page) for i in range(100)]
                 for page in range(MAX_PAGES)]
        p, _ = provider(pages=pages)
        with self.assertRaisesRegex(PhaseCommentReadDenied,
                                    "COMMENT_CATALOG_NOT_EXHAUSTIVE"):
            inspect(p)

    def test_policy_wrong_issue_owner_or_closed_denied(self):
        for change in ({"number": 808}, {"state": "closed"},
                       {"author_association": "COLLABORATOR"},
                       {"user": {"login": "other", "id": OWNER_ID}}):
            with self.subTest(change=change):
                altered = issue()
                altered.update(change)
                p, calls = provider(remote_issue=altered)
                with self.assertRaises(PhaseCommentReadDenied):
                    inspect(p)
                self.assertEqual(calls, [ISSUE_ROUTE])

    def test_policy_changed_source_or_enabled_denied(self):
        for change in ({"source_sha": "b" * 40},
                       {"enabled": False},
                       {"scientific_first_use": True},
                       {"accepted_ref_mutations": 1},
                       {"new_scheduler": True}):
            with self.subTest(change=change):
                altered = issue()
                obj = policy()
                obj.update(change)
                altered["body"] = json.dumps(obj)
                p, calls = provider(remote_issue=altered)
                with self.assertRaises(PhaseCommentReadDenied):
                    inspect(p)
                self.assertEqual(calls, [ISSUE_ROUTE])

    def test_policy_extra_field_and_duplicate_json_key_denied(self):
        altered = issue()
        obj = policy()
        obj["deployment_authorized"] = True
        altered["body"] = json.dumps(obj)
        p, _ = provider(remote_issue=altered)
        with self.assertRaises(PhaseCommentReadDenied):
            inspect(p)
        altered["body"] = issue()["body"][:-1] + ',"enabled":true}'
        p, _ = provider(remote_issue=altered)
        with self.assertRaises(PhaseCommentReadDenied):
            inspect(p)

    def test_foreign_prefixed_command_denied_not_silently_ignored(self):
        bad = steering()
        bad["user"] = {"login": "foreign", "id": 99}
        p, _ = provider(pages=[[bad]])
        with self.assertRaisesRegex(PhaseCommentReadDenied,
                                    "UNAUTHENTICATED_INTENT"):
            inspect(p)

    def test_edited_or_wrong_source_comment_denied(self):
        for change in ({"updated_at": "2026-11-19T00:00:00Z"},
                       {"body": "F139-STEER-V1 {}"}):
            with self.subTest(change=change):
                raw = steering()
                raw.update(change)
                p, _ = provider(pages=[[raw]])
                with self.assertRaises(PhaseCommentReadDenied):
                    inspect(p)

    def test_duplicate_or_out_of_order_comment_ids_denied(self):
        for rows in ([steering(10), steering(10)],
                     [steering(20), steering(19)]):
            p, _ = provider(pages=[rows])
            with self.assertRaisesRegex(PhaseCommentReadDenied,
                                        "COMMENT_SEQUENCE_OR_ISSUE_DRIFT"):
                inspect(p)

    def test_wrong_issue_url_and_invalid_catalog_page_denied(self):
        bad = steering()
        bad["issue_url"] = ISSUE_URL.replace("807", "808")
        p, _ = provider(pages=[[bad]])
        with self.assertRaises(PhaseCommentReadDenied):
            inspect(p)
        p, _ = provider(pages=[{"not": "a list"}])
        with self.assertRaises(PhaseCommentReadDenied):
            inspect(p)

    def test_preflight_source_epoch_and_consumed_type_before_any_read(self):
        for opts in ({"protected": "b" * 40}, {"source": "BAD"},
                     {"epoch": True}, {"consumed": {111}}):
            with self.subTest(opts=opts):
                p, calls = provider()
                with self.assertRaises(PhaseCommentReadDenied):
                    inspect(p, **opts)
                self.assertEqual(calls, [])

    def test_requires_original_git_hub_type(self):
        with self.assertRaises(PhaseCommentReadDenied):
            inspect(object())

    def test_empty_catalog_does_not_invent_manual_commands(self):
        p, calls = provider(pages=[[]])
        report = inspect(p)
        self.assertEqual(report["pending"], ())
        self.assertEqual(calls, [ISSUE_ROUTE, COMMENT_ROUTE + "1"])


if __name__ == "__main__":
    unittest.main()

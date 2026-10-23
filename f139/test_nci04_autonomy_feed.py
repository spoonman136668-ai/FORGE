from __future__ import annotations
import base64
import hashlib
import json
import unittest

from f139.local_controller import GitHub
from f139.nci04_autonomy_feed import (
    POLICY_ISSUE, POLICY_SCHEMA, TITLE_PREFIX, NativeFeedDenied,
    inspect_policy, prepare_feed,
)


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class FakeProvider:
    def __init__(self):
        self.source = "a" * 40
        self.parent = "b" * 40
        self.head = "c" * 40
        self.parent_tree = "d" * 40
        self.head_tree = "e" * 40
        self.path = "cognition/continual.go"
        self.before = b"package cognition\nfunc Old(){}\n"
        self.after = b"package cognition\nfunc Old(){ panic(\"bounded\") }\n"
        self.pr = {
            "number": 383, "id": 900383, "state": "open", "draft": True,
            "title": TITLE_PREFIX + " bounded owner candidate",
            "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {"sha": self.head,
                     "repo": {"full_name": "spoonman136668-ai/Wingless"}},
            "base": {"sha": "f" * 40},
        }
        self.policy = {
            "schema": POLICY_SCHEMA, "enabled": True, "source_sha": self.source,
            "title_prefix": TITLE_PREFIX, "lanes": ["Wingless", "Yggdrasil"],
            "max_issue_creations_per_cycle": 2,
            "require_owner_authored_pr": True,
            "require_single_head_commit_delta": True,
            "require_single_allowed_source_file": True,
            "scientific_first_use": False, "paid_model_calls": 0,
            "accepted_ref_mutations": 0, "new_controller": False,
            "new_scheduler": False, "new_queue": False,
        }

    def issue(self):
        return {
            "number": POLICY_ISSUE, "id": 807, "state": "open",
            "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "body": json.dumps(self.policy, separators=(",", ":")),
        }

    def content(self, raw):
        return {"type": "file", "encoding": "base64", "size": len(raw),
                "sha": blob(raw), "content": base64.b64encode(raw).decode("ascii")}

    def get(self, route):
        if route == "repos/spoonman136668-ai/FORGE/issues/807":
            return self.issue()
        if route == "repos/spoonman136668-ai/Wingless/pulls?state=open&per_page=100&page=1":
            return [self.pr]
        if route == "repos/spoonman136668-ai/Yggdrasil/pulls?state=open&per_page=100&page=1":
            return []
        if route == "repos/spoonman136668-ai/Wingless/pulls/383":
            return self.pr
        if route == "repos/spoonman136668-ai/Wingless/git/commits/" + self.head:
            return {"sha": self.head, "tree": {"sha": self.head_tree},
                    "parents": [{"sha": self.parent}]}
        if route == "repos/spoonman136668-ai/Wingless/git/commits/" + self.parent:
            return {"sha": self.parent, "tree": {"sha": self.parent_tree},
                    "parents": [{"sha": "1" * 40}]}
        if route == ("repos/spoonman136668-ai/Wingless/compare/" +
                     self.parent + "..." + self.head):
            return {
                "status": "ahead", "ahead_by": 1, "behind_by": 0,
                "total_commits": 1,
                "files": [{"status": "modified", "changes": 1,
                           "filename": self.path, "sha": blob(self.after)}],
            }
        if route == ("repos/spoonman136668-ai/Wingless/contents/" +
                     self.path + "?ref=" + self.parent):
            return self.content(self.before)
        if route == ("repos/spoonman136668-ai/Wingless/contents/" +
                     self.path + "?ref=" + self.head):
            return self.content(self.after)
        raise AssertionError("unexpected route " + route)


class NativeAutonomyFeedTests(unittest.TestCase):
    def test_enabled_owner_single_commit_source_candidate_compiles_v1_issue(self):
        p = FakeProvider()
        report = prepare_feed(p.get, source_sha=p.source,
                              existing_candidate_identities=set())
        self.assertTrue(report["enabled"])
        self.assertEqual(len(report["candidates"]), 1)
        self.assertEqual(report["rejected"], [])
        c = report["candidates"][0]
        self.assertEqual(c["pr_number"], 383)
        self.assertEqual(c["lane"], "Wingless")
        body = json.loads(c["issue_body"])
        self.assertEqual(body["schema"],
                         "forge.f139.nci04.owner-native-development.v1")
        self.assertFalse(body["scientific_first_use"])
        self.assertEqual(body["paid_model_calls"], 0)
        intent = json.loads(base64.b64decode(body["intent_base64"], validate=True))
        self.assertEqual(intent["target_commit"], p.parent)
        self.assertEqual(intent["target_tree_sha"], p.parent_tree)
        self.assertEqual(intent["path"], p.path)
        self.assertEqual(base64.b64decode(intent["after_base64"]), p.after)
        self.assertFalse(intent["scientific_first_use"])
        self.assertEqual(intent["accepted_ref_mutations"], 0)
        self.assertEqual(intent["paid_api_calls"], 0)

    def test_disabled_policy_is_inert(self):
        p = FakeProvider()
        p.policy["enabled"] = False
        self.assertEqual(
            prepare_feed(p.get, source_sha=p.source,
                         existing_candidate_identities=set()),
            {"enabled": False, "candidates": [], "rejected": []})

    def test_policy_source_drift_fails_closed(self):
        p = FakeProvider()
        with self.assertRaisesRegex(NativeFeedDenied, "POLICY_SCOPE_DRIFT"):
            prepare_feed(p.get, source_sha="9" * 40,
                         existing_candidate_identities=set())

    def test_non_owner_matching_pr_is_rejected_not_executed(self):
        p = FakeProvider()
        p.pr["user"] = {"login": "attacker"}
        report = prepare_feed(p.get, source_sha=p.source,
                              existing_candidate_identities=set())
        self.assertEqual(report["candidates"], [])
        self.assertRegex(report["rejected"][0]["reason"],
                         "PR_NOT_EXPLICIT_OWNER_CANDIDATE")

    def test_multi_file_or_multi_commit_delta_is_rejected(self):
        p = FakeProvider()
        original = p.get
        def get(route):
            value = original(route)
            if "/compare/" in route:
                value = dict(value, total_commits=2, ahead_by=2)
            return value
        report = prepare_feed(get, source_sha=p.source,
                              existing_candidate_identities=set())
        self.assertEqual(report["candidates"], [])
        self.assertRegex(report["rejected"][0]["reason"],
                         "HEAD_DELTA_NOT_EXACTLY_ONE_COMMIT_FILE")

    def test_disallowed_source_path_is_rejected(self):
        p = FakeProvider()
        p.path = ".github/workflows/pwn.yml"
        report = prepare_feed(p.get, source_sha=p.source,
                              existing_candidate_identities=set())
        self.assertEqual(report["candidates"], [])
        self.assertRegex(report["rejected"][0]["reason"],
                         "HEAD_FILE_NOT_ALLOWED_MODIFICATION")

    def test_existing_exact_intent_is_deduped(self):
        p = FakeProvider()
        first = prepare_feed(p.get, source_sha=p.source,
                             existing_candidate_identities=set())
        known = {first["candidates"][0]["candidate_identity"]}
        second = prepare_feed(p.get, source_sha=p.source,
                              existing_candidate_identities=known)
        self.assertEqual(second["candidates"], [])

    def test_same_patch_dedupes_even_if_provenance_intent_changes(self):
        p = FakeProvider()
        first = prepare_feed(p.get, source_sha=p.source,
                             existing_candidate_identities=set())
        identity = first["candidates"][0]["candidate_identity"]
        # Dedupe is the immutable patch, not compiler metadata/intent bytes.
        self.assertEqual(
            prepare_feed(p.get, source_sha=p.source,
                         existing_candidate_identities={identity})["candidates"],
            [])

    def test_nonprefixed_owner_pr_is_ignored(self):
        p = FakeProvider()
        p.pr["title"] = "ordinary draft"
        report = prepare_feed(p.get, source_sha=p.source,
                              existing_candidate_identities=set())
        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["rejected"], [])

    def test_provider_compare_route_allowed_but_path_traversal_denied(self):
        seen = []
        api = GitHub(runner=lambda args: (
            seen.append(args[0]) or b'{"status":"ahead"}'))
        route = ("repos/spoonman136668-ai/Wingless/compare/" +
                 "a"*40 + "..." + "b"*40)
        self.assertEqual(api.native_repo_get(route), {"status": "ahead"})
        self.assertEqual(seen, [route])
        with self.assertRaisesRegex(Exception, "NATIVE_FEED_ROUTE_INVALID"):
            api.native_repo_get(
                "repos/spoonman136668-ai/Wingless/contents/../secret")

    def test_policy_cannot_turn_on_science_or_new_scheduler(self):
        p = FakeProvider()
        for field, value in (("scientific_first_use", True),
                             ("paid_model_calls", 1),
                             ("accepted_ref_mutations", 1),
                             ("new_controller", True),
                             ("new_scheduler", True),
                             ("new_queue", True),
                             ("max_issue_creations_per_cycle", 3)):
            q = FakeProvider()
            q.policy[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                    NativeFeedDenied, "POLICY_SCOPE_DRIFT"):
                inspect_policy(q.issue(), q.source)


if __name__ == "__main__":
    unittest.main()

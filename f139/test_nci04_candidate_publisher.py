"""Adversarial G2 owner-only publisher tests: no real network writes."""
from __future__ import annotations

import base64
import hashlib
import json
import unittest

from f139.nci04_candidate_producer import candidate_mechanism_identity
from f139.nci04_candidate_publisher import (
    PublisherDenied, publish_single_draft, publisher_preflight,
)
from f139.test_nci04_candidate_producer import SOURCE


def blob_id(raw):
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\0" + raw
    ).hexdigest()


class FakeOriginalOwner:
    repo = "spoonman136668-ai/Yggdrasil"
    path = "yggdrasil/public_causal_cells.py"
    source = "6" * 40
    parent = "9" * 40
    tree = "3" * 40
    history = "e" * 64

    def __init__(self):
        self.parent_data = SOURCE
        self.head_data = None
        self.head_sha = None
        self.head_tree = "4" * 40
        self.reference = None
        self.pr = None
        self.write_calls = []
        self.original_owner = True
        self.fail_after_reference = False

    def get(self, route):
        if route == "repos/spoonman136668-ai/FORGE/issues/807":
            return {
                "number": 807, "state": "open",
                "author_association": "OWNER",
                "user": {"login": "spoonman136668-ai"},
                "body": json.dumps({
                    "schema": "forge.f139.native-autonomy-feed-owner-policy.v1",
                    "enabled": True, "source_sha": self.source,
                    "title_prefix": "F139 autonomy DEV:",
                    "lanes": ["Wingless", "Yggdrasil"],
                    "max_issue_creations_per_cycle": 2,
                    "require_owner_authored_pr": True,
                    "require_single_head_commit_delta": True,
                    "require_single_allowed_source_file": True,
                    "scientific_first_use": False, "paid_model_calls": 0,
                    "accepted_ref_mutations": 0,
                    "new_controller": False, "new_scheduler": False,
                    "new_queue": False,
                }),
            }
        if route == "repos/spoonman136668-ai/FORGE/branches/main":
            return {"protected": True, "commit": {"sha": self.source}}
        if route == f"repos/{self.repo}/git/commits/{self.parent}":
            return {"sha": self.parent, "tree": {"sha": self.tree},
                    "parents": [{"sha": "8"*40}]}
        if route == f"repos/{self.repo}/git/commits/{self.head_sha}":
            return {"sha": self.head_sha, "tree": {"sha": self.head_tree},
                    "parents": [{"sha": self.parent}]}
        if route == f"repos/{self.repo}/contents/{self.path}?ref={self.parent}":
            return self.content(self.parent_data)
        if route == f"repos/{self.repo}/contents/{self.path}?ref={self.head_sha}":
            return self.content(self.head_data)
        if route.startswith(f"repos/{self.repo}/git/matching-refs/heads/"):
            return [] if self.reference is None else [
                {"ref": self.reference, "object": {"sha": self.parent}}]
        if route == f"repos/{self.repo}/pulls?state=all&per_page=100&page=1":
            return [] if self.pr is None else [self.pr]
        if route == f"repos/{self.repo}/pulls?state=open&per_page=100&page=1":
            return [] if self.pr is None else [self.pr]
        if route == f"repos/{self.repo}/pulls/488":
            return self.pr
        if route == f"repos/{self.repo}/compare/{self.parent}...{self.head_sha}":
            return {
                "status": "ahead", "ahead_by": 1, "behind_by": 0,
                "total_commits": 1,
                "files": [{"filename": self.path, "status": "modified",
                           "changes": 23, "sha": blob_id(self.head_data)}],
            }
        raise AssertionError("unexpected GET: "+route)

    @staticmethod
    def content(raw):
        return {
            "type": "file", "encoding": "base64", "size": len(raw),
            "sha": blob_id(raw),
            "content": base64.b64encode(raw).decode(),
        }

    def write(self, method, route, payload):
        self.write_calls.append((method, route))
        if method == "POST" and route == f"repos/{self.repo}/git/refs":
            assert self.reference is None
            assert payload["sha"] == self.parent
            self.reference = payload["ref"]
            return {"ref": self.reference, "object": {"sha": self.parent}}
        if method == "PUT" and route == f"repos/{self.repo}/contents/{self.path}":
            if self.fail_after_reference:
                raise ConnectionError("ambiguous partial write")
            assert payload["sha"] == blob_id(SOURCE)
            self.head_data = base64.b64decode(payload["content"], validate=True)
            self.head_sha = "c" * 40
            return {"commit": {"sha": self.head_sha},
                    "content": {"sha": blob_id(self.head_data)}}
        if method == "POST" and route == f"repos/{self.repo}/pulls":
            assert payload["draft"] is True
            assert payload["head"] == self.reference.removeprefix("refs/heads/")
            assert payload["title"].startswith("F139 autonomy DEV:")
            self.pr = {
                "number": 488, "id": 600488, "state": "open",
                "author_association": "OWNER", "draft": True,
                "title": payload["title"], "body": payload["body"],
                "user": {"login": "spoonman136668-ai"},
                "head": {
                    "sha": self.head_sha,
                    "ref": payload["head"],
                    "repo": {"full_name": self.repo},
                },
                "base": {"sha": "f" * 40},
            }
            return {"number": 488}
        raise AssertionError("unapproved write: "+method+" "+route)

    def preflight(self, **kwargs):
        return publisher_preflight(
            self.get, source_sha=self.source, parent_commit=self.parent,
            historical_sha256=self.history, consumed_mechanisms=set(),
            existing_candidate_identities=set(), **kwargs)


class OwnerPublisherTests(unittest.TestCase):
    def test_verified_owner_creates_only_one_native_source_commit_and_draft(self):
        p = FakeOriginalOwner()
        plan = p.preflight()
        self.assertFalse(plan["writes_authorized"])
        self.assertNotEqual(plan["before_blob"], plan["after_blob"])
        result = publish_single_draft(
            p.get, p.write, plan, owner_witness=lambda: True,
            consumed_mechanisms=set(), existing_candidate_identities=set())
        self.assertTrue(result["source_qualified_for_existing_feeder"])
        self.assertTrue(result["authentic_single_commit_owner_draft"])
        self.assertFalse(result["worker_dispatched"])
        self.assertFalse(result["scientific_first_use"])
        self.assertEqual(len(p.write_calls), 3)
        self.assertEqual([m for m,_ in p.write_calls],
                         ["POST", "PUT", "POST"])
        self.assertIn("scientific first-use", p.pr["body"])

    def test_consumed_negative_mechanism_is_never_published(self):
        p = FakeOriginalOwner()
        with self.assertRaisesRegex(PublisherDenied, "PREVIOUSLY_CONSUMED"):
            publisher_preflight(
                p.get, source_sha=p.source, parent_commit=p.parent,
                historical_sha256=p.history,
                consumed_mechanisms={candidate_mechanism_identity()},
                existing_candidate_identities=set())
        plan = p.preflight()
        with self.assertRaisesRegex(PublisherDenied, "PREVIOUSLY_CONSUMED"):
            publish_single_draft(
                p.get, p.write, plan, owner_witness=lambda: True,
                consumed_mechanisms={candidate_mechanism_identity()},
                existing_candidate_identities=set())
        self.assertEqual(p.write_calls, [])

    def test_no_owner_witness_means_no_writes(self):
        p = FakeOriginalOwner()
        plan = p.preflight()
        with self.assertRaisesRegex(PublisherDenied, "OWNER_WRITER_NOT_QUALIFIED"):
            publish_single_draft(
                p.get, p.write, plan, owner_witness=lambda: False,
                consumed_mechanisms=set(), existing_candidate_identities=set())
        self.assertFalse(p.write_calls)

    def test_mismatched_source_plan_is_rejected_before_write(self):
        p = FakeOriginalOwner()
        plan = p.preflight()
        plan["before_blob"] = "f" * 40
        with self.assertRaisesRegex(PublisherDenied, "PLAN_MOVED"):
            publish_single_draft(
                p.get, p.write, plan, owner_witness=lambda: True,
                consumed_mechanisms=set(), existing_candidate_identities=set())
        self.assertFalse(p.write_calls)

    def test_no_retry_after_ambiguous_git_branch_write(self):
        p = FakeOriginalOwner()
        plan = p.preflight()
        p.fail_after_reference = True
        with self.assertRaises(ConnectionError):
            publish_single_draft(
                p.get, p.write, plan, owner_witness=lambda: True,
                consumed_mechanisms=set(), existing_candidate_identities=set())
        self.assertEqual(p.write_calls[:2], [
            ("POST", f"repos/{p.repo}/git/refs"),
            ("PUT", f"repos/{p.repo}/contents/{p.path}"),
        ])
        with self.assertRaisesRegex(PublisherDenied, "SOURCE_BRANCH_EXISTS"):
            p.preflight()

    def test_repeat_proposal_is_deduplicated(self):
        p = FakeOriginalOwner()
        plan = p.preflight()
        with self.assertRaisesRegex(PublisherDenied, "PREVIOUS_CANDIDATE"):
            publisher_preflight(
                p.get, source_sha=p.source, parent_commit=p.parent,
                historical_sha256=p.history, consumed_mechanisms=set(),
                existing_candidate_identities={plan["candidate_identity"]})
        self.assertFalse(p.write_calls)

    def test_missing_pin_and_fake_history_rejected(self):
        p = FakeOriginalOwner()
        with self.assertRaisesRegex(PublisherDenied, "HISTORICAL_SOURCE_OR_DEDUP"):
            publisher_preflight(
                p.get, source_sha=p.source, parent_commit=p.parent,
                historical_sha256="invalid", consumed_mechanisms=set(),
                existing_candidate_identities=set())

    def test_malicious_pr_actor_does_not_get_success(self):
        p = FakeOriginalOwner()
        original = p.write
        def write(method,route,payload):
            value = original(method,route,payload)
            if method == "POST" and route.endswith("/pulls"):
                p.pr["user"] = {"login": "attacker"}
            return value
        with self.assertRaisesRegex(PublisherDenied, "OWNER_DRAFT_PR_NOT_VERIFIED"):
            publish_single_draft(
                p.get, write, p.preflight(), owner_witness=lambda: True,
                consumed_mechanisms=set(), existing_candidate_identities=set())

    def test_source_branch_preexisting_ref_denied_without_write(self):
        p = FakeOriginalOwner()
        p.reference = "refs/heads/f139/auto-g2-ygg-old"
        with self.assertRaisesRegex(PublisherDenied, "SOURCE_BRANCH_EXISTS"):
            p.preflight()
        self.assertFalse(p.write_calls)


if __name__ == "__main__":
    unittest.main()

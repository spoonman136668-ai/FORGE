"""F139 native development must survive unrelated protected-main source changes.

No original SQLite, Windows scheduled task, worker dispatch or paid provider.
"""
from __future__ import annotations

import copy
import inspect
import json
import unittest

from f139.nci04_release_pin_continuity import (
    ReleaseContinuityDenied, prove_deployed_release_pin,
)
from f139.local_controller import GitHub, run_once

REPO = "spoonman136668-ai/FORGE"
RELEASE = "1" * 40
HEAD = "2" * 40
POLICY = {
    "schema": "forge.f139.native-autonomy-feed-owner-policy.v1",
    "enabled": True, "source_sha": RELEASE,
    "title_prefix": "F139 autonomy DEV:",
    "lanes": ["Wingless", "Yggdrasil"],
    "max_issue_creations_per_cycle": 2,
    "require_owner_authored_pr": True,
    "require_single_head_commit_delta": True,
    "require_single_allowed_source_file": True,
    "scientific_first_use": False, "paid_model_calls": 0,
    "accepted_ref_mutations": 0,
    "new_controller": False, "new_scheduler": False, "new_queue": False,
}


class AuthenticatedProvider:
    def __init__(self):
        self.branch = {"protected": True, "commit": {"sha": HEAD}}
        self.issue = {
            "state": "open", "number": 807,
            "user": {"login": "spoonman136668-ai"},
            "author_association": "OWNER",
            "body": json.dumps(POLICY,sort_keys=True),
        }
        self.compare = {
            "status": "ahead", "ahead_by": 9, "behind_by": 0,
            "merge_base_commit": {"sha": RELEASE},
        }
        self.calls=[]

    def get(self, path):
        self.calls.append(path)
        if path == f"repos/{REPO}/branches/main":
            return copy.deepcopy(self.branch)
        if path == f"repos/{REPO}/issues/807":
            return copy.deepcopy(self.issue)
        if path == f"repos/{REPO}/branches/f139-owner-release-{RELEASE}":
            return {"name":"f139-owner-release-"+RELEASE,
                    "commit":{"sha":RELEASE}}
        if path == f"repos/{REPO}/compare/{RELEASE}...{HEAD}":
            return copy.deepcopy(self.compare)
        raise AssertionError("unexpected route "+path)


class ReleasePinContinuityTests(unittest.TestCase):
    def setUp(self):
        self.provider=AuthenticatedProvider()

    def proof(self):
        return prove_deployed_release_pin(
            self.provider.get,deployed_source=RELEASE,protected_source=HEAD)

    def deny(self, mutate, reason):
        mutate(self.provider)
        with self.assertRaises(ReleaseContinuityDenied) as e:
            self.proof()
        self.assertIn(reason,str(e.exception))

    def test_post_merge_main_does_not_implicitly_replace_original_owner(self):
        proof=self.proof()
        self.assertEqual(proof["released_source_sha"],RELEASE)
        self.assertEqual(proof["latest_protected_main_sha"],HEAD)
        self.assertTrue(proof["existing_owner_policy_authorized"])
        self.assertTrue(proof["new_commits_are_uninstalled"])
        self.assertFalse(proof["source_transition_granted"])
        self.assertFalse(proof["scientific_first_use"])
        self.assertEqual(len(self.provider.calls),5)

    def test_authentic_owner_policy_pin_required(self):
        self.deny(lambda p:p.issue.update(author_association="NONE"),
                  "POLICY_OWNER_IDENTITY")
        self.deny(lambda p:p.issue.update(user={"login":"random"}),
                  "POLICY_OWNER_IDENTITY")
        self.deny(lambda p:p.issue.update(state="closed"),
                  "POLICY_OWNER_IDENTITY")

    def test_no_reprogramming_or_science_or_mutating_owner_scope(self):
        for change in (
            {"source_sha":HEAD}, {"enabled":False},
            {"scientific_first_use":True}, {"paid_model_calls":1},
            {"new_controller":True},{"new_scheduler":True},
            {"new_queue":True},{"accepted_ref_mutations":1},
            {"require_single_head_commit_delta":False},
        ):
            with self.subTest(change=change):
                p=AuthenticatedProvider()
                p.issue["body"]=json.dumps({**POLICY,**change})
                with self.assertRaises(Exception):
                    prove_deployed_release_pin(p.get,
                      deployed_source=RELEASE,protected_source=HEAD)

    def test_worker_source_must_use_immutable_exact_release_ref(self):
        self.assertIn(
            f"repos/{REPO}/branches/f139-owner-release-{RELEASE}",
            self.proof() and self.provider.calls)
        from f139.nci04_release_pin_continuity import (
            verify_release_worker_branch, release_worker_branch)
        self.assertEqual(release_worker_branch(RELEASE),
                         "f139-owner-release-"+RELEASE)
        wrong=lambda route: (
            {"name":"f139-owner-release-"+RELEASE,
             "commit":{"sha":HEAD}}
            if route.endswith("f139-owner-release-"+RELEASE)
            else self.provider.get(route))
        with self.assertRaisesRegex(ReleaseContinuityDenied,
                                    "WORKER_BRANCH_NOT_IMMUTABLE"):
            verify_release_worker_branch(wrong, RELEASE)

    def test_fork_or_rewritten_history_or_unprotected_main_denied(self):
        self.deny(lambda p:p.compare.update(status="diverged"),"NOT_RELEASE_ANCESTRY")
        self.deny(lambda p:p.compare.update(behind_by=1),"NOT_RELEASE_ANCESTRY")
        self.deny(lambda p:p.compare["merge_base_commit"].update(sha="3"*40),
                  "NOT_RELEASE_ANCESTRY")
        self.deny(lambda p:p.branch.update(protected=False),
                  "PROTECTED_MAIN_IDENTITY_DRIFT")

    def test_moving_main_during_check_fails_closed(self):
        p=AuthenticatedProvider()
        old=p.get
        n=[0]
        def moving(path):
            result=old(path)
            if path==f"repos/{REPO}/branches/main":
                n[0]+=1
                if n[0]>1:result["commit"]["sha"]="f"*40
            return result
        with self.assertRaisesRegex(ReleaseContinuityDenied,"PROTECTED_MAIN_MOVED"):
            prove_deployed_release_pin(
                moving,deployed_source=RELEASE,protected_source=HEAD)

    def test_authority_is_explicit_no_replay_and_no_v8_reuse(self):
        src=inspect.getsource(run_once)
        self.assertIn('deployed_release_continuity',src)
        self.assertIn('not source_matches and native_enabled',src)
        self.assertIn('MAIN_SOURCE_DRIFT_DISPATCH_BLOCKED',src)
        helper=inspect.getsource(GitHub.deployed_release_continuity)
        self.assertIn('db.verify()',helper)
        self.assertIn('verify_native_activation(db)',helper)
        self.assertIn('git("rev-parse", "HEAD") != deployed_source',helper)
        self.assertIn('git("status", "--porcelain", "--untracked-files=all")',helper)
        self.assertIn("prove_deployed_release_pin",helper)

if __name__=="__main__":
    unittest.main()

"""V42 source-only successor qualification and negative controls."""
import copy
import inspect
import json
import unittest
from unittest.mock import patch

from f139 import nci04_v42_owner_source_readiness as r


class SourceReleaseReadinessTests(unittest.TestCase):
    def fixture(self):
        prefix = "repos/" + r.REPO + "/"
        expected_policy = {
            "schema": "forge.f139.native-autonomy-feed-owner-policy.v1",
            "enabled": True, "source_sha": r.BEFORE,
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
        jobs = [{"name": name, "status": "completed", "conclusion": "success"}
                for name in sorted(r.EIGHT)]
        m = {
            prefix + "branches/main": {
                "name": "main", "protected": True,
                "commit": {"sha": r.REPAIR}},
            prefix + "pulls/1780": {
                "number": 1780, "state": "closed", "merged": True,
                "merge_commit_sha": r.REPAIR,
                "user": {"login": r.OWNER},
                "head": {"sha": r.REPAIR_HEAD},
                "base": {"ref": "main"}},
            prefix + "git/commits/" + r.REPAIR: {
                "sha": r.REPAIR, "tree": {"sha": r.REPAIR_TREE},
                "parents": [{"sha": r.BEFORE}, {"sha": r.REPAIR_HEAD}]},
            prefix + "git/commits/" + r.REPAIR_HEAD: {
                "sha": r.REPAIR_HEAD, "tree": {"sha": r.REPAIR_TREE}},
            prefix + "issues/807": {
                "state": "open", "user": {"login": r.OWNER},
                "body": json.dumps(expected_policy, sort_keys=True)},
            prefix + "issues/1715": {
                "number": 1715, "state": "open",
                "user": {"login": r.OWNER}},
            prefix + "actions/runs?head_sha=" + r.REPAIR +
                "&event=push&branch=main&per_page=100": {
                    "workflow_runs": [{
                        "name": "FORGE public Linux and Windows qualification",
                        "head_sha": r.REPAIR, "head_branch": "main",
                        "event": "push", "status": "completed",
                        "conclusion": "success", "run_attempt": 1,
                        "id": 43835468462, "actor": {"login": r.OWNER}}]},
            prefix + "actions/runs/43835468462/jobs?per_page=100": {
                "jobs": jobs},
        }
        for ancestor in (r.BEFORE, r.REPAIR):
            m[prefix + "compare/" + ancestor + "..." + r.REPAIR
              + "?per_page=1&page=2"] = {
                "status": "ahead" if ancestor == r.BEFORE else "identical",
                "behind_by": 0, "merge_base_commit": {"sha": ancestor}}
        return m

    def check(self, data):
        return r.release_source(lambda route: copy.deepcopy(data[route]),
                                r.REPAIR)

    def test_exact_repair_and_eight_real_jobs_source_only(self):
        receipt = self.check(self.fixture())
        self.assertEqual(receipt["repaired_tree_sha"], r.REPAIR_TREE)
        self.assertEqual(receipt["main_qualification_job_count"], 8)
        self.assertEqual(receipt["main_qualification_run_id"], 43835468462)
        for forbidden in ("live_owner_verified", "source_transition_authorized",
                          "scientific_first_use", "hybrid_scientific_admission"):
            self.assertFalse(receipt[forbidden])
        self.assertEqual(receipt["owner_task_mutations"], 0)
        self.assertEqual(receipt["new_dispatches"], 0)

    def test_frozen_repair_pr_tree_and_parent_can_never_be_substituted(self):
        base = self.fixture()
        p = "repos/" + r.REPO + "/"
        changes = [
            (p + "pulls/1780", "merged", False),
            (p + "pulls/1780", "merge_commit_sha", "f"*40),
            (p + "git/commits/" + r.REPAIR, "sha", "f"*40),
            (p + "git/commits/" + r.REPAIR_HEAD, "sha", "f"*40),
            (p + "git/commits/" + r.REPAIR, "tree", {"sha": "f"*40}),
            (p + "git/commits/" + r.REPAIR, "parents", [{"sha": "f"*40}]),
            (p + "branches/main", "protected", False),
        ]
        for route, field, value in changes:
            with self.subTest(route=route, field=field):
                data = copy.deepcopy(base)
                data[route][field] = value
                with self.assertRaises(r.SourceReadinessDenied):
                    self.check(data)

    def test_main_ancestry_and_policy_are_strict(self):
        base = self.fixture()
        p = "repos/" + r.REPO + "/"
        policy = json.loads(base[p + "issues/807"]["body"])
        bad = [
            ("source_sha", "b"*40),
            ("lanes", ["Wingless", "Yggdrasil"]),
            ("lanes", ["Wingless", "Yggdrasil", "TTT-Hybrid", "KTRADE"]),
            ("scientific_first_use", True),
            ("paid_model_calls", 1),
            ("new_scheduler", True),
        ]
        for field, value in bad:
            with self.subTest(field=field, value=value):
                data = copy.deepcopy(base)
                doc = copy.deepcopy(policy)
                doc[field] = value
                data[p + "issues/807"]["body"] = json.dumps(doc)
                with self.assertRaisesRegex(
                        r.SourceReadinessDenied, "OWNER_POLICY_DRIFT"):
                    self.check(data)
        for anc in (r.REPAIR, r.BEFORE):
            with self.subTest(ancestor=anc):
                data = copy.deepcopy(base)
                data[p+"compare/"+anc+"..."+r.REPAIR+
                     "?per_page=1&page=2"]["behind_by"] = 1
                with self.assertRaisesRegex(
                        r.SourceReadinessDenied, "ANCESTRY_DRIFT"):
                    self.check(data)
        data = copy.deepcopy(base)
        data[p + "issues/1715"]["state"] = "closed"
        with self.assertRaisesRegex(
                r.SourceReadinessDenied, "ESCROW_ISSUE_MISSING"):
            self.check(data)

    def test_exact_ci_not_workflow_presence_or_replay(self):
        base = self.fixture()
        p = "repos/" + r.REPO + "/"
        runs_key = p+"actions/runs?head_sha="+r.REPAIR+"&event=push&branch=main&per_page=100"
        jobs_key = p+"actions/runs/43835468462/jobs?per_page=100"
        variations = []
        wrong = copy.deepcopy(base)
        wrong[runs_key]["workflow_runs"][0]["run_attempt"] = 2
        variations.append(wrong)
        wrong = copy.deepcopy(base)
        wrong[runs_key]["workflow_runs"][0]["conclusion"] = "failure"
        variations.append(wrong)
        wrong = copy.deepcopy(base)
        wrong[runs_key]["workflow_runs"] *= 2
        variations.append(wrong)
        wrong = copy.deepcopy(base)
        wrong[jobs_key]["jobs"][0]["conclusion"] = "failure"
        variations.append(wrong)
        wrong = copy.deepcopy(base)
        wrong[jobs_key]["jobs"][0]["name"] = "fake"
        variations.append(wrong)
        wrong = copy.deepcopy(base)
        wrong[jobs_key]["jobs"].pop()
        variations.append(wrong)
        for i, data in enumerate(variations):
            with self.subTest(case=i), self.assertRaises(
                    r.SourceReadinessDenied):
                self.check(data)

    def test_untrusted_owner_snapshot_does_not_grant_authority(self):
        for sample in (None, {}, object()):
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(r.SourceReadinessDenied):
                    r.original_owner_cold_read(sample)
        source = inspect.getsource(r)
        for forbidden in ("Stop-ScheduledTask", "Start-ScheduledTask",
                          "Disable-ScheduledTask", "Enable-ScheduledTask",
                          "workflow_dispatch(", ".event(", ".transition_source(",
                          "update_ref(", "Import-Clixml", ".post("):
            self.assertNotIn(forbidden, source)
        self.assertFalse(hasattr(r, "install"))
        self.assertFalse(hasattr(r, "activate"))
        self.assertFalse(hasattr(r, "dispatch"))

    def test_nonstring_target_and_duplicate_policy_keys_fail_closed(self):
        base = self.fixture()
        for target in (None, 123, "", "a"*39, "A"*40):
            with self.subTest(target=target):
                with self.assertRaises(r.SourceReadinessDenied):
                    r.release_source(lambda path: copy.deepcopy(base[path]),
                                     target)
        p = "repos/" + r.REPO + "/"
        bad = copy.deepcopy(base)
        bad[p+"issues/807"]["body"] = (
            '{"schema":"forge.f139.native-autonomy-feed-owner-policy.v1",'
            '"source_sha":"' + r.BEFORE + '","source_sha":"' + r.BEFORE + '"}')
        with self.assertRaises(r.SourceReadinessDenied):
            self.check(bad)


if __name__ == "__main__":
    unittest.main()

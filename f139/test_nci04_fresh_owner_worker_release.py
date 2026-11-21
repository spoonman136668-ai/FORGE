"""Native release source qualification only; never mutate a live task."""
from copy import deepcopy
import os
import subprocess
import shutil
import unittest

from f139.nci04_fresh_owner_worker_release import (
    BASE, BRANCH, ROOT, REPO, OWNER, PR, PREFIX, QUALIFICATION,
    OWNER_WORKFLOW, OWNER_RELEASE_PREFIX, FRESH_RUN, TASK_SOURCE,
    OwnerReleaseDenied, inspect_event, qualify_release,
)


class FreshOwnerWorkerReleaseTests(unittest.TestCase):
    def setUp(self):
        self.target, self.head, self.tree = "a"*40, "b"*40, "c"*40
        t, h, tree = self.target, self.head, self.tree
        self.routes = {
            ROOT+"/branches/main": {"protected": True, "commit": {"sha": t}},
            ROOT+"/pulls/"+str(PR): {
                "number": PR, "merged": True, "draft": False, "state": "closed",
                "merge_commit_sha": t, "user": {"login": OWNER},
                "head": {"sha": h, "ref": BRANCH, "repo": {"full_name": REPO}},
                "base": {"ref": "main", "repo": {"full_name": REPO}},
            },
            ROOT+"/git/commits/"+t: {
                "sha": t, "tree": {"sha": tree}, "parents": [{"sha": BASE}, {"sha": h}]},
            ROOT+"/git/commits/"+h: {"sha": h, "tree": {"sha": tree}},
            ROOT+"/branches/"+PREFIX+t: {
                "name": PREFIX+t, "protected": True, "commit": {"sha": t}},
            ROOT+"/rulesets/26049392": {
                "id": 26049392, "target": "branch", "enforcement": "active",
                "conditions": {"ref_name": {"exclude": [], "include": ["refs/heads/f139-owner-release-*"]}},
                "bypass_actors": [], "rules": [{"type": "update"}, {"type": "deletion"}],
            },
        }
        self.run_route = ROOT+"/actions/runs?head_sha="+h+"&event=pull_request&per_page=100"
        self.routes[self.run_route] = {
            "total_count": 3,
            "workflow_runs": [{"id": i + 1, "path": path, "head_sha": h,
                               "event": "pull_request", "run_attempt": 1,
                               "status": "completed", "conclusion": "success",
                               "pull_requests": [{"number": PR}]}
                              for i, path in enumerate(sorted(QUALIFICATION))]}
        self.env = {
            "GITHUB_SHA": t, "GITHUB_RUN_ID": "101", "GITHUB_RUN_ATTEMPT": "1",
            "RUNNER_NAME": "FORGE-CODEX-REMOTE", "GITHUB_REPOSITORY": REPO,
            "GITHUB_ACTOR": OWNER, "GITHUB_EVENT_NAME": "issue_comment",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_WORKFLOW_REF": REPO+"/"+OWNER_WORKFLOW+"@refs/heads/main",
            "GH_TOKEN": "synthetic-test-only",
        }
        self.event = {
            "action": "created", "repository": {"full_name": REPO},
            "sender": {"login": OWNER},
            "issue": {"number": 1830, "state": "open", "user": {"login": OWNER}},
            "comment": {"id": 102, "user": {"login": OWNER}, "author_association": "OWNER",
                        "body": OWNER_RELEASE_PREFIX+t+" "+str(FRESH_RUN)},
        }

    def get(self, route):
        return deepcopy(self.routes[route])

    def test_final_exact_head_merge_and_immutable_pin_required(self):
        self.assertEqual(qualify_release(self.get, self.target, self.tree), self.head)
        for route, field, value in (
            (ROOT+"/branches/main", "protected", False),
            (ROOT+"/pulls/"+str(PR), "draft", True),
            (ROOT+"/git/commits/"+self.head, "tree", {"sha": "d"*40}),
            (ROOT+"/branches/"+PREFIX+self.target, "protected", False),
            (ROOT+"/rulesets/26049392", "bypass_actors", [{"actor_id": 1}]),
        ):
            with self.subTest(route=route, field=field):
                old = self.routes[route][field]
                self.routes[route][field] = value
                try:
                    with self.assertRaises(OwnerReleaseDenied):
                        qualify_release(self.get, self.target, self.tree)
                finally:
                    self.routes[route][field] = old

    def test_genuine_pr_workflow_run_with_empty_pr_array(self):
        # REST returns [] for all three actual PR1856 successful workflows.
        for row in self.routes[self.run_route]["workflow_runs"]:
            row["pull_requests"] = []
        self.assertEqual(qualify_release(self.get, self.target, self.tree), self.head)
        row = self.routes[self.run_route]["workflow_runs"][0]
        row["pull_requests"] = [{"number": PR}]
        self.assertEqual(qualify_release(self.get, self.target, self.tree), self.head)
        # Reject any explicit foreign or malformed association, even when
        # the correct PR appears elsewhere in the same provider array.
        for associations in (
            [{"number": PR + 1}],
            [{"number": PR}, {"number": PR + 1}],
            [{"number": PR}, "malformed"],
            [{"number": PR}, None],
            [{"number": PR}, {"number": str(PR)}],
            None,
            {},
        ):
            with self.subTest(associations=associations):
                row["pull_requests"] = associations
                with self.assertRaises(OwnerReleaseDenied):
                    qualify_release(self.get, self.target, self.tree)

    def test_final_suite_failure_or_old_sha_denied(self):
        run = self.routes[self.run_route]["workflow_runs"][0]
        for field, v in (("head_sha", "d"*40), ("conclusion", "failure"),
                         ("status", "in_progress"), ("run_attempt", 2)):
            with self.subTest(field=field):
                old = run[field]
                run[field] = v
                try:
                    with self.assertRaises(OwnerReleaseDenied):
                        qualify_release(self.get, self.target, self.tree)
                finally:
                    run[field] = old

    def test_release_event_is_distinct_from_already_consumed_rebind(self):
        self.assertEqual(inspect_event(self.event, self.env), (self.target, 101, 102))
        event = deepcopy(self.event)
        event["comment"]["body"] = "F139-FRESH-DEV-TASK-REBIND "+self.target+" "+str(FRESH_RUN)
        with self.assertRaises(OwnerReleaseDenied):
            inspect_event(event, self.env)
        for key, value in (("RUNNER_NAME", "foreign"), ("GITHUB_RUN_ATTEMPT", "2"),
                           ("GITHUB_ACTOR", "foreign"), ("OPENAI_API_KEY", "synthetic-blocked")):
            with self.subTest(key=key), self.assertRaises(OwnerReleaseDenied):
                inspect_event(self.event, dict(self.env, **{key: value}))

    def test_existing_task_only_no_dispatch_or_secondary_controller(self):
        for term in ("Register-ScheduledTask", "Unregister-ScheduledTask", "gh api",
                     "Start-ScheduledTask", "Stop-ScheduledTask", "workflow_dispatch"):
            self.assertNotIn(term, TASK_SOURCE)
        self.assertEqual(TASK_SOURCE.count("Set-ScheduledTask -TaskName"), 1)
        self.assertEqual(TASK_SOURCE.count("Enable-ScheduledTask -TaskName"), 1)
        self.assertLess(TASK_SOURCE.index("TASK_REBIND_READBACK_FAILED"),
                        TASK_SOURCE.index("Enable-ScheduledTask -TaskName"))

    @unittest.skipUnless(os.name == "nt", "Native Windows PowerShell AST only")
    def test_native_release_powershell_parses_without_running(self):
        ps = shutil.which("powershell.exe")
        self.assertIsNotNone(ps)
        result = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-Command",
            "$t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseInput("
            "$env:F139_SOURCE_AST,[ref]$t,[ref]$e)|Out-Null;"
            "if(@($e).Count -gt 0){exit 1}"],
            env={**os.environ, "F139_SOURCE_AST": TASK_SOURCE},
            capture_output=True, timeout=30, check=False)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()

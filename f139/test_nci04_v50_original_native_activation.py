"""V50 original task native-activation guardrails, synthetic only."""
from __future__ import annotations

from copy import deepcopy
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from f139 import nci04_v50_original_native_activation as v50
from f139 import nci04_v43_event1836_successor as v43
from f139 import nci04_owner_ledger as native


MAIN = "c" * 40
COMMENT = v50.PREVIOUS_COMMENT + 4444


def fake():
    env = dict(
        GITHUB_SHA=MAIN, GITHUB_REPOSITORY=v50.REPO,
        GITHUB_ACTOR=v50.OWNER, GITHUB_EVENT_NAME="issue_comment",
        GITHUB_REF="refs/heads/main", GITHUB_RUN_ATTEMPT="1",
        RUNNER_NAME="FORGE-CODEX-REMOTE")
    body = (v50.PREFIX + MAIN + " " + v50.SOURCE + " " +
            str(v50.PREVIOUS_RUN))
    comment = dict(id=COMMENT, body=body,
                   created_at="2026-11-16T23:10:00Z",
                   updated_at="2026-11-16T23:10:00Z",
                   author_association="OWNER", user=dict(login=v50.OWNER))
    event = dict(action="created", issue=dict(number=807,
                 user=dict(login=v50.OWNER)),
                 sender=dict(login=v50.OWNER), comment=comment)
    p = "repos/" + v50.REPO + "/"
    jobs = [dict(name=name, status="completed", conclusion="success")
            for name in sorted(v50.EIGHT)]
    state = {
        p+"issues/comments/"+str(COMMENT):
            dict(**comment, issue_url="https://api.github.com/repos/"+
                 v50.REPO+"/issues/807"),
        p+"actions/runs/"+str(v50.PREVIOUS_RUN):dict(
            id=v50.PREVIOUS_RUN, head_sha=v50.PREVIOUS_HEAD,
            name="FORGE G54 guarded V9 original-owner cutover",
            run_attempt=1, status="completed", conclusion="success",
            actor=dict(login=v50.OWNER)),
        p+"branches/main": dict(protected=True, commit=dict(sha=MAIN)),
        p+"actions/runs?head_sha="+MAIN+
          "&event=push&branch=main&per_page=100":dict(workflow_runs=[
            dict(name="FORGE public Linux and Windows qualification",
                 head_sha=MAIN, head_branch="main", run_attempt=1,
                 event="push", status="completed", conclusion="success",
                 actor=dict(login=v50.OWNER), id=112233)]),
        p+"actions/runs/112233/jobs?per_page=100":dict(jobs=jobs),
    }
    def get(route):
        if route not in state:
            raise AssertionError("unknown GET " + route)
        return deepcopy(state[route])
    return env, event, state, get


class V50SourceActivationTests(unittest.TestCase):
    def call(self, env, event, get, pinned=True):
        with patch.object(v50, "prove_deployed_release_pin",
                          return_value=dict(
                              existing_owner_policy_authorized=pinned,
                              new_commits_are_uninstalled=True)):
            return v50.request(get, env, event)

    def test_authenticated_owner_and_exact_eight_job_source(self):
        env, event, state, get = fake()
        receipt = self.call(env, event, get)
        self.assertEqual(receipt["main_sha"], MAIN)
        self.assertEqual(receipt["source_sha"], v50.SOURCE)
        self.assertEqual(receipt["job_count"], 8)
        self.assertFalse(receipt["scientific_first_use"])
        self.assertFalse(receipt["new_controller"])
        self.assertEqual(receipt["new_dispatches"], 0)
        self.assertEqual(receipt["owner_comment_id"], COMMENT)

    def test_actor_comment_and_immutable_prior_failure_closed(self):
        cases = (
            ("env", "GITHUB_ACTOR", "other"),
            ("env", "RUNNER_NAME", "other"),
            ("env", "GITHUB_RUN_ATTEMPT", "2"),
            ("env", "OPENAI_API_KEY", "forbidden"),
            ("event", "action", "edited"),
            ("comment", "body", "wrong"),
            ("comment", "id", v50.PREVIOUS_COMMENT),
            ("comment", "author_association", "CONTRIBUTOR"),
            ("remote", "body", "wrong"),
            ("prior", "conclusion", "failure"),
            ("prior", "run_attempt", 2),
            ("prior", "head_sha", "0"*40),
            ("main", "protected", False),
            ("ci", "run_attempt", 2),
            ("ci", "conclusion", "failure"),
            ("jobs", "status", "in_progress"),
        )
        for scope, key, value in cases:
            with self.subTest(scope=scope, key=key):
                env, event, state, get = fake()
                p = "repos/" + v50.REPO + "/"
                if scope == "env": env[key] = value
                if scope == "event": event[key] = value
                if scope == "comment": event["comment"][key] = value
                if scope == "remote":
                    state[p+"issues/comments/"+str(COMMENT)][key] = value
                if scope == "prior":
                    state[p+"actions/runs/"+str(v50.PREVIOUS_RUN)][key] = value
                if scope == "main": state[p+"branches/main"][key] = value
                if scope == "ci":
                    state[p+"actions/runs?head_sha="+MAIN+
                          "&event=push&branch=main&per_page=100"][
                              "workflow_runs"][0][key] = value
                if scope == "jobs":
                    state[p+"actions/runs/112233/jobs?per_page=100"][
                        "jobs"][0][key] = value
                with self.assertRaises(v50.NativeV50Denied):
                    self.call(env, event, get)

    def test_reject_wrong_released_source_and_missing_release_pin(self):
        env, event, state, get = fake()
        event["comment"]["body"] = (
            v50.PREFIX + MAIN + " " + "0"*40 + " " +
            str(v50.PREVIOUS_RUN))
        with self.assertRaises(v50.NativeV50Denied):
            self.call(env, event, get)
        env, event, state, get = fake()
        with self.assertRaises(v50.NativeV50Denied):
            self.call(env, event, get, pinned=False)

    def test_validator_admits_exact_v41_without_relaxing_future_schemas(self):
        source = inspect.getsource(native.activate_native)
        self.assertEqual(source.count('"forge.f139.source-transition.v41"'), 3)
        self.assertNotIn('"forge.f139.source-transition.v42"', source)
        self.assertEqual(v43.SCHEMA, "forge.f139.source-transition.v41")
        self.assertEqual(v50.HEAD_SEQ, 1836)
        self.assertEqual(v50.HEAD_HASH,
                         "dbc4e12862c819812121adf1df905f74023c65633067bcabe906488d37468964")
        self.assertEqual(v50.BEFORE, v43.ORIGINAL_SOURCE)
        self.assertNotEqual(v50.SOURCE, v50.BEFORE)
        self.assertEqual(v50.PREVIOUS_RUN, 43973705548)

    def test_live_mutator_is_single_source_locked_and_quiesced(self):
        source = inspect.getsource(v50.execute)
        self.assertIn('original_task_quiesced(db_path)', source)
        self.assertIn('with SingleOwner(db_path.with_suffix(".lock"))', source)
        self.assertIn('snapshot(db, False)', source)
        self.assertIn('activate_native(db, approved)', source)
        self.assertIn('snapshot(db, True)', source)
        self.assertIn('scientific_first_use=False', source)
        script = (Path(__file__).resolve().parents[1] /
                  "f139/v50_original_owner_native_activate.ps1").read_text(
                      encoding="utf-8")
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/f139-g54-v9-owner-cutover.yml").read_text(
                        encoding="utf-8")
        self.assertEqual(workflow.count(
            "  v50-original-owner-native-activation:"), 1)
        self.assertIn("concurrency:", workflow)
        self.assertIn("F139_V50_OWNER_NATIVE_ACTIVATE", v50.PREFIX.replace("-", "_"))
        self.assertIn("Disable-ScheduledTask", script)
        self.assertIn("Stop-ScheduledTask", script)
        self.assertIn("Enable-ScheduledTask", script)
        self.assertIn("Start-ScheduledTask", script)
        self.assertIn("F139_V50_FORWARD_ONLY_OWNER_HOLD_NO_REPLAY", script)
        self.assertNotIn("New-ScheduledTask", script)
        self.assertNotIn("Register-ScheduledTask", script)
        self.assertNotIn("OPENAI_API_KEY=", script)
        self.assertNotIn("gh api --method POST", script)

    def test_direct_commit_refused_outside_original_windows(self):
        with self.assertRaises(v50.NativeV50Denied):
            v50.execute(Path("/tmp/not-real-original.sqlite"), "commit")


if __name__ == "__main__":
    unittest.main()

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
        self.assertLess(script.index("$sealed=InvokeV50 'verify'"),
                        script.index("Start-ScheduledTask"))
        self.assertLess(script.index("Start-ScheduledTask"),
                        script.index("$verified=InvokeV50 'poststart'"))
        self.assertNotIn("$verified=InvokeV50 'verify'", script)
        self.assertNotIn("New-ScheduledTask", script)
        self.assertNotIn("Register-ScheduledTask", script)
        self.assertNotIn("OPENAI_API_KEY=", script)
        self.assertNotIn("gh api --method POST", script)

    def test_poststart_allows_append_only_progress_without_weakening_anchor(self):
        from unittest.mock import MagicMock
        record = dict(schema=native.ACTIVATION_SCHEMA,
                      source_sha=v50.SOURCE,
                      prior_event_head_sha256=v50.HEAD_HASH,
                      sealed_original_prefix_sha256="a"*64,
                      verified_original_tasks=4, verified_d2k_tasks=2,
                      new_dispatches=0, scientific_first_use=False,
                      development_only=True)
        event = dict(seq=1837, sha="e"*64, prior_sha=v50.HEAD_HASH,
                     kind=native.ACTIVATION_KIND, payload=json.dumps(record))
        db = MagicMock()
        metadata = dict(source_sha=v50.SOURCE, head_seq=1841,
                        head_hash="f"*64, enabled=1, legacy_suspended=1)
        db.meta.return_value = metadata
        db.conn.execute.return_value.fetchone.return_value = event
        with patch.object(v50, "verify_native_activation", return_value=True):
            receipt = v50.poststart_snapshot(db)
            self.assertEqual(receipt["event_seq"], 1841)
            self.assertEqual(receipt["activation_event_seq"], 1837)
            self.assertEqual(receipt["activation_event_sha256"], "e"*64)
            db.verify.assert_called()
            for key, wrong in (("source_sha", "0"*40),
                               ("head_seq", 1836), ("enabled", 0)):
                with self.subTest(key=key):
                    changed = dict(metadata, **{key: wrong})
                    db.meta.return_value = changed
                    with self.assertRaises(v50.NativeV50Denied):
                        v50.poststart_snapshot(db)
            db.meta.return_value = metadata
            event["prior_sha"] = "0"*64
            with self.assertRaises(v50.NativeV50Denied):
                v50.poststart_snapshot(db)
            event["prior_sha"] = v50.HEAD_HASH
            event["payload"] = json.dumps(dict(record, scientific_first_use=True))
            with self.assertRaises(v50.NativeV50Denied):
                v50.poststart_snapshot(db)
        event["payload"] = json.dumps(record)
        with patch.object(v50, "verify_native_activation", return_value=False):
            with self.assertRaises(v50.NativeV50Denied):
                v50.poststart_snapshot(db)

    def test_v50_workflow_source_scope_is_exact_not_generic(self):
        from scripts import check_rar_g145_pr_scope as scope
        branch = "engineering/f139-v50-v41-original-native-activation-20261116"
        pinned_base, allowed = scope.FROZEN_SCOPES[branch]
        self.assertEqual(pinned_base, "2567775a9c06b306142812cc8c0e252278f87273")
        self.assertEqual(len(allowed), 8)
        self.assertIn("scripts/check_rar_g145_pr_scope.py", allowed)
        self.assertIn("scripts/check_rar_g148_go_cache.py", allowed)
        self.assertIn("scripts/check_rar_g156_dynamic_base_cache.py", allowed)
        # Inspect the existing entrypoint source without importing its CLI
        # module: that module intentionally uses script-relative imports.
        script_dir = Path(__file__).resolve().parents[1] / "scripts"
        cache = (script_dir / "check_rar_g148_go_cache.py").read_text(
            encoding="utf-8")
        reuse = (script_dir / "check_rar_g156_dynamic_base_cache.py").read_text(
            encoding="utf-8")
        self.assertIn("G148_V50_ORIGINAL_NATIVE_EXACT_SCOPE_REQUIRED", cache)
        self.assertIn("G156_V50_ORIGINAL_NATIVE_EXACT_BASE_TREE_REQUIRED", reuse)
        workflow = ".github/workflows/f139-g54-v9-owner-cutover.yml"
        self.assertIn(workflow, allowed)
        self.assertFalse(scope.generic_paths_safe([workflow]))
        guard = inspect.getsource(scope.admit_original_pr)
        self.assertIn("G145_V50_ORIGINAL_NATIVE_ACTIVATION_SCOPE_DENIED", guard)
        self.assertIn("ad98fa391638b59254534ddfffea1be5c538b958", guard)
        self.assertIn("39f189fde3a6fece791cd3a6ca7dd0517cb6b430", guard)

    def test_direct_commit_refused_outside_original_windows(self):
        with self.assertRaises(v50.NativeV50Denied):
            v50.execute(Path("/tmp/not-real-original.sqlite"), "commit")


if __name__ == "__main__":
    unittest.main()

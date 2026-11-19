"""Opt-in original F139 loop comment intake, disposable SQLite only.

No live GitHub writes, no user control changes, no scheduled task creation.
The native Windows running-owner witness is mocked in synthetic tests only.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import (
    Database, F139Error, SingleOwner, cli, phase_comment_poll_due, run_once)
from f139.nci04_phase_comment_read import PhaseCommentReadDenied
from f139.test_nci04_phase_original_admission import (
    external_provider, owner_comment)
from f139.test_nci04_phase_comment_read import provider, SOURCE
from f139.nci04_phase_mode_replay import read_original_owner_mode


class OriginalLoopPhaseCommentTests(unittest.TestCase):
    def fixture(self):
        tmp = tempfile.TemporaryDirectory(prefix="f139-phase-loop-fixture-")
        path = Path(tmp.name) / "state.sqlite"
        db = Database.initialize(path, SOURCE)
        db.enable(legacy_suspended=True)
        return tmp, path, db

    def tick(self, db, path, api, *, scan=False):
        return run_once(
            db, api, path, "x" * 32,
            now="2026-11-19T02:05:00Z",
            scan_pending_phase_comments=scan)

    def test_poll_cadence_opt_in_only_and_type_strict(self):
        self.assertFalse(phase_comment_poll_due(0, 0))
        self.assertFalse(phase_comment_poll_due(20, 0))
        self.assertTrue(phase_comment_poll_due(0, 5))
        self.assertFalse(phase_comment_poll_due(1, 5))
        self.assertTrue(phase_comment_poll_due(5, 5))
        self.assertTrue(phase_comment_poll_due(240, 240))
        for cycle, every in ((-1, 5), (0, True), (0, 1),
                             (0, 241), (0.0, 5), (0, -1)):
            with self.subTest(cycle=cycle, every=every):
                with self.assertRaises(F139Error):
                    phase_comment_poll_due(cycle, every)

    def test_default_real_tick_does_not_scan_owner_issue(self):
        tmp, path, db = self.fixture()
        p, routes = external_provider([owner_comment(111)])
        try:
            with SingleOwner(path.with_suffix(".lock")):
                res = self.tick(db, path, p)
            self.assertEqual(res["disposition"], "QUEUE_EMPTY_NO_SCIENCE")
            self.assertEqual(routes, [])
            self.assertEqual(db.meta()["head_seq"], 1)
        finally:
            db.close()
            tmp.cleanup()

    def test_opt_in_scan_discovers_and_commits_exact_once(self):
        tmp, path, db = self.fixture()
        p, routes = external_provider([owner_comment(111)])
        try:
            with patch("f139.local_controller.native_original_running_publisher_profile",
                       return_value=True), SingleOwner(path.with_suffix(".lock")):
                res = self.tick(db, path, p, scan=True)
            self.assertEqual(res["disposition"], "PHASE_HOLD_NO_NEW_ADMISSIONS")
            self.assertIn("repos/spoonman136668-ai/FORGE/issues/comments/111",
                          routes)
            db.verify()
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind='PHASE_MODE_ADMITTED'"
            ).fetchone()[0], 1)
            # The next scan sees original SQLite comment consumed; never
            # reissues the same mode or needs the Windows writer witness.
            with SingleOwner(path.with_suffix(".lock")):
                again = self.tick(db, path, p, scan=True)
            self.assertEqual(again["disposition"],
                             "PHASE_HOLD_NO_NEW_ADMISSIONS")
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM events WHERE kind='PHASE_MODE_ADMITTED'"
            ).fetchone()[0], 1)
        finally:
            db.close()
            tmp.cleanup()

    def test_opt_in_empty_catalog_does_not_create_mode_or_work(self):
        tmp, path, db = self.fixture()
        p, routes = provider(pages=[[]])
        p.protected_main = lambda: SOURCE
        try:
            with SingleOwner(path.with_suffix(".lock")):
                res = self.tick(db, path, p, scan=True)
            self.assertEqual(res["disposition"], "QUEUE_EMPTY_NO_SCIENCE")
            self.assertEqual(db.meta()["head_seq"], 1)
            self.assertTrue(any("/issues/807" in route for route in routes))
        finally:
            db.close()
            tmp.cleanup()

    def test_invalid_policy_denies_scan_and_preserves_original_head(self):
        tmp, path, db = self.fixture()
        p, routes = provider(pages=[[owner_comment(111)]])
        p.protected_main = lambda: SOURCE
        original = p.runner

        def changed_policy(args):
            if args[0].endswith("/issues/807"):
                import json
                from f139.test_nci04_phase_comment_read import issue
                x = issue()
                o = json.loads(x["body"])
                o["scientific_first_use"] = True
                x["body"] = json.dumps(o)
                return json.dumps(x).encode()
            return original(args)

        p.runner = changed_policy
        try:
            with SingleOwner(path.with_suffix(".lock")):
                with self.assertRaises(PhaseCommentReadDenied):
                    self.tick(db, path, p, scan=True)
            self.assertEqual(db.meta()["head_seq"], 1)
        finally:
            db.close()
            tmp.cleanup()

    def test_scan_and_explicit_pair_must_not_mix(self):
        tmp, path, db = self.fixture()
        p, routes = external_provider([owner_comment(111)])
        try:
            with self.assertRaises(F139Error):
                run_once(
                    db, p, path, "x" * 32,
                    manual_phase_comment_id=111,
                    expected_phase_head_sha256=db.meta()["head_hash"],
                    scan_pending_phase_comments=True)
            self.assertEqual(routes, [])
        finally:
            db.close()
            tmp.cleanup()

    def test_cli_loop_flag_off_is_backward_compatible(self):
        tmp, path, db = self.fixture()
        db.close()
        seen = []

        class StopLoop(Exception):
            pass

        def fake_tick(*args, **kwargs):
            seen.append(kwargs)
            raise StopLoop()

        try:
            with patch("f139.local_controller.run_once", side_effect=fake_tick):
                with self.assertRaises(StopLoop):
                    cli(["--db", str(path), "loop", "--seconds", "45"])
            self.assertEqual(seen, [{}])
        finally:
            tmp.cleanup()

    def test_cli_opt_in_loop_scans_only_at_eligible_cycle(self):
        tmp, path, db = self.fixture()
        db.close()
        seen = []

        class StopLoop(Exception):
            pass

        def fake_tick(*args, **kwargs):
            seen.append(kwargs)
            if len(seen) == 7:
                raise StopLoop()
            return {"disposition": "QUEUE_EMPTY_NO_SCIENCE"}

        try:
            with patch("f139.local_controller.run_once", side_effect=fake_tick), \
                 patch("f139.local_controller.time.sleep", return_value=None):
                with self.assertRaises(StopLoop):
                    cli(["--db", str(path), "loop", "--seconds", "45",
                         "--phase-comment-poll-every", "5"])
            self.assertEqual(
                [x.get("scan_pending_phase_comments", False) for x in seen],
                [True, False, False, False, False, True, False])
        finally:
            tmp.cleanup()


    def test_bad_mode_comment_does_not_terminate_original_loop(self):
        from f139.nci04_phase_original_admission import (
            OriginalModeAdmissionDenied)
        import io
        tmp, path, db = self.fixture()
        db.close()

        class StopLoop(Exception):
            pass

        try:
            for rejection in (
                    PhaseCommentReadDenied("F139_PHASE_COMMENT_TEST_DENIED"),
                    OriginalModeAdmissionDenied("F139_PHASE_OWNER_TEST_DENIED")):
                with self.subTest(kind=type(rejection).__name__):
                    seen = []

                    def fake_tick(*args, **kwargs):
                        seen.append(kwargs)
                        if len(seen) == 1:
                            raise rejection
                        raise StopLoop()

                    with patch("f139.local_controller.run_once",
                               side_effect=fake_tick), \
                         patch("f139.local_controller.time.sleep",
                               return_value=None), \
                         patch("f139.local_controller.sys.stderr", io.StringIO()) as err:
                        with self.assertRaises(StopLoop):
                            cli(["--db", str(path), "loop",
                                 "--seconds", "45",
                                 "--phase-comment-poll-every", "5"])
                        self.assertIn("manual_mode_committed", err.getvalue())
                    self.assertEqual(
                        [x.get("scan_pending_phase_comments", False)
                         for x in seen], [True, False])
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()

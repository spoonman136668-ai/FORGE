"""Exact live run_once new-work seam exercised on disabled/synthetic owner fixtures.

No GitHub API calls, actual owner task modification or native scientific work.
Source-only regression of the ORIGINAL run_once() implementation.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from f139.local_controller import (
    Database, F139Error, SingleOwner, run_once,
)
from f139.nci04_phase_mode_replay import (
    KIND, ModeReplayDenied,
)
from f139.test_nci04_phase_mode_replay import SOURCE, admission


class FakeReadOnlyProvider:
    def __init__(self):
        self.events = []

    def protected_main(self):
        self.events.append("protected_main")
        return SOURCE

    def d2k_eligible_issues(self, source):
        self.events.append("d2k_eligible_issues")
        return []

    def dispatch(self, *args, **kwargs):
        self.events.append("dispatch")
        return None


class OriginalPhaseIntakeSeamTests(unittest.TestCase):
    def fixture(self, mode="HOLD", lane=None, *, ready=False):
        fixture = tempfile.TemporaryDirectory(prefix="f139-phase-gate-")
        path = Path(fixture.name) / "disabled.sqlite"
        db = Database.initialize(path, SOURCE)
        try:
            if ready:
                db.enqueue([{
                    "ticket": "f139-preexisting-wingless",
                    "lane": "Wingless", "source_sha": SOURCE,
                }], "a" * 64)
            with db.transaction():
                m = db.meta()
                db.event(KIND, admission(
                    mode=mode, lane=lane, prior=m["head_hash"]))
            db.enable(legacy_suspended=True)
            db.verify()
        except BaseException:
            db.close()
            fixture.cleanup()
            raise
        return fixture, path, db

    def invoke(self, db, path, provider):
        return run_once(db, provider, path, "x" * 32,
                        now="2026-11-19T01:01:01Z")

    def test_persisted_hold_blocks_new_work_before_any_catalog_call(self):
        temp, path, db = self.fixture("HOLD")
        try:
            p = FakeReadOnlyProvider()
            before = db.meta()
            with SingleOwner(path.with_suffix(".lock")):
                report = self.invoke(db, path, p)
            self.assertEqual(report["disposition"],
                             "PHASE_HOLD_NO_NEW_ADMISSIONS")
            self.assertFalse(report["worker_dispatched"])
            self.assertEqual(p.events, ["protected_main"])
            self.assertEqual(db.meta(), before)
        finally:
            db.close()
            temp.cleanup()

    def test_train_and_self_improve_do_not_inherit_research_permit(self):
        for mode in ("TRAIN", "SELF_IMPROVE"):
            with self.subTest(mode=mode):
                temp, path, db = self.fixture(mode)
                try:
                    p = FakeReadOnlyProvider()
                    with SingleOwner(path.with_suffix(".lock")):
                        report = self.invoke(db, path, p)
                    self.assertEqual(report["mode"], mode)
                    self.assertEqual(report["disposition"],
                                     "PHASE_EXECUTION_ADAPTER_NOT_QUALIFIED")
                    self.assertFalse(report["scientific_first_use"])
                    self.assertEqual(p.events, ["protected_main"])
                finally:
                    db.close()
                    temp.cleanup()

    def test_scoped_research_cannot_fall_through_to_other_lane(self):
        temp, path, db = self.fixture("RESEARCH", "Yggdrasil")
        try:
            p = FakeReadOnlyProvider()
            with SingleOwner(path.with_suffix(".lock")):
                report = self.invoke(db, path, p)
            self.assertEqual(report["disposition"],
                             "PHASE_LANE_SCOPING_NOT_QUALIFIED")
            self.assertEqual(report["lane"], "Yggdrasil")
            self.assertEqual(p.events, ["protected_main"])
        finally:
            db.close()
            temp.cleanup()

    def test_auto_and_unscoped_research_use_only_existing_owner_intake(self):
        for mode in ("AUTO", "RESEARCH"):
            with self.subTest(mode=mode):
                temp, path, db = self.fixture(mode)
                try:
                    p = FakeReadOnlyProvider()
                    with SingleOwner(path.with_suffix(".lock")):
                        report = self.invoke(db, path, p)
                    self.assertEqual(report["disposition"],
                                     "QUEUE_EMPTY_NO_SCIENCE")
                    self.assertEqual(p.events, ["protected_main"])
                    self.assertEqual(db.conn.execute(
                        "SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
                finally:
                    db.close()
                    temp.cleanup()

    def test_lane_pinned_auto_does_not_dispatch_unrelated_research(self):
        temp, path, db = self.fixture("AUTO", "Wingless")
        try:
            p = FakeReadOnlyProvider()
            with SingleOwner(path.with_suffix(".lock")):
                report = self.invoke(db, path, p)
            self.assertEqual(report["disposition"],
                             "PHASE_LANE_SCOPING_NOT_QUALIFIED")
            self.assertEqual(report["lane"], "Wingless")
            self.assertEqual(p.events, ["protected_main"])
        finally:
            db.close()
            temp.cleanup()

    def test_existing_ready_ticket_continues_under_hold_without_new_admission(self):
        temp, path, db = self.fixture("HOLD", ready=True)
        try:
            p = FakeReadOnlyProvider()
            before_count = db.conn.execute(
                "SELECT COUNT(*) FROM tasks").fetchone()[0]
            with SingleOwner(path.with_suffix(".lock")):
                report = self.invoke(db, path, p)
            self.assertEqual(report["disposition"],
                             "DEVELOPMENT_DISPATCHED_ONCE")
            self.assertIn("dispatch", p.events)
            self.assertEqual(db.conn.execute(
                "SELECT COUNT(*) FROM tasks").fetchone()[0], before_count)
            self.assertEqual(db.conn.execute(
                "SELECT stage FROM tasks LIMIT 1").fetchone()[0],
                             "WAIT_PROVIDER")
        finally:
            db.close()
            temp.cleanup()

    def test_no_original_mutex_denied_if_mode_record_exists(self):
        temp, path, db = self.fixture("HOLD")
        try:
            p = FakeReadOnlyProvider()
            before = db.meta()
            with self.assertRaises(ModeReplayDenied):
                self.invoke(db, path, p)
            self.assertEqual(db.meta(), before)
        finally:
            db.close()
            temp.cleanup()

    def test_forged_mode_event_is_rejected_by_core_verify(self):
        temp = tempfile.TemporaryDirectory(prefix="f139-phase-gate-")
        path = Path(temp.name) / "disabled.sqlite"
        db = Database.initialize(path, SOURCE)
        try:
            with db.transaction():
                m = db.meta()
                payload = admission(mode="HOLD", prior=m["head_hash"])
                payload["scientific_first_use"] = True
                db.event(KIND, payload)
            with self.assertRaises(ModeReplayDenied):
                db.verify()
        finally:
            db.close()
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()

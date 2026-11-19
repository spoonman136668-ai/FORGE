"""Focused no-remote replay and original-disabled-SQLite cold tests."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from f139.nci04_phase_mode_replay import (
    FIELDS, KIND, SCHEMA, ModeReplayDenied, project_verified_events,
    read_original_owner_mode,
)

SOURCE = "c06403c8b6035c6c7013866a7ea08cef1244b507"
HEAD = "0" * 64
AFTER = "1" * 64


def admission(*, mode="HOLD", lane=None, source=SOURCE,
              epoch=1, comment_id=121, prior=HEAD):
    return {
        "schema": SCHEMA, "source_sha": source,
        "owner_epoch": epoch, "comment_id": comment_id,
        "body_sha256": "a" * 64, "mode": mode, "lane": lane,
        "prior_event_head_sha256": prior,
        "scientific_first_use": False, "dispatch_authorized": False,
        "self_source_mutation": False, "checkpoint_mutation": False,
        "accepted_ref_mutation": False,
    }


def row(payload=None, *, seq=1, prior=HEAD, sha=AFTER):
    return {"seq": seq, "prior_sha": prior, "sha": sha,
            "payload": admission() if payload is None else payload}


def replay(*events, source=SOURCE, epoch=1):
    return project_verified_events(events=tuple(events),
                                   current_source_sha=source,
                                   current_epoch=epoch)


class PhaseModeReplayTests(unittest.TestCase):
    def test_empty_verified_history_defaults_auto_only_as_preview(self):
        actual = replay()
        self.assertEqual(actual["mode"], "AUTO")
        self.assertEqual(actual["status"], "NO_PERSISTED_OVERRIDE_AUTO_DEFAULT")
        self.assertFalse(actual["mode_writer_installed"])

    def test_hold_is_sticky_across_cold_projections(self):
        event = row()
        a = replay(event)
        b = replay(event)
        self.assertEqual((a["mode"], b["mode"]), ("HOLD", "HOLD"))
        self.assertIsNone(a["lane"])
        self.assertFalse(a["dispatch_authorized"])
        self.assertEqual(a["consumed_comment_ids"], frozenset({121}))

    def test_subsequent_verified_auto_replaces_prior_hold(self):
        first = row()
        second = row(admission(mode="AUTO", comment_id=122, prior=AFTER),
                     seq=4, prior=AFTER, sha="2" * 64)
        self.assertEqual(replay(first, second)["mode"], "AUTO")

    def test_research_lane_recovered(self):
        a = replay(row(admission(mode="RESEARCH", lane="Wingless")))
        self.assertEqual((a["mode"], a["lane"]), ("RESEARCH", "Wingless"))

    def test_self_improvement_remains_separate_lane(self):
        a = replay(row(admission(mode="SELF_IMPROVE")))
        self.assertEqual(a["mode"], "SELF_IMPROVE")
        self.assertIsNone(a["lane"])

    def test_duplicate_comment_replay_denied(self):
        with self.assertRaises(ModeReplayDenied):
            replay(row(), row(admission(prior=AFTER), seq=2,
                              prior=AFTER, sha="2" * 64))

    def test_event_sort_and_seq_denied(self):
        with self.assertRaises(ModeReplayDenied):
            replay(row(), row(admission(comment_id=122, prior=AFTER),
                              seq=1, prior=AFTER, sha="2" * 64))

    def test_edited_payload_prior_hash_denied(self):
        with self.assertRaises(ModeReplayDenied):
            replay(row(admission(prior="f" * 64)))

    def test_unknown_fields_or_missing_fields_denied(self):
        for payload in ({**admission(), "permit": True},
                        {k: v for k, v in admission().items() if k != "mode"}):
            with self.subTest(payload=payload):
                with self.assertRaises(ModeReplayDenied):
                    replay(row(payload))

    def test_new_source_or_epoch_never_clears_hold(self):
        a = row()
        for kwargs in ({"source": "b" * 40}, {"epoch": 2}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ModeReplayDenied):
                    replay(a, **kwargs)

    def test_mode_malformed_or_forbidden_lane_denied(self):
        for d in ({"mode": "EXECUTE"},
                  {"mode": "SELF_IMPROVE", "lane": "Yggdrasil"},
                  {"mode": "HOLD", "lane": "Wingless"},
                  {"mode": "TRAIN", "lane": "FORGE-self"}):
            with self.subTest(d=d):
                with self.assertRaises(ModeReplayDenied):
                    replay(row(admission(**d)))

    def test_escalation_flag_denied(self):
        for flag in ("scientific_first_use", "dispatch_authorized",
                     "self_source_mutation", "checkpoint_mutation",
                     "accepted_ref_mutation"):
            with self.subTest(flag=flag):
                payload = admission()
                payload[flag] = True
                with self.assertRaises(ModeReplayDenied):
                    replay(row(payload))

    def test_invalid_comment_id_and_sha_denied(self):
        for payload in (admission(comment_id=True),
                        admission(comment_id=0),
                        {**admission(), "body_sha256": "not-a-hash"}):
            with self.subTest(payload=payload):
                with self.assertRaises(ModeReplayDenied):
                    replay(row(payload))

    def test_event_shape_and_event_count_denied(self):
        with self.assertRaises(ModeReplayDenied):
            project_verified_events(events=[row()],
                                    current_source_sha=SOURCE,
                                    current_epoch=1)
        with self.assertRaises(ModeReplayDenied):
            replay({"seq": 1})

    def test_real_disabled_owner_sqlite_cold_readback_and_no_writes(self):
        from f139.local_controller import Database
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "disabled-original-fixture.sqlite"
            db = Database.initialize(path, SOURCE)
            try:
                meta = db.meta()
                self.assertEqual(meta["enabled"], 0)
                original = read_original_owner_mode(
                    db=db, installed_source_sha=SOURCE,
                    protected_main_sha=SOURCE, owner_epoch=1)
                self.assertEqual(original["mode"], "AUTO")
                with db.transaction():
                    before = db.meta()
                    payload = admission(prior=before["head_hash"])
                    db.event(KIND, payload)
                db.verify()
            finally:
                db.close()
            ro = Database.open_readonly(path)
            try:
                a = read_original_owner_mode(
                    db=ro, installed_source_sha=SOURCE,
                    protected_main_sha=SOURCE, owner_epoch=1)
                b = read_original_owner_mode(
                    db=ro, installed_source_sha=SOURCE,
                    protected_main_sha=SOURCE, owner_epoch=1)
                self.assertEqual((a["mode"], b["mode"]), ("HOLD", "HOLD"))
                self.assertEqual(a["last_comment_id"], 121)
                with self.assertRaises(ModeReplayDenied):
                    read_original_owner_mode(
                        db=ro, installed_source_sha=SOURCE,
                        protected_main_sha="b" * 40, owner_epoch=1)
                with self.assertRaises(ModeReplayDenied):
                    read_original_owner_mode(
                        db=ro, installed_source_sha=SOURCE,
                        protected_main_sha=SOURCE, owner_epoch=2)
            finally:
                ro.close()


if __name__ == "__main__":
    unittest.main()
